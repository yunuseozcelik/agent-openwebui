"""
Microsoft Azure AI Agent Service - FastAPI Server
OpenAI-uyumlu /v1/chat/completions endpoint'i sunar.
Mevcut LangGraph projesiyle ayni API formatini kullanir,
boylece Open WebUI'den dogrudan test edilebilir.
"""

import time
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Union, Any

from agents import process_message
from config import AZURE_OPENAI_ENDPOINT

app = FastAPI(title="IFS Corporate AI Server (Azure)")


# --- Baslangic kontrolu ---
@app.on_event("startup")
async def startup_check():
    if not AZURE_OPENAI_ENDPOINT:
        print("[UYARI] AZURE_OPENAI_ENDPOINT ayarlanmamis! .env dosyasini kontrol edin.")
    else:
        print(f"[OK] Azure Agent Sistemi Hazir - Endpoint: {AZURE_OPENAI_ENDPOINT}")


# --- OpenAI Uyumlu Veri Modelleri ---
class Message(BaseModel):
    role: str
    content: Union[str, List[Any]]


class ChatCompletionRequest(BaseModel):
    model: str = "azure-agent"
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


# --- MODEL LiSTESi ---
@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "azure-agent",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "azure-ai-agent-service",
            }
        ],
    }


def normalize_content(content) -> str:
    """Content'i string'e cevirir (OpenAI content parts destegi)."""
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


# --- CHAT COMPLETION ENDPOINT ---
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    try:
        # Mesajlari OpenAI formatina cevir
        messages = []
        for m in request.messages:
            content_text = normalize_content(m.content)
            if m.role in ("user", "assistant", "system"):
                messages.append({"role": m.role, "content": content_text})

        # Agent sistemini calistir
        final_content = process_message(messages)

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4()}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=ResponseMessage(role="assistant", content=final_content or ""),
                    finish_reason="stop",
                )
            ],
        )

    except Exception as e:
        print(f"[HATA] {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9098, reload=True)
