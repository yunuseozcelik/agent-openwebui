import os
import time
import uuid
from typing import Any, List, Union

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from graph.builder import build_graph
from microsoft_agents.orchestrator import MicrosoftAgentOrchestrator
from utils.context import extract_ow_context
from utils.cost_control import cost_tracker


app = FastAPI(title="IFS Corporate AI Server")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

LANGGRAPH_MODEL_ID = "ifs-agent"
MAF_MODEL_ID = "ifs-microsoft-agent"


@app.get("/")
async def chat_ui():
    return FileResponse(os.path.join(STATIC_DIR, "chat.html"))


@app.get("/gateway")
async def gateway_ui():
    return FileResponse(os.path.join(STATIC_DIR, "gateway.html"))


@app.get("/dashboard")
async def dashboard_ui():
    return FileResponse(os.path.join(STATIC_DIR, "gateway.html"))


@app.get("/api/control-panel")
async def get_control_panel():
    return cost_tracker.snapshot()


@app.post("/api/control-panel/reset")
async def reset_control_panel():
    cost_tracker.reset()
    return {"ok": True}


try:
    langgraph_graph = build_graph()
    print("[OK] LangGraph supervisor hazir.")
except Exception as exc:
    print(f"[HATA] LangGraph yuklenirken hata: {exc}")
    langgraph_graph = None

try:
    maf_orchestrator = MicrosoftAgentOrchestrator()
    print("[OK] Microsoft Agent Framework orchestrator hazir.")
except Exception as exc:
    print(f"[HATA] Microsoft Agent Framework yuklenirken hata: {exc}")
    maf_orchestrator = None


class Message(BaseModel):
    role: str
    content: Union[str, List[Any]]


class ChatCompletionRequest(BaseModel):
    model: str = LANGGRAPH_MODEL_ID
    messages: List[Message]
    stream: bool = False


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
                "id": LANGGRAPH_MODEL_ID,
                "object": "model",
                "created": now,
                "owned_by": "ifs-corporate-ai",
            },
            {
                "id": MAF_MODEL_ID,
                "object": "model",
                "created": now,
                "owned_by": "ifs-corporate-ai",
            },
        ],
    }


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


def extract_final_text(messages) -> str:
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        text = normalize_content(content)
        if isinstance(text, str) and text.strip():
            return text
    return ""


def to_langchain_messages(request_messages: List[Message]):
    messages = []
    for item in request_messages:
        content_text = normalize_content(item.content)
        if item.role == "user":
            messages.append(HumanMessage(content=content_text))
        elif item.role == "assistant":
            messages.append(AIMessage(content=content_text))
        elif item.role == "system":
            messages.append(SystemMessage(content=content_text))
    return messages


def to_agent_history(request_messages: List[Message]) -> list[dict[str, str]]:
    history = []
    for item in request_messages:
        if item.role not in {"user", "assistant", "system"}:
            continue
        history.append(
            {
                "role": item.role,
                "content": normalize_content(item.content),
            }
        )
    return history


async def run_langgraph(request: ChatCompletionRequest) -> str:
    if not langgraph_graph:
        raise HTTPException(status_code=500, detail="LangGraph agent yuklenemedi.")

    cost_tracker.record_request("langgraph")
    langchain_messages = to_langchain_messages(request.messages)
    user_ctx = extract_ow_context(langchain_messages)
    inputs = {"messages": langchain_messages, "user_context": user_ctx}
    config = {"configurable": {"thread_id": user_ctx.get("user_email") or "api_user"}}
    result = langgraph_graph.invoke(inputs, config=config)
    return extract_final_text(result.get("messages", []))


async def run_maf(request: ChatCompletionRequest) -> str:
    if not maf_orchestrator:
        raise HTTPException(status_code=500, detail="Microsoft Agent Framework yuklenemedi.")

    langchain_messages = to_langchain_messages(request.messages)
    user_ctx = extract_ow_context(langchain_messages)
    history = to_agent_history(request.messages)
    result = await maf_orchestrator.run(history, user_context=user_ctx)
    return result.final_text


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    try:
        if request.model == MAF_MODEL_ID:
            final_content = await run_maf(request)
        else:
            final_content = await run_langgraph(request)

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4()}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=ResponseMessage(role="assistant", content=final_content),
                    finish_reason="stop",
                )
            ],
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"HATA: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9099, reload=True)
