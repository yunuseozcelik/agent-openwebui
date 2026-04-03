"""MAF Orchestrator - plan -> specialist -> synthesis workflow."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Literal

from agent_framework import AgentResponse

from agent_setup import (
    create_chat_agent,
    create_output_structurer_agent,
    create_planner_agent,
    create_specialist_agents,
    create_synthesis_agent,
)
from config import (
    MAX_WORKFLOW_SESSIONS,
    OPENAI_PLANNER_MODEL,
    OPENAI_WORKER_MODEL,
    WORKFLOW_SESSION_TTL_SECONDS,
)
from cost_control import cost_tracker
from domains import AGENT_LABELS, DOMAIN_ORDER, DOMAIN_REGISTRY, AgentName


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
WorkflowState = Literal["active", "waiting_for_details", "waiting_for_approval", "completed"]
VALID_WORKFLOW_STATES = {"active", "waiting_for_details", "waiting_for_approval", "completed"}
SPECIALIST_WORKFLOW_STATES = {"waiting_for_details", "waiting_for_approval", "completed"}


@dataclass
class PlanStep:
    agent: AgentName
    description: str


@dataclass
class PlannerDecision:
    steps: list[PlanStep]
    continue_current_workflow: bool = False


@dataclass
class StructuredAgentOutput:
    user_response: str
    workflow_state: WorkflowState
    summary: str
    shared_context: str
    missing_fields: list[dict[str, Any]] = field(default_factory=list)
    approval_required: bool = False
    result_reference: dict[str, Any] | None = None


@dataclass
class StepResult:
    agent: AgentName
    description: str
    output: str
    summary: str
    workflow_state: WorkflowState
    missing_fields: list[dict[str, Any]] = field(default_factory=list)
    approval_required: bool = False
    result_reference: dict[str, Any] | None = None
    shared_context: str = ""


@dataclass
class WorkflowContext:
    workflow_id: str
    state: WorkflowState
    current_agent: AgentName | None = None
    current_step_index: int = 0
    total_steps: int = 0
    summary: str = ""
    missing_fields: list[dict[str, Any]] = field(default_factory=list)
    approval_required: bool = False
    plan_steps: list[PlanStep] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


@dataclass
class WorkflowResult:
    plan_steps: list[PlanStep]
    step_results: list[StepResult]
    final_text: str
    shared_context: dict[str, str]
    workflow_context: WorkflowContext | None = None
    continue_current_workflow: bool = False


@dataclass
class ConversationWorkflowSession:
    conversation_id: str
    active_workflow: WorkflowContext | None = None
    workflow_counter: int = 0
    updated_at: float = field(default_factory=time.time)


class MicrosoftAgentOrchestrator:
    def __init__(self) -> None:
        self.planner_model_id = OPENAI_PLANNER_MODEL
        self.worker_model_id = OPENAI_WORKER_MODEL
        self.planner_agent = create_planner_agent()
        self.chat_agent = create_chat_agent()
        self.synthesis_agent = create_synthesis_agent()
        self.output_structurer_agent = create_output_structurer_agent()
        self.specialists = create_specialist_agents()
        self.workflow_sessions: dict[str, ConversationWorkflowSession] = {}
        self.session_ttl_seconds = WORKFLOW_SESSION_TTL_SECONDS
        self.max_workflow_sessions = MAX_WORKFLOW_SESSIONS

    async def run(
        self,
        history: list[dict[str, str]],
        *,
        conversation_id: str | None = None,
        user_context: dict[str, str] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> WorkflowResult:
        cost_tracker.record_request("maf")
        self._cleanup_sessions()

        session = self._get_session(conversation_id) if conversation_id else None
        current_workflow = session.active_workflow if session else None

        planner_decision = await self.plan(history, workflow_context=current_workflow)
        continue_current_workflow = bool(current_workflow and planner_decision.continue_current_workflow)
        execution_steps = planner_decision.steps

        if continue_current_workflow and current_workflow and not execution_steps:
            execution_steps = self._resume_plan_steps(current_workflow)

        if not execution_steps:
            if session:
                session.active_workflow = None
                session.updated_at = time.time()

            final_text = await self._run_chat(history, user_context=user_context or {})
            if progress_callback:
                await _emit(progress_callback, {"type": "chat_output", "output": final_text})

            return WorkflowResult(
                plan_steps=[],
                step_results=[],
                final_text=final_text,
                shared_context={},
                workflow_context=None,
                continue_current_workflow=False,
            )

        display_steps = self._merge_plan_steps(
            current_workflow.plan_steps if continue_current_workflow and current_workflow else [],
            execution_steps,
        )

        workflow_id = (
            current_workflow.workflow_id
            if continue_current_workflow and current_workflow
            else self._next_workflow_id(session)
        )
        workflow_context = WorkflowContext(
            workflow_id=workflow_id,
            state="active",
            current_step_index=0,
            total_steps=len(display_steps),
            plan_steps=display_steps,
            updated_at=time.time(),
        )

        if session:
            session.active_workflow = workflow_context
            session.updated_at = time.time()

        if progress_callback:
            await _emit(
                progress_callback,
                {
                    "type": "plan_ready",
                    "plan_steps": display_steps,
                    "workflow_context": self._serialize_workflow_context(workflow_context),
                    "continue_current_workflow": continue_current_workflow,
                },
            )

        transcript = self._format_history(history)
        shared_context: dict[str, str] = {}
        step_results: list[StepResult] = []

        for step in execution_steps:
            workflow_context.state = "active"
            workflow_context.current_agent = step.agent
            workflow_context.current_step_index = self._get_step_position(display_steps, step.agent)
            workflow_context.summary = step.description
            workflow_context.missing_fields = []
            workflow_context.approval_required = False
            workflow_context.updated_at = time.time()

            if progress_callback:
                await _emit(
                    progress_callback,
                    {
                        "type": "step_start",
                        "step": step,
                        "workflow_context": self._serialize_workflow_context(workflow_context),
                    },
                )

            agent = self.specialists[step.agent]
            prompt = self._build_step_prompt(
                step=step,
                transcript=transcript,
                user_context=user_context or {},
                shared_context=shared_context,
                workflow_context=workflow_context,
            )
            response = await agent.run(prompt)
            self._record_response_usage(
                response,
                component=step.agent.lower(),
                default_model_id=self.worker_model_id,
            )
            raw_output = self._extract_text(response) or "Islem tamamlandi fakat bos bir cevap dondu."
            structured_output = await self._parse_structured_agent_output(
                raw_output,
                step=step,
                workflow_context=current_workflow if continue_current_workflow else workflow_context,
            )

            step_result = StepResult(
                agent=step.agent,
                description=step.description,
                output=structured_output.user_response,
                summary=structured_output.summary,
                workflow_state=structured_output.workflow_state,
                missing_fields=structured_output.missing_fields,
                approval_required=structured_output.approval_required,
                result_reference=structured_output.result_reference,
                shared_context=structured_output.shared_context,
            )
            step_results.append(step_result)
            shared_context[step.agent] = structured_output.shared_context

            workflow_context.current_agent = step.agent
            workflow_context.summary = structured_output.summary
            workflow_context.state = structured_output.workflow_state
            workflow_context.missing_fields = structured_output.missing_fields
            workflow_context.approval_required = structured_output.approval_required
            workflow_context.updated_at = time.time()

            if progress_callback:
                await _emit(
                    progress_callback,
                    {
                        "type": "step_end",
                        "step": step,
                        "output": structured_output.summary,
                        "workflow_context": self._serialize_workflow_context(workflow_context),
                    },
                )

            if structured_output.workflow_state != "completed":
                if session:
                    session.active_workflow = workflow_context
                    session.updated_at = time.time()

                return WorkflowResult(
                    plan_steps=display_steps,
                    step_results=step_results,
                    final_text=structured_output.user_response,
                    shared_context=shared_context,
                    workflow_context=workflow_context,
                    continue_current_workflow=continue_current_workflow,
                )

        final_text = await self._build_final_text(
            step_results,
            history=history,
            user_context=user_context or {},
        )
        workflow_context.state = "completed"
        workflow_context.current_step_index = len(display_steps)
        workflow_context.summary = step_results[-1].summary if step_results else ""
        workflow_context.missing_fields = []
        workflow_context.approval_required = False
        workflow_context.updated_at = time.time()

        if session:
            session.active_workflow = None
            session.updated_at = time.time()

        return WorkflowResult(
            plan_steps=display_steps,
            step_results=step_results,
            final_text=final_text,
            shared_context=shared_context,
            workflow_context=workflow_context,
            continue_current_workflow=continue_current_workflow,
        )

    async def plan(
        self,
        history: list[dict[str, str]],
        *,
        workflow_context: WorkflowContext | None = None,
    ) -> PlannerDecision:
        response = await self.planner_agent.run(self._build_plan_prompt(history, workflow_context=workflow_context))
        self._record_response_usage(response, component="planner", default_model_id=self.planner_model_id)
        response_text = self._extract_text(response)
        payload = self._parse_json_payload(response_text)

        continue_current_workflow = bool(payload.get("continue_current_workflow")) if isinstance(payload, dict) else False
        raw_steps = payload.get("steps", []) if isinstance(payload, dict) else []
        if not raw_steps:
            raw_steps = self._fallback_plan(history)

        normalized: list[PlanStep] = []
        seen_agents: set[str] = set()
        for step in raw_steps:
            agent = step.get("agent")
            description = (step.get("description") or "").strip()
            if agent not in AGENT_LABELS or agent in seen_agents:
                continue
            seen_agents.add(agent)
            normalized.append(
                PlanStep(
                    agent=agent,
                    description=description or f"{AGENT_LABELS[agent]} adimi calistiriliyor",
                )
            )

        return PlannerDecision(
            steps=self._apply_domain_dependencies(normalized),
            continue_current_workflow=continue_current_workflow,
        )

    async def _run_chat(self, history: list[dict[str, str]], *, user_context: dict[str, str]) -> str:
        prompt = self._build_chat_prompt(history, user_context=user_context)
        response = await self.chat_agent.run(prompt)
        self._record_response_usage(response, component="chat", default_model_id=self.worker_model_id)
        return self._extract_text(response) or "Merhaba, nasil yardimci olabilirim?"

    def _build_plan_prompt(
        self,
        history: list[dict[str, str]],
        *,
        workflow_context: WorkflowContext | None = None,
    ) -> str:
        current_workflow_block = (
            json.dumps(self._serialize_workflow_context(workflow_context), ensure_ascii=False)
            if workflow_context
            else "null"
        )
        last_user_message = self._get_last_user_message(history)
        return (
            "KULLANICI MESAJ GECMISI\n"
            f"{self._format_history(history)}\n\n"
            "SON KULLANICI MESAJI\n"
            f"{last_user_message}\n\n"
            "AKTIF WORKFLOW KONTEXTI\n"
            f"{current_workflow_block}\n\n"
            "JSON CIKTI SOZLESMESI\n"
            "{\n"
            '  "continue_current_workflow": true | false,\n'
            '  "steps": [{"agent": "HR_Agent|IT_Agent|General_Agent|Test_Agent", "description": "Turkce kisa aciklama"}]\n'
            "}\n\n"
            "KURALLAR:\n"
            "- Yalnizca gecerli JSON don. Markdown veya code fence kullanma.\n"
            "- Aktif workflow varsa ve kullanicinin son mesaji o akistaki eksik bilgi/onay/yaniti tamamliyorsa continue_current_workflow=true yap.\n"
            "- Kullanici yeni ve alakasiz bir konuya gectiyse continue_current_workflow=false yap ve yeni steps listesi uret.\n"
            "- Selamlasma veya bos sohbet ise steps listesini [] don.\n"
            "- Her adim icin kullaniciya gosterilecek kisa bir aciklama yaz.\n"
        )

    def _build_chat_prompt(self, history: list[dict[str, str]], *, user_context: dict[str, str]) -> str:
        return (
            "AKTIF KULLANICI BAGLAMI\n"
            f"{json.dumps(user_context, ensure_ascii=False)}\n\n"
            "KONUSMA GECMISI\n"
            f"{self._format_history(history)}\n\n"
            "Kullanicinin son mesajina Turkce cevap ver."
        )

    def _build_step_prompt(
        self,
        *,
        step: PlanStep,
        transcript: str,
        user_context: dict[str, str],
        shared_context: dict[str, str],
        workflow_context: WorkflowContext | None = None,
    ) -> str:
        shared_lines = "\n".join(
            f"- {AGENT_LABELS.get(agent, agent)}: {output}"
            for agent, output in shared_context.items()
        ) or "- Henuz onceki adim yok."
        domain_spec = DOMAIN_REGISTRY[step.agent]
        current_workflow_block = (
            json.dumps(self._serialize_workflow_context(workflow_context), ensure_ascii=False)
            if workflow_context
            else "null"
        )
        last_user_message = self._get_last_user_message_from_transcript(transcript)
        email_line = ""
        if domain_spec.requires_user_email and not user_context.get("user_email"):
            email_line = (
                "\n- Kullanici e-postasi baglamda yok. Mock mod varsayimi ile demo kullanici uzerinden ilerle."
            )

        return (
            f"AKTIF ADIM: {step.description}\n"
            f"AKTIF UZMAN: {step.agent}\n\n"
            "KULLANICI BAGLAMI\n"
            f"{json.dumps(user_context, ensure_ascii=False)}\n\n"
            "AKTIF WORKFLOW KONTEXTI\n"
            f"{current_workflow_block}\n\n"
            "SON KULLANICI MESAJI\n"
            f"{last_user_message}\n\n"
            "ONCEKI UZMAN CIKTILARI\n"
            f"{shared_lines}\n\n"
            "KONUSMA GECMISI\n"
            f"{transcript}\n\n"
            "JSON CIKTI SOZLESMESI\n"
            "{\n"
            '  "user_response": "Kullaniciya gidecek Turkce cevap",\n'
            '  "workflow_state": "waiting_for_details | waiting_for_approval | completed",\n'
            '  "summary": "UI paneli icin tek cumlelik kisa ozet",\n'
            '  "shared_context": "Sonraki uzmanlara aktarilacak kisa olgusal ozet",\n'
            '  "missing_fields": [{"name": "alan_adi", "label": "Gorunen Alan"}],\n'
            '  "approval_required": true | false,\n'
            '  "result_reference": {"kind": "kayit_tipi", "id": "kayit_numarasi"} | null\n'
            "}\n\n"
            "KURALLAR:\n"
            "- Sadece kendi uzmanlik alanini ele al.\n"
            "- Kullaniciya ait veri gerekiyorsa user_email bilgisini kullan.\n"
            "- Yalnizca desteklenen IFS sorgulari icin gerekli tool'lari cagir.\n"
            f"- Alan ozel kurallar: {domain_spec.execution_guidance}\n"
            "- waiting_for_details: Yalnizca desteklenen sorgu icin eksik veri istiyorsan kullan.\n"
            "- waiting_for_approval: Yalnizca gercekten son kullanici onayi gerektiren desteklenen akista kullan.\n"
            "- completed: Bilgi cevabi verdigin, sorguyu tamamladigin veya desteklenmeyen istegin kapsam disi oldugunu net acikladigin durumlarda kullan.\n"
            "- Resmi talep, ticket, avans, bordro veya servis bilgisi olusturabilecegini iddia etme.\n"
            "- Kullaniciya soru soruyorsan, netlestirme istiyorsan veya bilgi listesi istiyorsan completed deme.\n"
            "- waiting_for_details kullaniyorsan eksik alanlari tahmin etme; gercekten hangi alanlari bekliyorsan tek tek yaz.\n"
            "- Kullanicidan sadece tek bir detay bekliyorsan bile missing_fields listesine onu ekle.\n"
            "- Yanitinin sonunda yalnizca nezaket veya kapanis sorusu varsa bu workflow_state'i waiting yapmaz; asıl islem sonucuna gore karar ver.\n"
            "- missing_fields yalnizca waiting_for_details durumunda doldur.\n"
            "- approval_required yalnizca waiting_for_approval durumunda true olsun.\n"
            "- Gercek bir sistem kayit kimligi yoksa result_reference alanini null birak.\n"
            "- waiting_for_details kullaniyorsan missing_fields bos olamaz.\n"
            "- waiting_for_approval kullaniyorsan approval_required=true olmalidir.\n"
            "- Aktif workflow varsa ve kullanicinin son mesaji o akisi tamamliyorsa ayni akisi devam ettir, bastan baslama.\n"
            "- Yalnizca gecerli JSON don. Markdown veya code fence kullanma."
            f"{email_line}"
        )

    async def _build_final_text(
        self,
        step_results: list[StepResult],
        *,
        history: list[dict[str, str]],
        user_context: dict[str, str],
    ) -> str:
        if not step_results:
            return "Yanit olusturulamadi."
        if len(step_results) == 1:
            return step_results[0].output

        summary_prompt = (
            "KULLANICI BAGLAMI\n"
            f"{json.dumps(user_context, ensure_ascii=False)}\n\n"
            "KONUSMA OZETI\n"
            f"{self._format_history(history)}\n\n"
            "UZMAN CIKTILARI\n"
            + "\n\n".join(
                f"{AGENT_LABELS.get(item.agent, item.agent)}\n{item.output}" for item in step_results
            )
            + "\n\nBunlari tek, net ve kullanici dostu bir final cevapta birlestir."
        )
        response = await self.synthesis_agent.run(summary_prompt)
        self._record_response_usage(response, component="synthesis", default_model_id=self.worker_model_id)
        return self._extract_text(response) or "\n\n".join(item.output for item in step_results)

    def _get_session(self, conversation_id: str) -> ConversationWorkflowSession:
        session = self.workflow_sessions.get(conversation_id)
        if session is None:
            session = ConversationWorkflowSession(conversation_id=conversation_id)
            self.workflow_sessions[conversation_id] = session
        session.updated_at = time.time()
        return session

    def _cleanup_sessions(self) -> None:
        if not self.workflow_sessions:
            return

        now = time.time()
        expired_ids = [
            conversation_id
            for conversation_id, session in self.workflow_sessions.items()
            if now - session.updated_at > self.session_ttl_seconds
        ]
        for conversation_id in expired_ids:
            self.workflow_sessions.pop(conversation_id, None)

        if len(self.workflow_sessions) <= self.max_workflow_sessions:
            return

        overflow = len(self.workflow_sessions) - self.max_workflow_sessions
        oldest_sessions = sorted(
            self.workflow_sessions.items(),
            key=lambda item: item[1].updated_at,
        )[:overflow]
        for conversation_id, _ in oldest_sessions:
            self.workflow_sessions.pop(conversation_id, None)

    @staticmethod
    def _next_workflow_id(session: ConversationWorkflowSession | None) -> str:
        if session is None:
            return f"wf-{int(time.time() * 1000)}"

        session.workflow_counter += 1
        safe_conversation_id = re.sub(r"[^a-zA-Z0-9]", "", session.conversation_id)[:10] or "conv"
        return f"wf-{safe_conversation_id}-{session.workflow_counter:04d}"

    @staticmethod
    def _serialize_workflow_context(workflow_context: WorkflowContext | None) -> dict[str, Any] | None:
        if not workflow_context:
            return None

        return {
            "workflow_id": workflow_context.workflow_id,
            "state": workflow_context.state,
            "current_agent": workflow_context.current_agent,
            "current_step_index": workflow_context.current_step_index,
            "total_steps": workflow_context.total_steps,
            "summary": workflow_context.summary,
            "missing_fields": workflow_context.missing_fields,
            "approval_required": workflow_context.approval_required,
            "plan_steps": [
                {"agent": step.agent, "description": step.description}
                for step in workflow_context.plan_steps
            ],
        }

    @staticmethod
    def _merge_plan_steps(existing: list[PlanStep], incoming: list[PlanStep]) -> list[PlanStep]:
        merged: list[PlanStep] = []
        seen_agents: set[str] = set()

        for step in [*existing, *incoming]:
            if step.agent in seen_agents:
                continue
            seen_agents.add(step.agent)
            merged.append(step)

        return merged

    @staticmethod
    def _resume_plan_steps(workflow_context: WorkflowContext) -> list[PlanStep]:
        if workflow_context.current_agent:
            current_step = next(
                (
                    step
                    for step in workflow_context.plan_steps
                    if step.agent == workflow_context.current_agent
                ),
                None,
            )
            if current_step:
                return [current_step]
            return [
                PlanStep(
                    agent=workflow_context.current_agent,
                    description=workflow_context.summary or f"{workflow_context.current_agent} adimi surduruluyor",
                )
            ]

        if workflow_context.plan_steps:
            return [workflow_context.plan_steps[-1]]

        return []

    @staticmethod
    def _get_step_position(plan_steps: list[PlanStep], agent_name: AgentName) -> int:
        for index, step in enumerate(plan_steps, start=1):
            if step.agent == agent_name:
                return index
        return len(plan_steps) or 1

    async def _parse_structured_agent_output(
        self,
        raw_output: str,
        *,
        step: PlanStep,
        workflow_context: WorkflowContext | None = None,
    ) -> StructuredAgentOutput:
        payload = self._parse_json_payload(raw_output)
        if not self._is_structured_payload(payload):
            repaired_payload = await self._repair_structured_agent_output(
                raw_output,
                step=step,
                workflow_context=workflow_context,
            )
            if repaired_payload:
                payload = repaired_payload

        requested_state = payload.get("workflow_state")
        if requested_state not in SPECIALIST_WORKFLOW_STATES:
            requested_state = None

        user_response = str(payload.get("user_response") or "").strip() or raw_output.strip()
        summary = str(payload.get("summary") or "").strip() or step.description
        shared_context = str(payload.get("shared_context") or "").strip() or summary or user_response
        missing_fields = self._normalize_missing_fields(payload.get("missing_fields"))
        approval_required = bool(payload.get("approval_required"))
        result_reference = self._normalize_result_reference(payload.get("result_reference"))
        if result_reference is None:
            result_reference = self._extract_result_reference_from_text(user_response, step=step)
        workflow_state = self._resolve_workflow_state(
            requested_state=requested_state,
            missing_fields=missing_fields,
            approval_required=approval_required,
            result_reference=result_reference,
            workflow_context=workflow_context,
        )
        if workflow_state == "waiting_for_details" and not missing_fields:
            missing_fields = self._default_missing_fields_for_step(step)

        if workflow_state != "waiting_for_details":
            missing_fields = []
        if workflow_state != "waiting_for_approval":
            approval_required = False
        if workflow_state == "completed":
            missing_fields = []
            approval_required = False

        return StructuredAgentOutput(
            user_response=user_response,
            workflow_state=workflow_state,
            summary=summary,
            shared_context=shared_context,
            missing_fields=missing_fields,
            approval_required=approval_required,
            result_reference=result_reference,
        )

    @staticmethod
    def _is_structured_payload(payload: dict[str, Any]) -> bool:
        if not payload:
            return False

        if payload.get("workflow_state") in SPECIALIST_WORKFLOW_STATES and payload.get("user_response"):
            return True

        return any(
            key in payload
            for key in ("missing_fields", "approval_required", "result_reference", "summary", "shared_context")
        )

    async def _repair_structured_agent_output(
        self,
        raw_output: str,
        *,
        step: PlanStep,
        workflow_context: WorkflowContext | None = None,
    ) -> dict[str, Any]:
        prompt = (
            f"AKTIF ADIM\n{step.agent} - {step.description}\n\n"
            "AKTIF WORKFLOW KONTEXTI\n"
            f"{json.dumps(self._serialize_workflow_context(workflow_context), ensure_ascii=False) if workflow_context else 'null'}\n\n"
            "HAM UZMAN CIKTISI\n"
            f"{raw_output}\n\n"
            "Yukarıdaki ham ciktiyi backend workflow JSON sozlesmesine gore normalize et."
        )
        response = await self.output_structurer_agent.run(prompt)
        self._record_response_usage(
            response,
            component="workflow_repair",
            default_model_id=self.worker_model_id,
        )
        repaired_text = self._extract_text(response)
        return self._parse_json_payload(repaired_text)

    @staticmethod
    def _resolve_workflow_state(
        *,
        requested_state: str | None,
        missing_fields: list[dict[str, Any]],
        approval_required: bool,
        result_reference: dict[str, Any] | None,
        workflow_context: WorkflowContext | None = None,
    ) -> WorkflowState:
        if result_reference and result_reference.get("id"):
            return "completed"

        if approval_required:
            return "waiting_for_approval"

        if missing_fields:
            return "waiting_for_details"

        if requested_state in SPECIALIST_WORKFLOW_STATES:
            return requested_state

        if workflow_context and workflow_context.state in {"waiting_for_details", "waiting_for_approval"}:
            return workflow_context.state

        return "completed"

    @staticmethod
    def _normalize_missing_fields(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, str):
                label = item.strip()
                if label:
                    normalized.append({"name": label.lower().replace(" ", "_"), "label": label})
                continue
            if not isinstance(item, dict):
                continue

            name = str(item.get("name") or item.get("field") or item.get("label") or "").strip()
            label = str(item.get("label") or item.get("title") or name).strip()
            if not name and not label:
                continue
            normalized.append(
                {
                    "name": name or label.lower().replace(" ", "_"),
                    "label": label or name,
                }
            )

        return normalized

    @staticmethod
    def _normalize_result_reference(value: Any) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            return None

        kind = str(value.get("kind") or value.get("type") or "").strip()
        ref_id = str(value.get("id") or value.get("request_id") or value.get("ticket_id") or "").strip()
        if not kind and not ref_id:
            return None

        return {
            "kind": kind or "record",
            "id": ref_id,
        }

    @staticmethod
    def _default_missing_fields_for_step(step: PlanStep) -> list[dict[str, Any]]:
        if step.agent == "Test_Agent":
            return [
                {"name": "talep_basligi", "label": "Talep Basligi"},
                {"name": "oncelik", "label": "Oncelik"},
                {"name": "hedef_tarih", "label": "Hedef Tarih"},
            ]
        if step.agent == "IT_Agent":
            return [{"name": "parca_no", "label": "Parca Numarasi"}]
        if step.agent == "HR_Agent":
            return [{"name": "user_identifier", "label": "E-posta veya Sicil Numarasi"}]
        return [{"name": "details", "label": "Gerekli Detaylar"}]

    @staticmethod
    def _extract_result_reference_from_text(
        text: str,
        *,
        step: PlanStep,
    ) -> dict[str, Any] | None:
        if not text:
            return None

        patterns = [
            ("mock_request", r"\b(MOCK-\d{8,})\b"),
            ("leave_request", r"\b(LEAVE-\d{6,})\b"),
            ("support_ticket", r"\b(INC-\d{5,})\b"),
            ("equipment_request", r"\b(EQ-\d{4,})\b"),
            ("advance_request", r"\b(ADV-\d{4,})\b"),
            ("expense_report", r"\b(EXP-\d{4,})\b"),
        ]
        for kind, pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    "kind": kind,
                    "id": match.group(1),
                }

        return None

    @staticmethod
    def _record_response_usage(
        response: AgentResponse,
        *,
        component: str,
        default_model_id: str,
    ) -> None:
        usage = getattr(response, "usage_details", None) or {}
        if not usage:
            return

        raw_representation = getattr(response, "raw_representation", None)
        model_id = (
            getattr(response, "model_id", None)
            or getattr(raw_representation, "model", None)
            or getattr(response, "additional_properties", {}).get("model")
            or default_model_id
        )
        input_tokens = int(usage.get("input_token_count") or 0)
        output_tokens = int(usage.get("output_token_count") or 0)
        total_tokens = int(usage.get("total_token_count") or (input_tokens + output_tokens))
        if input_tokens == 0 and output_tokens == 0 and total_tokens == 0:
            return

        cost_tracker.record_llm_call(
            engine="maf",
            component=component,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    @staticmethod
    def _format_history(history: list[dict[str, str]]) -> str:
        lines = []
        for item in history:
            role = item.get("role", "user").upper()
            content = (item.get("content") or "").strip()
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines) if lines else "Bos konusma."

    @staticmethod
    def _get_last_user_message(history: list[dict[str, str]]) -> str:
        for item in reversed(history):
            if item.get("role") == "user":
                return (item.get("content") or "").strip() or "-"
        return "-"

    @staticmethod
    def _get_last_user_message_from_transcript(transcript: str) -> str:
        for line in reversed(transcript.splitlines()):
            if line.startswith("USER:"):
                return line.split(":", 1)[1].strip() or "-"
        return "-"

    @staticmethod
    def _extract_text(response: AgentResponse) -> str:
        if getattr(response, "text", None):
            return response.text
        value = getattr(response, "value", None)
        if isinstance(value, str):
            return value
        return str(value) if value else ""

    @staticmethod
    def _parse_json_payload(text: str) -> dict[str, Any]:
        if not text:
            return {}

        candidate = text.strip()
        fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
        if fence_match:
            candidate = fence_match.group(1)
        else:
            brace_match = re.search(r"\{.*\}", candidate, re.DOTALL)
            if brace_match:
                candidate = brace_match.group(0)

        try:
            payload = json.loads(candidate)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _fallback_plan(self, history: list[dict[str, str]]) -> list[dict[str, str]]:
        transcript = self._format_history(history).lower()
        steps: list[dict[str, str]] = []
        for agent_name, spec in DOMAIN_REGISTRY.items():
            if any(hint in transcript for hint in spec.planner_hints):
                steps.append(
                    {
                        "agent": agent_name,
                        "description": f"{spec.label} adimi calistiriliyor",
                    }
                )
        return steps

    def _apply_domain_dependencies(self, steps: list[PlanStep]) -> list[PlanStep]:
        step_by_agent = {step.agent: step for step in steps}
        ordered: list[PlanStep] = []
        visited: set[AgentName] = set()

        def visit(agent_name: AgentName) -> None:
            if agent_name in visited or agent_name not in step_by_agent:
                return
            for dependency in DOMAIN_REGISTRY[agent_name].dependencies:
                visit(dependency)
            visited.add(agent_name)
            ordered.append(step_by_agent[agent_name])

        planner_index = {step.agent: idx for idx, step in enumerate(steps)}
        for agent_name in sorted(
            step_by_agent.keys(),
            key=lambda name: (planner_index.get(name, 999), DOMAIN_ORDER.index(name)),
        ):
            visit(agent_name)
        return ordered


async def _emit(callback: ProgressCallback, payload: dict[str, Any]) -> None:
    result = callback(payload)
    if hasattr(result, "__await__"):
        await result
