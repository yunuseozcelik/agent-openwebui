import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Union, Any
import time
import uuid

# Kendi graph yapını import et
from config import OPENAI_API_KEY  # dotenv yüklenmesini tetikler
from graph.builder import build_graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from utils.context import extract_ow_context

app = FastAPI(title="IFS Corporate AI Server")

# Graph'ı bir kere yükle
try:
    graph = build_graph()
    print("[OK] Supervisor Ajani Hazir ve Bekliyor...")
except Exception as e:
    print(f"[HATA] Graph yuklenirken hata: {e}")
    graph = None


# --- OpenAI Uyumlu Veri Modelleri (REQUEST) ---
class Message(BaseModel):
    role: str
    content: Union[str, List[Any]]  # string veya content-parts listesi


class ChatCompletionRequest(BaseModel):
    model: str = "ifs-agent"
    messages: List[Message]
    stream: bool = False


# --- OpenAI Uyumlu Veri Modelleri (RESPONSE) ---
class ResponseMessage(BaseModel):
    role: str
    content: str  # 5ire/OpenWebUI için daima string dön


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


# --- MODEL LİSTESİ ENDPOINT'İ ---
@app.get("/v1/models")
async def list_models():
    """Open WebUI / 5ire model listesini görsün diye"""
    return {
        "object": "list",
        "data": [
            {
                "id": "ifs-agent",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "ifs-corporate-ai",
            }
        ],
    }


def normalize_content(content) -> str:
    """Request/Graph content'ini daima string'e çevir."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict):
                # OpenAI "content parts" formatı
                if part.get("type") == "text" and isinstance(part.get("text"), str):
                    texts.append(part["text"])
                # Bazı istemciler {"text": "..."} gibi de yollayabiliyor
                elif isinstance(part.get("text"), str):
                    texts.append(part["text"])
        return "\n".join(texts).strip()

    return str(content)


def extract_final_text(messages) -> str:
    """
    Graph çıktısı bazen en sonda tool/structured message bırakabiliyor.
    Sondan geriye doğru gidip "string'e normalize edilebilir" en son dolu metni al.
    """
    for msg in reversed(messages):
        c = getattr(msg, "content", "")
        text = normalize_content(c)
        if isinstance(text, str) and text.strip():
            return text
    return ""


# --- CHAT COMPLETION ENDPOINT ---
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    if not graph:
        raise HTTPException(status_code=500, detail="Agent Graph yüklenemedi.")

    try:
        # 1) Mesajları LangChain formatına çevir (normalize ederek)
        langchain_messages = []
        for m in request.messages:
            content_text = normalize_content(m.content)

            if m.role == "user":
                langchain_messages.append(HumanMessage(content=content_text))
            elif m.role == "assistant":
                langchain_messages.append(AIMessage(content=content_text))
            elif m.role == "system":
                langchain_messages.append(SystemMessage(content=content_text))

        # 2) Kullanıcı context'ini çıkar ve graph'a aktar
        user_ctx = extract_ow_context(langchain_messages)
        inputs = {"messages": langchain_messages, "user_context": user_ctx}
        config = {"configurable": {"thread_id": user_ctx.get("user_email") or "api_user"}}

        result = graph.invoke(inputs, config=config)

        # 3) Son cevabı güvenli şekilde al (daima string)
        final_content = extract_final_text(result.get("messages", []))

        # 4) OpenAI uyumlu yanıt dön
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

    except Exception as e:
        print(f"HATA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=9099, reload=True)
