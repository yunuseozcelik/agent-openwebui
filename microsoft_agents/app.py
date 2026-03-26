"""
Chainlit UI for the Microsoft Agent Framework flow only.

Run with:
chainlit run microsoft_agents/app.py
"""

from __future__ import annotations

import asyncio

import chainlit as cl

try:
    from .agent_setup import AGENT_LABELS
    from .orchestrator import MicrosoftAgentOrchestrator
except ImportError:
    from agent_setup import AGENT_LABELS
    from orchestrator import MicrosoftAgentOrchestrator


orchestrator = MicrosoftAgentOrchestrator()


def build_checklist(plan_steps, completed=None):
    completed = completed or set()
    lines = []
    for index, step in enumerate(plan_steps):
        label = AGENT_LABELS.get(step.agent, step.agent)
        if index in completed:
            lines.append(f"~~Adim {index + 1}: {step.description}~~ **Tamamlandi**")
        else:
            lines.append(f"**Adim {index + 1}:** {step.description}")
    return "\n".join(lines)


async def stream_final_answer(text: str) -> None:
    msg = cl.Message(content="")
    await msg.send()
    for char in text:
        await msg.stream_token(char)
        await asyncio.sleep(0.008)
    await msg.update()


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("conversation_history", [])
    await cl.Message(
        content=(
            "Merhaba! Ben IFS Kurumsal Asistaniyim.\n\n"
            "Bu oturumda Microsoft Agent Framework tabanli uzman ajan yapisi aktif."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    history = cl.user_session.get("conversation_history", [])
    history.append({"role": "user", "content": message.content})

    checklist_msg = None
    completed_steps = set()
    latest_plan = []

    step = cl.Step(name="Supervisor", type="tool")
    step.input = "Mesajiniz analiz ediliyor..."
    await step.send()

    async def on_progress(event: dict):
        nonlocal checklist_msg, latest_plan
        event_type = event.get("type")

        if event_type == "plan_ready":
            latest_plan = event.get("plan_steps", [])
            if len(latest_plan) > 1:
                checklist_msg = cl.Message(content=build_checklist(latest_plan, completed_steps))
                await checklist_msg.send()
            elif not latest_plan:
                step.name = "Genel Sohbet"
                step.input = "Sohbet modu aktif"
                await step.update()

        elif event_type == "step_start":
            plan_step = event["step"]
            step.name = AGENT_LABELS.get(plan_step.agent, plan_step.agent)
            step.input = plan_step.description
            step.output = ""
            await step.update()

        elif event_type == "step_end":
            step.output = event.get("output", "")[:300]
            await step.update()
            completed_steps.add(event["index"])
            if checklist_msg and latest_plan:
                checklist_msg.content = build_checklist(latest_plan, completed_steps)
                await checklist_msg.update()

        elif event_type == "chat_output":
            step.output = "Yanit hazirlaniyor..."
            await step.update()

    try:
        result = await orchestrator.run(history, progress_callback=on_progress)
    except Exception as exc:
        step.output = f"Hata: {exc}"
        await step.update()
        return

    try:
        await step.remove()
    except Exception:
        pass

    if checklist_msg and result.plan_steps:
        checklist_msg.content = build_checklist(result.plan_steps, set(range(len(result.plan_steps))))
        await checklist_msg.update()

    history.append({"role": "assistant", "content": result.final_text})
    cl.user_session.set("conversation_history", history)
    await stream_final_answer(result.final_text)
