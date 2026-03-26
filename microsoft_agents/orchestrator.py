from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from agent_framework import AgentResponse

try:
    from .agent_setup import (
        create_chat_agent,
        create_chat_client,
        create_planner_agent,
        create_planner_client,
        create_specialist_agents,
        create_specialist_client,
        create_synthesis_agent,
        create_synthesis_client,
    )
    from .config import OPENAI_PLANNER_MODEL, OPENAI_WORKER_MODEL
    from .domains import AGENT_LABELS, DOMAIN_ORDER, DOMAIN_REGISTRY, AgentName
except ImportError:
    from agent_setup import (
        create_chat_agent,
        create_chat_client,
        create_planner_agent,
        create_planner_client,
        create_specialist_agents,
        create_specialist_client,
        create_synthesis_agent,
        create_synthesis_client,
    )
    from config import OPENAI_PLANNER_MODEL, OPENAI_WORKER_MODEL
    from domains import AGENT_LABELS, DOMAIN_ORDER, DOMAIN_REGISTRY, AgentName

from utils.cost_control import cost_tracker


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


@dataclass
class PlanStep:
    agent: AgentName
    description: str


@dataclass
class StepResult:
    agent: AgentName
    description: str
    output: str


@dataclass
class WorkflowResult:
    plan_steps: list[PlanStep]
    step_results: list[StepResult]
    final_text: str
    shared_context: dict[str, str]


class MicrosoftAgentOrchestrator:
    def __init__(self) -> None:
        self.planner_model_id = OPENAI_PLANNER_MODEL
        self.worker_model_id = OPENAI_WORKER_MODEL
        planner_client = create_planner_client()
        chat_client = create_chat_client()
        specialist_client = create_specialist_client()
        synthesis_client = create_synthesis_client()
        self.planner_agent = create_planner_agent(planner_client)
        self.chat_agent = create_chat_agent(chat_client)
        self.synthesis_agent = create_synthesis_agent(synthesis_client)
        self.specialists = create_specialist_agents(specialist_client)

    async def run(
        self,
        history: list[dict[str, str]],
        *,
        user_context: dict[str, str] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> WorkflowResult:
        cost_tracker.record_request("maf")
        plan_steps = await self.plan(history)
        if progress_callback:
            await _emit(progress_callback, {"type": "plan_ready", "plan_steps": plan_steps})

        if not plan_steps:
            final_text = await self._run_chat(history, user_context=user_context)
            if progress_callback:
                await _emit(progress_callback, {"type": "chat_output", "output": final_text})
            return WorkflowResult(plan_steps=[], step_results=[], final_text=final_text, shared_context={})

        transcript = self._format_history(history)
        shared_context: dict[str, str] = {}
        step_results: list[StepResult] = []

        for index, step in enumerate(plan_steps):
            if progress_callback:
                await _emit(
                    progress_callback,
                    {
                        "type": "step_start",
                        "index": index,
                        "step": step,
                    },
                )

            agent = self.specialists[step.agent]
            prompt = self._build_step_prompt(
                step=step,
                transcript=transcript,
                user_context=user_context or {},
                shared_context=shared_context,
            )
            response = await agent.run(prompt)
            self._record_response_usage(response, component=step.agent.lower(), default_model_id=self.worker_model_id)
            output = self._extract_text(response) or "Islem tamamlandi fakat bos bir cevap dondu."

            step_result = StepResult(agent=step.agent, description=step.description, output=output)
            step_results.append(step_result)
            shared_context[step.agent] = output

            if progress_callback:
                await _emit(
                    progress_callback,
                    {
                        "type": "step_end",
                        "index": index,
                        "step": step,
                        "output": output,
                    },
                )

        final_text = await self._build_final_text(
            step_results,
            history=history,
            user_context=user_context or {},
        )
        return WorkflowResult(
            plan_steps=plan_steps,
            step_results=step_results,
            final_text=final_text,
            shared_context=shared_context,
        )

    async def plan(self, history: list[dict[str, str]]) -> list[PlanStep]:
        response = await self.planner_agent.run(self._build_plan_prompt(history))
        self._record_response_usage(response, component="planner", default_model_id=self.planner_model_id)
        response_text = self._extract_text(response)
        payload = self._parse_json_payload(response_text)
        steps = payload.get("steps", []) if isinstance(payload, dict) else []
        if not steps:
            steps = self._fallback_plan(history)

        normalized: list[PlanStep] = []
        seen_agents: set[str] = set()
        for step in steps:
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
        return self._apply_domain_dependencies(normalized)

    async def _run_chat(self, history: list[dict[str, str]], *, user_context: dict[str, str] | None = None) -> str:
        prompt = self._build_chat_prompt(history, user_context=user_context or {})
        response = await self.chat_agent.run(prompt)
        self._record_response_usage(response, component="chat", default_model_id=self.worker_model_id)
        return self._extract_text(response) or "Merhaba, nasil yardimci olabilirim?"

    def _build_plan_prompt(self, history: list[dict[str, str]]) -> str:
        return (
            "KULLANICI MESAJ GECMISI\n"
            f"{self._format_history(history)}\n\n"
            "Yukaridaki konusmaya gore JSON plani uret."
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
    ) -> str:
        shared_lines = "\n".join(
            f"- {AGENT_LABELS.get(agent, agent)}: {output}"
            for agent, output in shared_context.items()
        ) or "- Henuz onceki adim yok."
        domain_spec = DOMAIN_REGISTRY[step.agent]
        email_line = ""
        if domain_spec.requires_user_email and not user_context.get("user_email"):
            email_line = (
                "\n- Kullanici e-postasi baglamda yok. Mock mod varsayimi ile demo kullanici uzerinden ilerle ve islemi tamamla."
            )
        return (
            f"AKTIF ADIM: {step.description}\n"
            f"AKTIF UZMAN: {step.agent}\n\n"
            "KULLANICI BAGLAMI\n"
            f"{json.dumps(user_context, ensure_ascii=False)}\n\n"
            "ONCEKI UZMAN CIKTILARI\n"
            f"{shared_lines}\n\n"
            "KONUSMA GECMISI\n"
            f"{transcript}\n\n"
            "Kurallar:\n"
            "- Sadece kendi uzmanlik alanini ele al.\n"
            "- Kullaniciya ait veri gerekiyorsa user_email bilgisini kullan.\n"
            "- Islem gerekiyorsa gerekli tool'lari cagir.\n"
            f"- Alan ozel kurallar: {domain_spec.execution_guidance}\n"
            f"- Turkce ve net cevap ver.{email_line}"
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
            return json.loads(candidate)
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
