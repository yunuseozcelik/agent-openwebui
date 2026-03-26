"""
Unified Chainlit UI for LangGraph and Microsoft Agent Framework.

Run with:
chainlit run app_chainlit.py -w --port 8501
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import chainlit as cl
import pandas as pd
import plotly.graph_objects as go
from langchain_core.messages import AIMessage, HumanMessage

from graph.builder import build_graph
from microsoft_agents.agent_setup import AGENT_LABELS
from microsoft_agents.orchestrator import MicrosoftAgentOrchestrator
from utils.cost_control import cost_tracker


LANGGRAPH_PROFILE = "LangGraph Chat"
MAF_PROFILE = "Microsoft Agent Framework"
GATEWAY_PROFILE = "Gateway / Portkey"

graph = build_graph()
maf_orchestrator = MicrosoftAgentOrchestrator()


def to_str(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif "text" in item and item.get("type") not in ("reasoning", "summary"):
                    parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts).strip()
    return str(content) if content else ""


def build_checklist(plan_steps, completed=None):
    completed = completed or set()
    lines = []
    for index, step in enumerate(plan_steps):
        agent_name = step.agent if hasattr(step, "agent") else step.get("agent", "")
        description = step.description if hasattr(step, "description") else step.get("description", "")
        label = AGENT_LABELS.get(agent_name, agent_name)
        if index in completed:
            lines.append(f"~~Adim {index + 1}: {description}~~ **Tamamlandi**")
        else:
            lines.append(f"**Adim {index + 1}:** {description}")
    return "\n".join(lines)


def _format_usd(value: float) -> str:
    return f"${value:.4f}" if value < 0.01 else f"${value:.2f}"


def _format_int(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def build_gateway_markdown(snapshot: dict) -> str:
    gateway = snapshot.get("gateway", {})
    totals = snapshot.get("totals", {})
    budget = snapshot.get("budget", {})
    recent = snapshot.get("recent", [])[:8]
    engines = snapshot.get("engines", {})
    models = snapshot.get("models", {})

    lines = [
        "## Portkey Gateway Panel",
        "",
        f"- Durum: {'Aktif' if gateway.get('enabled') else 'Kapali'}",
        f"- Mod: `{gateway.get('mode', '-')}`",
        f"- Provider: `{gateway.get('provider', '-')}`",
        f"- Base URL: `{gateway.get('base_url', '-')}`",
        f"- Dashboard: {gateway.get('dashboard_url', 'https://app.portkey.ai')}",
        "",
        "### Toplam",
        f"- Tahmini maliyet: `{_format_usd(float(totals.get('estimated_cost_usd', 0.0)))}`",
        f"- Toplam token: `{_format_int(int(totals.get('total_tokens', 0)))}`",
        f"- LLM cagrisi: `{_format_int(int(totals.get('llm_calls', 0)))}`",
        f"- Butce kullanimi: `%{budget.get('used_percent', 0)}`",
        "",
        "### Motorlar",
    ]

    if engines:
        for engine_name, item in engines.items():
            display = "Microsoft Agent Framework" if engine_name == "maf" else "LangGraph"
            lines.append(
                f"- {display}: `{_format_usd(float(item.get('estimated_cost_usd', 0.0)))}` | "
                f"`{_format_int(int(item.get('total_tokens', 0)))}` token | "
                f"`{_format_int(int(item.get('llm_calls', 0)))}` cagri"
            )
    else:
        lines.append("- Henuz kayit yok.")

    lines.extend(["", "### Modeller"])
    if models:
        for model_name, item in models.items():
            lines.append(
                f"- `{model_name}`: `{_format_usd(float(item.get('estimated_cost_usd', 0.0)))}` | "
                f"`{_format_int(int(item.get('total_tokens', 0)))}` token"
            )
    else:
        lines.append("- Henuz model verisi yok.")

    lines.extend(["", "### Son Cagrilar"])
    if recent:
        for item in recent:
            ts = item.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M:%S")
            except Exception:
                pass
            lines.append(
                f"- `{ts}` | `{item.get('engine', '-')}/{item.get('component', '-')}` | "
                f"`{item.get('model_id', '-')}` | "
                f"`{_format_usd(float(item.get('estimated_cost_usd', 0.0)))}` | "
                f"`{_format_int(int(item.get('total_tokens', 0)))}` token"
            )
    else:
        lines.append("- Henuz cagri kaydi yok.")

    lines.extend(
        [
            "",
            "### Not",
            "- Bu ekran yerel telemetry verisini gosterir.",
            "- Portkey web panelinde gorunurluk icin uygulamayi bu ayarlarla yeniden baslatip yeni istek gondermen gerekir.",
        ]
    )

    return "\n".join(lines)


def build_gateway_elements(snapshot: dict) -> list:
    totals = snapshot.get("totals", {})
    engines = snapshot.get("engines", {})
    models = snapshot.get("models", {})
    recent = snapshot.get("recent", [])[:12]

    engine_rows = []
    for engine_name, item in engines.items():
        engine_rows.append(
            {
                "Framework": "Microsoft Agent Framework" if engine_name == "maf" else "LangGraph",
                "Requests": int(item.get("requests", 0)),
                "LLM Calls": int(item.get("llm_calls", 0)),
                "Tokens": int(item.get("total_tokens", 0)),
                "Estimated Cost (USD)": round(float(item.get("estimated_cost_usd", 0.0)), 6),
            }
        )
    if not engine_rows:
        engine_rows.append(
            {
                "Framework": "No data",
                "Requests": 0,
                "LLM Calls": 0,
                "Tokens": 0,
                "Estimated Cost (USD)": 0.0,
            }
        )

    model_rows = []
    for model_name, item in models.items():
        model_rows.append(
            {
                "Model": model_name,
                "LLM Calls": int(item.get("llm_calls", 0)),
                "Tokens": int(item.get("total_tokens", 0)),
                "Estimated Cost (USD)": round(float(item.get("estimated_cost_usd", 0.0)), 6),
            }
        )
    if not model_rows:
        model_rows.append(
            {
                "Model": "No data",
                "LLM Calls": 0,
                "Tokens": 0,
                "Estimated Cost (USD)": 0.0,
            }
        )

    recent_rows = []
    for item in recent:
        recent_rows.append(
            {
                "Time": item.get("timestamp", ""),
                "Framework": item.get("engine", "-"),
                "Component": item.get("component", "-"),
                "Model": item.get("model_id", "-"),
                "Tokens": int(item.get("total_tokens", 0)),
                "Estimated Cost (USD)": round(float(item.get("estimated_cost_usd", 0.0)), 6),
            }
        )
    if not recent_rows:
        recent_rows.append(
            {
                "Time": "-",
                "Framework": "-",
                "Component": "-",
                "Model": "-",
                "Tokens": 0,
                "Estimated Cost (USD)": 0.0,
            }
        )

    engine_df = pd.DataFrame(engine_rows)
    model_df = pd.DataFrame(model_rows)
    recent_df = pd.DataFrame(recent_rows)

    fig = go.Figure()
    fig.add_bar(
        x=engine_df["Framework"],
        y=engine_df["Estimated Cost (USD)"],
        marker_color=["#355bff", "#ff6a3d"][: len(engine_df)],
        text=engine_df["Estimated Cost (USD)"],
        textposition="outside",
    )
    fig.update_layout(
        title="Framework Bazli Tahmini Maliyet",
        template="plotly_white",
        height=360,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_title="Framework",
        yaxis_title="USD",
    )

    total_cost = float(totals.get("estimated_cost_usd", 0.0))
    total_tokens = int(totals.get("total_tokens", 0))
    total_calls = int(totals.get("llm_calls", 0))
    total_requests = int(snapshot.get("total_requests", 0))
    budget = snapshot.get("budget", {})

    hero = cl.Text(
        name="gateway-kpi",
        display="inline",
        content=(
            "### Dashboard Ozeti\n"
            f"- Toplam tahmini maliyet: `{_format_usd(total_cost)}`\n"
            f"- Toplam token: `{_format_int(total_tokens)}`\n"
            f"- Toplam LLM cagrisi: `{_format_int(total_calls)}`\n"
            f"- Toplam istek: `{_format_int(total_requests)}`\n"
            f"- Butce kullanimi: `%{budget.get('used_percent', 0)}`"
        ),
    )

    engine_element = cl.Dataframe(
        name="framework-costs",
        display="inline",
        data=engine_df,
    )
    model_element = cl.Dataframe(
        name="model-costs",
        display="inline",
        data=model_df,
    )
    recent_element = cl.Dataframe(
        name="recent-calls",
        display="inline",
        data=recent_df,
    )
    plot_element = cl.Plotly(
        name="framework-chart",
        display="inline",
        figure=fig,
    )

    return [hero, plot_element, engine_element, model_element, recent_element]


async def send_gateway_dashboard() -> None:
    snapshot = cost_tracker.snapshot()
    dashboard_url = snapshot.get("gateway", {}).get("dashboard_url", "https://app.portkey.ai")
    actions = [
        cl.Action(name="gateway_refresh", payload={}, label="Yenile"),
        cl.Action(name="gateway_reset", payload={}, label="Sifirla"),
    ]
    content = (
        "## Cost Dashboard\n\n"
        "Bu profil sohbet icin degil, `LangGraph` ve `Microsoft Agent Framework` maliyetlerini "
        "izlemek icin kullanilir.\n\n"
        f"Portkey dashboard: {dashboard_url}"
    )

    dashboard_message = cl.user_session.get("gateway_dashboard_message")
    if dashboard_message is None:
        dashboard_message = cl.Message(
            content=content,
            actions=actions,
            elements=build_gateway_elements(snapshot),
        )
        await dashboard_message.send()
        cl.user_session.set("gateway_dashboard_message", dashboard_message)
        return

    dashboard_message.content = content
    dashboard_message.actions = actions
    dashboard_message.elements = build_gateway_elements(snapshot)
    await dashboard_message.update()


async def stream_final_answer(final_content: str) -> None:
    msg = cl.Message(content="")
    await msg.send()
    for char in final_content:
        await msg.stream_token(char)
        await asyncio.sleep(0.008)
    await msg.update()


@cl.set_chat_profiles
async def chat_profiles(_current_user, _language):
    return [
        cl.ChatProfile(
            name=LANGGRAPH_PROFILE,
            markdown_description="Supervisor + LangGraph uzman ajanlari",
            display_name="LangGraph Chat",
            default=True,
        ),
        cl.ChatProfile(
            name=MAF_PROFILE,
            markdown_description="Microsoft Agent Framework uzman ajanlari",
            display_name="Microsoft Agent Framework",
        ),
        cl.ChatProfile(
            name=GATEWAY_PROFILE,
            markdown_description="Portkey gateway ve maliyet paneli",
            display_name="Gateway / Portkey",
        ),
    ]


@cl.on_chat_start
async def on_chat_start():
    profile = cl.user_session.get("chat_profile") or LANGGRAPH_PROFILE
    if profile == MAF_PROFILE:
        engine = "maf"
    elif profile == GATEWAY_PROFILE:
        engine = "gateway"
    else:
        engine = "langgraph"
    cl.user_session.set("engine", engine)
    cl.user_session.set("history", [])
    cl.user_session.set("conversation_history", [])

    if engine == "gateway":
        await send_gateway_dashboard()
        return

    intro = (
        "Merhaba! Ben **IFS Corporate AI** asistaniyim.\n\n"
        "Yardim alanlarim:\n"
        "- **IK**: Izin, maas, personel bilgileri\n"
        "- **IT**: Teknik destek, donanim talepleri, parca sorgusu\n"
        "- **Finans**: Avans, harcama raporu\n"
        "- **Matematik**: Hesaplamalar, birim donusumu\n"
        "- **Genel**: Yemek menusu, servis saatleri\n\n"
    )
    if engine == "maf":
        intro += "Aktif motor: **Microsoft Agent Framework**"
    else:
        intro += "Aktif motor: **LangGraph Supervisor**"

    await cl.Message(content=intro).send()


@cl.on_message
async def on_message(message: cl.Message):
    engine = cl.user_session.get("engine", "langgraph")
    if engine == "gateway":
        await _handle_gateway_message(message)
        return
    if engine == "maf":
        await _handle_maf_message(message)
        return
    await _handle_langgraph_message(message)


@cl.action_callback("gateway_refresh")
async def gateway_refresh(_action: cl.Action):
    await send_gateway_dashboard()


@cl.action_callback("gateway_reset")
async def gateway_reset(_action: cl.Action):
    cost_tracker.reset()
    await cl.Message(content="Gateway panel verisi sifirlandi.").send()
    await send_gateway_dashboard()


async def _handle_langgraph_message(message: cl.Message):
    history = cl.user_session.get("history", [])
    history.append(HumanMessage(content=message.content))

    inputs = {"messages": history, "user_context": {}}
    config = {"configurable": {"thread_id": "chainlit_user"}, "recursion_limit": 25}

    checklist_msg = None
    completed_steps = set()
    plan_steps = []

    step = cl.Step(name="Supervisor", type="tool")
    step.input = "Mesajiniz analiz ediliyor..."
    await step.send()

    final_content = ""
    current_plan_idx = 0

    try:
        async for event in graph.astream_events(inputs, config=config, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_chain_end" and name == "supervisor":
                output = event.get("data", {}).get("output", {})
                next_val = output.get("next", "FINISH")
                if not plan_steps:
                    plan_steps = output.get("plan_steps", []) or []
                    if plan_steps:
                        checklist_msg = cl.Message(content=build_checklist(plan_steps, completed_steps))
                        await checklist_msg.send()
                agent_key = next_val.lower().replace("_agent", "")

                if agent_key in ("hr", "it", "finance", "math", "general"):
                    label = AGENT_LABELS.get(next_val, next_val)
                    step.name = label
                    step.input = f"{label} isleminiz hazirlaniyor..."
                    step.output = ""
                    await step.update()

                    if plan_steps:
                        for index, plan_step in enumerate(plan_steps):
                            plan_agent = plan_step.agent if hasattr(plan_step, "agent") else plan_step.get("agent", "")
                            if plan_agent == next_val and index not in completed_steps:
                                current_plan_idx = index
                                break

            elif kind == "on_tool_start":
                step.output = f"`{name}` calistiriliyor..."
                await step.update()

            elif kind == "on_tool_end":
                tool_output = event.get("data", {}).get("output", "")
                if hasattr(tool_output, "content"):
                    step.output = to_str(tool_output.content)[:300]
                else:
                    step.output = to_str(str(tool_output))[:300]
                await step.update()

            elif kind == "on_chain_end" and name in ("hr", "it", "finance", "math", "general"):
                output = event.get("data", {}).get("output", {})
                msgs = output.get("messages", [])
                if msgs:
                    last = msgs[-1]
                    if hasattr(last, "content"):
                        text = to_str(last.content)
                        if text.strip():
                            final_content = text

                step.output = "Tamamlandi, siradaki kontrol ediliyor..."
                await step.update()

                if plan_steps and checklist_msg:
                    completed_steps.add(current_plan_idx)
                    checklist_msg.content = build_checklist(plan_steps, completed_steps)
                    await checklist_msg.update()

            elif kind == "on_chain_end" and name == "chat":
                output = event.get("data", {}).get("output", {})
                msgs = output.get("messages", [])
                if msgs:
                    last = msgs[-1]
                    if hasattr(last, "content"):
                        text = to_str(last.content)
                        if text.strip():
                            final_content = text

    except Exception as exc:
        step.output = f"Hata: {exc}"
        await step.update()
        await cl.Message(content=f"Bir hata olustu: {exc}").send()
        return

    try:
        await step.remove()
    except Exception:
        pass

    if plan_steps and checklist_msg:
        for index in range(len(plan_steps)):
            completed_steps.add(index)
        checklist_msg.content = build_checklist(plan_steps, completed_steps)
        await checklist_msg.update()

    if final_content:
        history.append(AIMessage(content=final_content))
        cl.user_session.set("history", history)
        await stream_final_answer(final_content)
    else:
        await cl.Message(content="Yanit alinamadi.").send()


async def _handle_maf_message(message: cl.Message):
    conversation_history = cl.user_session.get("conversation_history", [])
    conversation_history.append({"role": "user", "content": message.content})

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
                step.output = ""
                await step.update()

        elif event_type == "step_start":
            plan_step = event["step"]
            label = AGENT_LABELS.get(plan_step.agent, plan_step.agent)
            step.name = label
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
        result = await maf_orchestrator.run(conversation_history, progress_callback=on_progress)
        final_content = result.final_text
    except Exception as exc:
        step.output = f"Hata: {exc}"
        await step.update()
        await cl.Message(content=f"Bir hata olustu: {exc}").send()
        return

    try:
        await step.remove()
    except Exception:
        pass

    if checklist_msg and result.plan_steps:
        checklist_msg.content = build_checklist(result.plan_steps, set(range(len(result.plan_steps))))
        await checklist_msg.update()

    conversation_history.append({"role": "assistant", "content": final_content})
    cl.user_session.set("conversation_history", conversation_history)
    await stream_final_answer(final_content)


async def _handle_gateway_message(message: cl.Message):
    text = (message.content or "").strip().lower()

    if text in {"sifirla", "reset", "/reset"}:
        cost_tracker.reset()
        await cl.Message(content="Gateway panel verisi sifirlandi.").send()
        await send_gateway_dashboard()
        return

    if text not in {"yenile", "refresh", "/refresh", ""}:
        await cl.Message(
            content=(
                "Bu profil sohbet motoru degil. Burada iki frameworkun cost dashboard'u gosterilir.\n"
                "`yenile` yazarak paneli guncelleyebilir, `sifirla` yazarak maliyet kaydini sifirlayabilirsin."
            )
        ).send()

    await send_gateway_dashboard()
