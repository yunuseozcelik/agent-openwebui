"""
Chainlit UI ile Microsoft Azure AI Agent Service entegrasyonu.
Multi-agent supervisor sistemini gorsel arayuzde calistirir.

Calistirmak icin:
    chainlit run app.py
"""

import asyncio
import json

import chainlit as cl
from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
)
from agents import (
    SUPERVISOR_SYSTEM_PROMPT,
    HR_SYSTEM_PROMPT,
    IT_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
)
from tools import (
    HR_TOOL_DEFINITIONS,
    IT_TOOL_DEFINITIONS,
    TOOL_FUNCTIONS,
)


def get_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


# ------------------------------------------------------------------
# Supervisor: mesaji analiz edip hangi agent'a yonlendirecegine karar verir
# ------------------------------------------------------------------
def _run_supervisor(client: AzureOpenAI, messages: list[dict]) -> str:
    supervisor_messages = [
        {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
        {"role": "user", "content": messages[-1]["content"] if messages else "merhaba"},
    ]
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=supervisor_messages,
        temperature=0,
        max_tokens=50,
        response_format={"type": "json_object"},
    )
    try:
        result = json.loads(response.choices[0].message.content)
        next_agent = result.get("next", "CHAT")
        if next_agent not in ("HR_Agent", "IT_Agent", "CHAT"):
            next_agent = "CHAT"
        return next_agent
    except (json.JSONDecodeError, KeyError):
        return "CHAT"


# ------------------------------------------------------------------
# Worker agent: tool calling ile gorevini yerine getirir
# ------------------------------------------------------------------
def _run_worker_agent(
    client: AzureOpenAI,
    messages: list[dict],
    system_prompt: str,
    tool_definitions: list[dict],
) -> tuple[str, list[dict]]:
    """Worker agent calistirir. (sonuc_metni, tool_call_bilgileri) doner."""
    agent_messages = [{"role": "system", "content": system_prompt}, *messages]

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=agent_messages,
        tools=tool_definitions,
        tool_choice="auto",
        temperature=0.3,
    )
    assistant_message = response.choices[0].message
    tool_call_infos = []

    if assistant_message.tool_calls:
        agent_messages.append(assistant_message)

        for tool_call in assistant_message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            fn = TOOL_FUNCTIONS.get(fn_name)
            if fn:
                result = fn(**fn_args)
            else:
                result = json.dumps({"error": f"Bilinmeyen tool: {fn_name}"})

            tool_call_infos.append({
                "name": fn_name,
                "args": fn_args,
                "result": result,
            })

            agent_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        second_response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=agent_messages,
            temperature=0.3,
        )
        return second_response.choices[0].message.content, tool_call_infos

    return assistant_message.content, tool_call_infos


# ------------------------------------------------------------------
# Chat agent (tool kullanmaz)
# ------------------------------------------------------------------
def _run_chat_agent(client: AzureOpenAI, messages: list[dict]) -> str:
    chat_messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}, *messages]
    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=chat_messages,
        temperature=0.7,
    )
    return response.choices[0].message.content


# ==================================================================
# CHAINLIT EVENT HANDLERS
# ==================================================================

@cl.on_chat_start
async def on_chat_start():
    client = get_client()
    cl.user_session.set("client", client)
    cl.user_session.set("messages", [])

    await cl.Message(
        content="Merhaba! Ben IFS Kurumsal AI Asistaniyim.\n\n"
        "Size su konularda yardimci olabilirim:\n"
        "- **IK**: Izin talebi, izin bakiyesi, maas, personel bilgileri\n"
        "- **IT**: Bilgisayar arizasi, donanim talebi, teknik destek\n"
        "- **Genel sohbet**: Her turlu soru ve bilgi\n\n"
        "Nasil yardimci olabilirim?"
    ).send()


@cl.on_message
async def on_message(msg: cl.Message):
    client = cl.user_session.get("client")
    messages: list[dict] = cl.user_session.get("messages")

    messages.append({"role": "user", "content": msg.content})

    # 1) Supervisor yonlendirmesi
    async with cl.Step(name="Supervisor", type="llm") as supervisor_step:
        supervisor_step.input = msg.content
        next_agent = await asyncio.to_thread(_run_supervisor, client, messages)
        label = {"HR_Agent": "IK Asistani", "IT_Agent": "IT Destek", "CHAT": "Genel Sohbet"}
        supervisor_step.output = f"Yonlendirme: **{label.get(next_agent, next_agent)}**"

    # 2) Ilgili agent'i calistir
    if next_agent == "HR_Agent":
        async with cl.Step(name="IK Asistani", type="llm") as agent_step:
            agent_step.input = msg.content
            result, tool_calls = await asyncio.to_thread(
                _run_worker_agent, client, messages, HR_SYSTEM_PROMPT, HR_TOOL_DEFINITIONS
            )
            # Tool call'lari ic step olarak goster
            for tc in tool_calls:
                async with cl.Step(name=tc["name"], type="tool") as tool_step:
                    tool_step.input = json.dumps(tc["args"], ensure_ascii=False, indent=2)
                    tool_step.output = tc["result"]
            agent_step.output = result

    elif next_agent == "IT_Agent":
        async with cl.Step(name="IT Destek", type="llm") as agent_step:
            agent_step.input = msg.content
            result, tool_calls = await asyncio.to_thread(
                _run_worker_agent, client, messages, IT_SYSTEM_PROMPT, IT_TOOL_DEFINITIONS
            )
            for tc in tool_calls:
                async with cl.Step(name=tc["name"], type="tool") as tool_step:
                    tool_step.input = json.dumps(tc["args"], ensure_ascii=False, indent=2)
                    tool_step.output = tc["result"]
            agent_step.output = result

    else:
        async with cl.Step(name="Genel Sohbet", type="llm") as agent_step:
            agent_step.input = msg.content
            result = await asyncio.to_thread(_run_chat_agent, client, messages)
            agent_step.output = result

    # Mesaj gecmisini guncelle
    messages.append({"role": "assistant", "content": result})
    cl.user_session.set("messages", messages)

    # Son cevabi gonder
    await cl.Message(content=result).send()
