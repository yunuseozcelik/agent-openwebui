"""
Chainlit UI - Microsoft Agent Framework ile IFS Kurumsal Asistan.
Calistirmak icin: chainlit run app.py
"""

import chainlit as cl
from agent_framework import AgentResponse
from agent_framework.orchestrations import HandoffAgentUserRequest

from agent_setup import build_handoff_workflow


@cl.on_chat_start
async def on_chat_start():
    """Sohbet basladiginda workflow olustur ve session'a kaydet."""
    workflow = build_handoff_workflow()
    cl.user_session.set("workflow", workflow)
    cl.user_session.set("started", False)
    cl.user_session.set("pending_requests", [])

    await cl.Message(
        content=(
            "Merhaba! Ben IFS Kurumsal Asistaniyim (Microsoft Agent Framework).\n\n"
            "Size su konularda yardimci olabilirim:\n"
            "- **HR**: Izin sorgulama, izin talebi, maas bordrosu, personel bilgileri\n"
            "- **IT**: Destek talebi, ekipman talebi, ticket takibi\n"
            "- **Finans**: Avans talebi, harcama raporu\n"
            "- **Genel**: Yemek menusu, parca sorgulama\n\n"
            "Nasil yardimci olabilirim?"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Kullanici mesajini agent workflow'una gonder."""
    workflow = cl.user_session.get("workflow")
    started = cl.user_session.get("started")
    pending = cl.user_session.get("pending_requests")

    thinking_msg = cl.Message(content="")
    await thinking_msg.send()

    try:
        if pending:
            # Pending request'lere cevap gonder
            responses = {
                req.request_id: HandoffAgentUserRequest.create_response(message.content)
                for req in pending
            }
            events = await workflow.run(responses=responses)
            response_text, new_pending = _process_events(events)
            cl.user_session.set("pending_requests", new_pending)

        elif not started:
            # Ilk mesaj: workflow'u baslat
            cl.user_session.set("started", True)
            events = []
            async for event in workflow.run(message.content, stream=True):
                events.append(event)
            response_text, new_pending = _process_events(events)
            cl.user_session.set("pending_requests", new_pending)

        else:
            # Yeni konusma: workflow'u yeniden olustur
            workflow = build_handoff_workflow()
            cl.user_session.set("workflow", workflow)
            events = []
            async for event in workflow.run(message.content, stream=True):
                events.append(event)
            response_text, new_pending = _process_events(events)
            cl.user_session.set("pending_requests", new_pending)

        thinking_msg.content = response_text or "Islem tamamlandi."
        await thinking_msg.update()

    except Exception as e:
        thinking_msg.content = f"Bir hata olustu: {str(e)}"
        await thinking_msg.update()


def _process_events(events) -> tuple[str, list]:
    """Workflow event'lerini isleyerek yanit metnini ve pending request'leri cikarir."""
    response_parts = []
    pending_requests = []

    for event in events:
        if event.type == "handoff_sent":
            source = event.data.source
            target = event.data.target
            print(f"[HANDOFF] {source} -> {target}")

        elif event.type == "output":
            data = event.data
            if isinstance(data, AgentResponse):
                for msg in data.messages:
                    if msg.text:
                        response_parts.append(msg.text)

        elif event.type == "request_info" and isinstance(event.data, HandoffAgentUserRequest):
            agent_resp = event.data.agent_response
            if agent_resp and agent_resp.messages:
                for msg in agent_resp.messages:
                    if msg.text:
                        response_parts.append(msg.text)
            pending_requests.append(event)

    response_text = "\n\n".join(response_parts) if response_parts else ""
    return response_text, pending_requests
