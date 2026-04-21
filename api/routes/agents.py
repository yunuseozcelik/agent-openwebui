"""Agents endpoints — list, detail, chat, delete."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agent_factory.deployment.foundry_client import (
    AgentInfo,
    delete_agent as foundry_delete_agent,
    get_agent_detail,
    list_agents,
    update_agent_local,
)
from agent_factory.runner import AgentRunner
from agent_factory.orchestrator import orchestrate

from ..schemas import (
    AgentDeleteResponse,
    AgentSummary,
    AgentUpdateRequest,
    AgentUpdateResponse,
    ChatRequest,
    ChatResponse,
)
from ..sessions import session_store
from ..streaming import sse_event


router = APIRouter(prefix="/api/agents", tags=["agents"])


def _to_summary(a: AgentInfo) -> AgentSummary:
    status = "active"
    if a.metadata.get("mock"):
        status = "mock"
    elif a.metadata.get("status") == "draft":
        status = "draft"

    tools = []
    for t in a.tools:
        if isinstance(t, dict):
            tools.append(t)
        else:
            tools.append({"type": str(t)})

    return AgentSummary(
        id=a.id,
        name=a.name,
        model=a.model or "",
        instructions=a.instructions or "",
        tools=tools,
        metadata=a.metadata or {},
        source=a.source,
        status=status,
    )


@router.get("", response_model=list[AgentSummary])
async def get_agents():
    return [_to_summary(a) for a in list_agents()]


@router.get("/{agent_id}", response_model=AgentSummary)
async def get_agent(agent_id: str):
    a = get_agent_detail(agent_id)
    if not a:
        raise HTTPException(status_code=404, detail="Agent bulunamadi")
    return _to_summary(a)


def _get_or_create_runner(session_id: str, agent_id: str) -> AgentRunner:
    session = session_store.get(session_id)
    if agent_id in session.runners:
        return session.runners[agent_id]

    info = get_agent_detail(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail="Agent bulunamadi")

    runner = AgentRunner(info)
    session.runners[agent_id] = runner
    return runner


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    runner = _get_or_create_runner(req.session_id, req.agent_id)
    try:
        text = await runner.send(req.message)
        return ChatResponse(content=text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """SSE chunk-based stream (simulasyon — gercek token streami icin runner guncellenir)."""
    runner = _get_or_create_runner(req.session_id, req.agent_id)

    async def generator():
        yield sse_event("start", {})
        try:
            text = await runner.send(req.message)
            # Kelime kelime streaming animasyonu
            words = text.split(" ")
            buf = ""
            for i, word in enumerate(words):
                buf += ("" if i == 0 else " ") + word
                if len(buf) >= 6 or i == len(words) - 1:
                    yield sse_event("chunk", {"text": buf})
                    buf = ""
                    await asyncio.sleep(0.045)
            yield sse_event("done", {"full": text})
        except Exception as exc:
            yield sse_event("error", {"message": str(exc)})

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(generator(), media_type="text/event-stream", headers=headers)


@router.post("/chat/orchestrate")
async def chat_orchestrate(req: ChatRequest):
    """Supervisor → Alt Agent'lar → Synthesis akisini SSE olarak yayinlar."""

    _SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

    async def generator():
        yield sse_event("start", {})
        try:
            async for step in orchestrate(req.message):
                if step.type == "routing":
                    yield sse_event("routing", {
                        "agent": step.agent,
                        "selected": step.selected,
                        "text": step.text,
                    })
                elif step.type == "agent_start":
                    yield sse_event("agent_start", {"agent": step.agent})
                elif step.type == "agent_done":
                    yield sse_event("agent_done", {
                        "agent": step.agent,
                        "text": step.text,
                    })
                elif step.type == "synthesis":
                    yield sse_event("synthesis", {"agent": step.agent})
                elif step.type == "done":
                    # Final cevabi kelime kelime stream et
                    words = step.text.split(" ")
                    buf = ""
                    for i, word in enumerate(words):
                        buf += ("" if i == 0 else " ") + word
                        if len(buf) >= 6 or i == len(words) - 1:
                            yield sse_event("chunk", {"text": buf})
                            buf = ""
                            await asyncio.sleep(0.045)
                    yield sse_event("done", {"full": step.text})
                elif step.type == "error":
                    yield sse_event("error", {"message": step.text})
        except Exception as exc:
            yield sse_event("error", {"message": str(exc)})

    return StreamingResponse(generator(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.patch("/{agent_id}", response_model=AgentUpdateResponse)
async def update_agent(agent_id: str, req: AgentUpdateRequest):
    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Guncelleme alani belirtilmedi")
    updated = update_agent_local(agent_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Agent bulunamadi veya guncellenemedi")
    return AgentUpdateResponse(success=True, agent=_to_summary(updated))


@router.delete("/{agent_id}", response_model=AgentDeleteResponse)
async def delete_agent_route(agent_id: str):
    seed_names = {
        "Supervisor-Agent", "Synthesis-Agent",
        "HR-Agent", "IT-Agent", "Finance-Agent",
        "Math-Agent", "General-Agent", "Chat-Agent",
    }
    # Strip ":version" suffix that appears in Foundry-listed agent ids
    bare_id = agent_id.split(":", 1)[0] if ":" in agent_id else agent_id
    if bare_id in seed_names or agent_id in seed_names:
        raise HTTPException(status_code=403, detail="Sistem agentlari silinemez")
    deleted = foundry_delete_agent(bare_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent bulunamadi")
    return AgentDeleteResponse(success=True)


@router.post("/session/new")
async def new_session():
    return {"session_id": f"sess_{uuid.uuid4().hex[:12]}"}
