"""FNSS Assist Backend - MAF-only FastAPI Server."""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, List, Union

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from context import extract_ow_context
from config import AGENT_ALLOWED_EMAILS, CORS_ALLOW_ORIGINS, MAX_HISTORY_MESSAGES
from cost_control import cost_tracker
from domains import AGENT_LABELS
from orchestrator import MicrosoftAgentOrchestrator

logger = logging.getLogger(__name__)

app = FastAPI(title="FNSS Assist - MAF Backend")
allow_all_origins = CORS_ALLOW_ORIGINS == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_ID = "ifs-microsoft-agent"

# MAF Orchestrator başlatma
try:
    maf_orchestrator = MicrosoftAgentOrchestrator()
    print("[OK] Microsoft Agent Framework orchestrator hazır.")
except Exception as exc:
    logger.exception("Microsoft Agent Framework yüklenirken hata oluştu: %s", exc)
    maf_orchestrator = None


class Message(BaseModel):
    role: str
    content: Union[str, List[Any]]


class ChatCompletionRequest(BaseModel):
    model: str = MODEL_ID
    messages: List[Message]
    stream: bool = False
    conversation_id: str | None = None


class ResponseMessage(BaseModel):
    role: str
    content: str


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ResponseMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]


@app.get("/v1/models")
async def list_models():
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_ID,
                "object": "model",
                "created": now,
                "owned_by": "fnss-assist",
            },
        ],
    }


@app.get("/api/control-panel")
async def get_control_panel():
    return cost_tracker.snapshot()


@app.post("/api/control-panel/reset")
async def reset_control_panel():
    cost_tracker.reset()
    return {"ok": True}


def normalize_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text" and isinstance(part.get("text"), str):
                    texts.append(part["text"])
                elif isinstance(part.get("text"), str):
                    texts.append(part["text"])
        return "\n".join(texts).strip()
    return str(content)


def to_agent_history(request_messages: List[Message]) -> list[dict[str, str]]:
    history = []
    for item in request_messages:
        if item.role not in {"user", "assistant"}:
            continue
        history.append(
            {
                "role": item.role,
                "content": normalize_content(item.content),
            }
        )
    return history[-MAX_HISTORY_MESSAGES:]


def _normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _extract_request_context(request_messages: List[Message]) -> dict[str, str | None]:
    raw_messages = [
        {
            "role": item.role,
            "content": normalize_content(item.content),
        }
        for item in request_messages
    ]
    return extract_ow_context(raw_messages)


def _ensure_agent_access(user_ctx: dict[str, str | None]) -> None:
    if not AGENT_ALLOWED_EMAILS:
        return

    user_email = _normalize_email(user_ctx.get("user_email"))
    allowed_emails = {_normalize_email(item) for item in AGENT_ALLOWED_EMAILS}

    if not user_email:
        raise HTTPException(
            status_code=403,
            detail="FNSS Agent kullanımı için oturum e-posta bilginiz bulunamadı.",
        )

    if user_email not in allowed_emails:
        raise HTTPException(
            status_code=403,
            detail="Bu hesap FNSS Agent özelliği için yetkili değil.",
        )


def _workflow_state_to_mode(state: str | None) -> str:
    if state == "active":
        return "active"
    if state in {"waiting_for_details", "waiting_for_approval"}:
        return "waiting"
    return "done"


def _workflow_state_to_waiting_label(state: str | None) -> str:
    if state == "waiting_for_approval":
        return "Onay Bekleniyor"
    if state == "waiting_for_details":
        return "Bilgi Bekleniyor"
    return "Yanıt Bekliyor"


def _workflow_state_to_status_text(state: str | None) -> str:
    if state == "waiting_for_approval":
        return "Onayınız bekleniyor"
    if state == "waiting_for_details":
        return "Eksik bilgiler bekleniyor"
    if state == "active":
        return "İşlem devam ediyor"
    return "Süreç tamamlandı"


def _serialize_workflow_status(workflow_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not workflow_context:
        return None

    state = workflow_context.get("state") or "completed"
    current_agent = workflow_context.get("current_agent")

    return {
        "workflow_id": workflow_context.get("workflow_id"),
        "state": state,
        "mode": _workflow_state_to_mode(state),
        "status_text": _workflow_state_to_status_text(state),
        "waiting_label": _workflow_state_to_waiting_label(state),
        "missing_fields": workflow_context.get("missing_fields") or [],
        "approval_required": bool(workflow_context.get("approval_required")),
        "current_agent": AGENT_LABELS.get(current_agent, current_agent) if current_agent else None,
        "current_step_index": int(workflow_context.get("current_step_index") or 0),
        "total_steps": int(workflow_context.get("total_steps") or 0),
    }


def _make_status_chunk(
    completion_id,
    created,
    model,
    agent_name,
    action,
    description="",
    workflow_status: dict[str, Any] | None = None,
):
    chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": ""},
            "finish_reason": None,
        }],
        "agent_status": {
            "agent": agent_name,
            "action": action,
            "description": description,
        },
    }
    if workflow_status:
        chunk["workflow_status"] = workflow_status
    return chunk


def _make_content_chunk(completion_id, created, model, token):
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": token},
            "finish_reason": None,
        }],
    }


def _make_done_chunk(completion_id, created, model):
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop",
        }],
    }


def _make_workflow_chunk(completion_id, created, model, workflow_status: dict[str, Any]):
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": ""},
            "finish_reason": None,
        }],
        "workflow_status": workflow_status,
    }


async def stream_maf(request: ChatCompletionRequest, completion_id: str, created: int):
    """Stream MAF events as SSE chunks with agent status updates."""
    if not maf_orchestrator:
        raise HTTPException(status_code=500, detail="Microsoft Agent Framework yüklenemedi.")

    user_ctx = _extract_request_context(request.messages)
    _ensure_agent_access(user_ctx)
    history = to_agent_history(request.messages)

    initial_status_chunk = _make_status_chunk(
        completion_id,
        created,
        request.model,
        "Planner",
        "analyzing",
        "Plan hazırlanıyor...",
    )
    yield f"data: {json.dumps(initial_status_chunk)}\n\n"

    status_queue = asyncio.Queue()

    async def on_progress(event: dict):
        await status_queue.put(event)

    result_holder = {}
    error_holder = {}

    async def run_maf_task():
        try:
            result = await maf_orchestrator.run(
                history,
                conversation_id=request.conversation_id,
                user_context=user_ctx,
                progress_callback=on_progress,
            )
            result_holder["result"] = result
        except Exception as exc:
            error_holder["error"] = exc
        finally:
            await status_queue.put(None)

    task = asyncio.create_task(run_maf_task())

    while True:
        event = await status_queue.get()
        if event is None:
            break

        event_type = event.get("type")
        workflow_status = _serialize_workflow_status(event.get("workflow_context"))

        if event_type == "plan_ready":
            plan_steps = event.get("plan_steps", [])
            if plan_steps:
                desc = " -> ".join(
                    [
                        AGENT_LABELS.get(
                            step.agent if hasattr(step, "agent") else step.get("agent", ""),
                            "?",
                        )
                        for step in plan_steps
                    ]
                )
                plan_ready_chunk = _make_status_chunk(
                    completion_id,
                    created,
                    request.model,
                    "Planner",
                    "plan_ready",
                    f"Plan: {desc}",
                    workflow_status=workflow_status,
                )
                yield f"data: {json.dumps(plan_ready_chunk)}\n\n"

        elif event_type == "step_start":
            plan_step = event["step"]
            agent_name = plan_step.agent if hasattr(plan_step, "agent") else plan_step.get("agent", "")
            description = (
                plan_step.description
                if hasattr(plan_step, "description")
                else plan_step.get("description", "")
            )
            label = AGENT_LABELS.get(agent_name, agent_name)
            step_start_chunk = _make_status_chunk(
                completion_id,
                created,
                request.model,
                label,
                "working",
                description,
                workflow_status=workflow_status,
            )
            yield f"data: {json.dumps(step_start_chunk)}\n\n"

        elif event_type == "step_end":
            plan_step = event.get("step", {})
            agent_name = plan_step.agent if hasattr(plan_step, "agent") else plan_step.get("agent", "")
            label = AGENT_LABELS.get(agent_name, agent_name)
            output_text = str(event.get("output", ""))[:200]
            step_done_chunk = _make_status_chunk(
                completion_id,
                created,
                request.model,
                label,
                "done",
                output_text,
                workflow_status=workflow_status,
            )
            yield f"data: {json.dumps(step_done_chunk)}\n\n"

        elif event_type == "chat_output":
            chat_output_chunk = _make_status_chunk(
                completion_id,
                created,
                request.model,
                "Sentez",
                "working",
                "Yanıt hazırlanıyor...",
            )
            yield f"data: {json.dumps(chat_output_chunk)}\n\n"

    await task

    final_content = ""
    final_workflow_status = None
    if "error" in error_holder:
        final_content = f"Bir hata oluştu: {error_holder['error']}"
    elif "result" in result_holder:
        final_result = result_holder["result"]
        final_content = final_result.final_text
        final_workflow_status = _serialize_workflow_status(
            maf_orchestrator._serialize_workflow_context(final_result.workflow_context)
            if final_result.workflow_context
            else None
        )

    if final_workflow_status:
        yield f"data: {json.dumps(_make_workflow_chunk(completion_id, created, request.model, final_workflow_status))}\n\n"

    if final_content:
        words = final_content.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else " " + word
            yield f"data: {json.dumps(_make_content_chunk(completion_id, created, request.model, token))}\n\n"
            await asyncio.sleep(0.02)

    yield f"data: {json.dumps(_make_done_chunk(completion_id, created, request.model))}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    try:
        completion_id = f"chatcmpl-{uuid.uuid4()}"
        created = int(time.time())

        if not request.stream:
            if not maf_orchestrator:
                raise HTTPException(status_code=500, detail="MAF yüklenemedi.")
            user_ctx = _extract_request_context(request.messages)
            _ensure_agent_access(user_ctx)
            history = to_agent_history(request.messages)
            result = await maf_orchestrator.run(
                history,
                conversation_id=request.conversation_id,
                user_context=user_ctx,
            )
            final_content = result.final_text

            return ChatCompletionResponse(
                id=completion_id,
                created=created,
                model=request.model,
                choices=[
                    ChatCompletionResponseChoice(
                        index=0,
                        message=ResponseMessage(role="assistant", content=final_content),
                        finish_reason="stop",
                    )
                ],
            )

        generator = stream_maf(request, completion_id, created)
        return StreamingResponse(generator, media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Beklenmeyen backend hatası: %s", exc)
        raise HTTPException(status_code=500, detail="Beklenmeyen bir sunucu hatası oluştu.")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9099, reload=True)
