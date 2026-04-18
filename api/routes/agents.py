"""Agents endpoints — list, detail, chat, delete."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from agent_factory.deployment.foundry_client import (
    AgentInfo,
    get_agent_detail,
    list_agents,
)
from agent_factory.runner import AgentRunner

from ..schemas import AgentSummary, ChatRequest, ChatResponse
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
            # Basit chunking — gercek streaming icin runner yeniden yazilabilir
            chunk_size = 18
            for i in range(0, len(text), chunk_size):
                yield sse_event("chunk", {"text": text[i:i + chunk_size]})
                await asyncio.sleep(0.015)
            yield sse_event("done", {"full": text})
        except Exception as exc:
            yield sse_event("error", {"message": str(exc)})

    return EventSourceResponse(generator())


@router.post("/session/new")
async def new_session():
    return {"session_id": f"sess_{uuid.uuid4().hex[:12]}"}
