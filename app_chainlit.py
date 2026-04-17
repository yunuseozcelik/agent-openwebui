"""
Agent Factory MVP - Chainlit UI (Wizard Flow)

Kullanici dogal dille agent tarif eder, adim adim form sorulariyla
detaylar toplanir, pipeline calistirilir, onay sonrasi deploy edilir.

Run with:
    chainlit run app_chainlit.py -w --port 8501
"""

from __future__ import annotations

import asyncio
import re

import chainlit as cl

from agent_factory.builder.copilot.wizard import (
    WIZARD_STEPS,
    WizardState,
)
from agent_factory.builder.copilot.analyzer import parse_description, build_final_spec_data
from agent_factory.builder.spec.schema import AgentSpec, ToolSpec, RiskLevel
from agent_factory.builder.spec.store import save_spec
from agent_factory.builder.workflow import run_pipeline
from agent_factory.deployment.foundry_client import deploy_prompt_agent, list_agents
from agent_factory.registry import suggest_integrations_for_new_agent, build_interaction_graph


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _build_agents_panel() -> str:
    agents = list_agents()
    if not agents:
        return ""
    lines = ["### Mevcut Agent'lar\n"]
    for agent in agents:
        badge = ""
        if agent.metadata.get("mock"):
            badge = " `mock`"
        elif agent.metadata.get("status") == "draft":
            badge = " `taslak`"
        else:
            badge = " `aktif`"
        lines.append(f"- **{agent.name}**{badge} — Model: `{agent.model}`")
    lines.append(f"\nToplam: **{len(agents)}** agent")
    return "\n".join(lines)


# ──────────────────────────────────────────────
#  Chat Start
# ──────────────────────────────────────────────

@cl.on_chat_start
async def on_chat_start():
    wizard = WizardState(current_step=-1)
    cl.user_session.set("wizard", wizard)
    cl.user_session.set("pending_spec_id", None)
    cl.user_session.set("pending_definition", None)

    agents_panel = _build_agents_panel()

    intro = "## Agent Factory Builder\n\n"
    if agents_panel:
        intro += agents_panel + "\n\n---\n\n"

    intro += (
        "Yeni bir agent olusturmak icin, ne yapmasini istediginizi yazin.\n\n"
        "Ornegin:\n"
        '- *"Musteri sikayetlerini analiz eden bir agent istiyorum"*\n'
        '- *"Excel dosyalarindaki hata kodlarini bulan bir agent lazim"*\n'
        '- *"Haftalik satis raporlarini ozetleyen bir agent olustur"*'
    )
    await cl.Message(content=intro).send()


# ──────────────────────────────────────────────
#  Message Handler
# ──────────────────────────────────────────────

@cl.on_message
async def on_message(message: cl.Message):
    # Onay/red kontrolu
    pending_spec = cl.user_session.get("pending_spec_id")
    if pending_spec:
        text = (message.content or "").strip().lower()
        if text in ("evet", "onay", "onayla", "deploy", "yes", "approve"):
            await _handle_deploy(pending_spec)
            return
        elif text in ("hayir", "red", "iptal", "no", "cancel"):
            cl.user_session.set("pending_spec_id", None)
            cl.user_session.set("pending_definition", None)
            await _reset_wizard("Deploy iptal edildi.")
            return

    wizard: WizardState = cl.user_session.get("wizard")
    if not wizard:
        wizard = WizardState(current_step=-1)
        cl.user_session.set("wizard", wizard)

    # Wizard adimlarinda serbest metin cevabi
    if wizard.is_collecting_description:
        await _handle_initial_description(message.content, wizard)
    elif wizard.is_in_steps:
        # Kullanici buton yerine serbest metin yazdi
        step = wizard.current_wizard_step
        if step and step.allow_custom:
            wizard.set_answer(step.id, message.content.strip())
            wizard.advance()
            cl.user_session.set("wizard", wizard)
            await _show_next_step(wizard)
        elif step:
            # Serbest metin kabul etmeyen adim - butonu kullanmasini soylet
            await cl.Message(content="Lutfen yukaridaki seceneklerden birini secin.").send()
        else:
            await _handle_initial_description(message.content, wizard)
    elif wizard.is_ready_for_summary:
        # Ozet asamasinda
        pass
    else:
        # Wizard tamamlanmis, yeni agent icin reset
        wizard = WizardState(current_step=-1)
        cl.user_session.set("wizard", wizard)
        await _handle_initial_description(message.content, wizard)


# ──────────────────────────────────────────────
#  Wizard: Initial Description
# ──────────────────────────────────────────────

async def _handle_initial_description(text: str, wizard: WizardState):
    step = cl.Step(name="Analiz", type="tool")
    step.input = "Talebiniz analiz ediliyor..."
    await step.send()

    try:
        parsed = await parse_description(text)
    except Exception as exc:
        await step.remove()
        await cl.Message(content=f"Analiz hatasi: {exc}").send()
        return

    try:
        await step.remove()
    except Exception:
        pass

    wizard.description = text
    wizard.agent_name = parsed.get("name", "")
    wizard.agent_purpose = parsed.get("purpose", "")
    wizard.answers["inferred_tools"] = parsed.get("inferred_tools", [])
    wizard.answers["inferred_data_sources"] = parsed.get("inferred_data_sources", [])
    wizard.answers["complexity_hints"] = parsed.get("complexity_hints", {})

    # Analiz sonucunu goster
    tools_display = ", ".join(parsed.get("inferred_tools", [])) or "belirsiz"
    summary = (
        f"### Anladim!\n\n"
        f"**Agent:** {wizard.agent_name}\n"
        f"**Amac:** {wizard.agent_purpose}\n"
        f"**Ongordugun araclar:** {tools_display}\n\n"
        "---\n\n"
        "Simdi birkaç detay soracagim:"
    )
    await cl.Message(content=summary).send()

    # Wizard adimlarini baslat
    wizard.current_step = 0
    cl.user_session.set("wizard", wizard)
    await _show_next_step(wizard)


# ──────────────────────────────────────────────
#  Wizard: Step Display
# ──────────────────────────────────────────────

async def _show_next_step(wizard: WizardState):
    if wizard.is_in_steps:
        step_def = wizard.current_wizard_step
        await _render_step(step_def)
    elif wizard.is_ready_for_summary:
        await _show_summary(wizard)


async def _render_step(step_def):
    """Bir wizard adimini butonlarla goster."""
    actions = []
    for choice in step_def.choices:
        actions.append(
            cl.Action(
                name="wizard_choice",
                payload={"step_id": step_def.id, "value": choice.value},
                label=choice.label,
                tooltip=choice.description,
            )
        )

    content = f"**{step_def.title}**\n\n{step_def.description}"
    if step_def.allow_custom:
        content += "\n\n_Seceneklerden birini secin veya asagiya kendi cevabinizi yazin._"

    await cl.Message(content=content, actions=actions).send()


@cl.action_callback("wizard_choice")
async def on_wizard_choice(action: cl.Action):
    wizard: WizardState = cl.user_session.get("wizard")
    if not wizard:
        return

    step_id = action.payload.get("step_id")
    value = action.payload.get("value")

    wizard.set_answer(step_id, value)
    wizard.advance()
    cl.user_session.set("wizard", wizard)

    # Secilen cevabi goster
    selected_label = action.label or value
    await cl.Message(content=f"_{selected_label}_", author="user").send()

    await _show_next_step(wizard)


# ──────────────────────────────────────────────
#  Wizard: Summary + Spec Creation
# ──────────────────────────────────────────────

async def _show_summary(wizard: WizardState):
    """Toplanan bilgileri ozetle ve spec olustur."""
    audience = wizard.answers.get("audience", "belirtilmedi")
    pii_raw = wizard.answers.get("pii", "false")
    approval_raw = wizard.answers.get("approval", "false")

    # Display labels
    pii_display = {"true": "Evet", "false": "Hayir", "maybe": "Belirsiz (sistem belirleyecek)"}.get(pii_raw, pii_raw)
    approval_display = {
        "true": "Evet",
        "false": "Hayir",
        "conditional": "Kosullu",
    }.get(approval_raw, approval_raw)

    tools_display = ", ".join(wizard.answers.get("inferred_tools", [])) or "otomatik"

    summary = (
        f"## Agent Ozeti\n\n"
        f"| Alan | Deger |\n"
        f"|---|---|\n"
        f"| **Isim** | {wizard.agent_name} |\n"
        f"| **Amac** | {wizard.agent_purpose} |\n"
        f"| **Hedef Kitle** | {audience} |\n"
        f"| **Hassas Veri** | {pii_display} |\n"
        f"| **Insan Onayi** | {approval_display} |\n"
        f"| **Araclar** | {tools_display} |\n"
    )

    # Mevcut agent'larla entegrasyon onerileri
    integrations = suggest_integrations_for_new_agent(
        purpose=wizard.agent_purpose or wizard.description,
        tool_types=wizard.answers.get("inferred_tools", []),
    )
    if integrations:
        summary += f"\n\n{integrations}"

    await cl.Message(content=summary).send()

    # LLM ile final spec'i olustur
    step = cl.Step(name="Spec Olusturuluyor", type="tool")
    step.input = "Agent spec'i hazirlaniyor..."
    await step.send()

    try:
        spec_data = await build_final_spec_data(
            description=wizard.description,
            name=wizard.agent_name,
            purpose=wizard.agent_purpose,
            audience=audience,
            pii=pii_raw,
            approval=approval_raw,
            inferred_tools=wizard.answers.get("inferred_tools", []),
            inferred_data_sources=wizard.answers.get("inferred_data_sources", []),
        )
    except Exception as exc:
        try:
            await step.remove()
        except Exception:
            pass
        await cl.Message(content=f"Spec olusturma hatasi: {exc}").send()
        return

    try:
        await step.remove()
    except Exception:
        pass

    # Spec'i olustur ve kaydet
    spec = _build_spec_from_data(spec_data, wizard)
    save_spec(spec)

    wizard.completed = True
    cl.user_session.set("wizard", wizard)

    await cl.Message(content=f"Spec olusturuldu: `{spec.id}`").send()

    # Pipeline calistir
    await _run_pipeline(spec.id)


def _build_spec_from_data(spec_data: dict, wizard: WizardState) -> AgentSpec:
    """LLM ciktisini veya wizard verilerini AgentSpec'e cevir."""
    # Tool'lari parse et
    tool_specs = []
    tools_raw = spec_data.get("tools", [])
    for t in tools_raw:
        if isinstance(t, dict) and t.get("name"):
            try:
                tool_specs.append(ToolSpec(
                    name=t["name"],
                    type=t.get("type", "file_reader"),
                    description=t.get("description", ""),
                ))
            except Exception:
                pass

    # Fallback: inferred_tools'tan olustur
    if not tool_specs:
        for tool_type in wizard.answers.get("inferred_tools", []):
            tool_specs.append(ToolSpec(
                name=tool_type,
                type=tool_type,
                description=f"{tool_type} araci",
            ))

    # Risk level
    try:
        risk = RiskLevel(spec_data.get("risk_level", "low"))
    except ValueError:
        risk = RiskLevel.LOW

    # PII ve approval
    pii_answer = wizard.answers.get("pii", "false")
    approval_answer = wizard.answers.get("approval", "false")

    contains_pii = spec_data.get("contains_pii", pii_answer in ("true", "maybe"))
    approval_required = spec_data.get("approval_required", approval_answer in ("true", "conditional"))

    # Complexity hints
    hints = wizard.answers.get("complexity_hints", {})

    return AgentSpec(
        name=spec_data.get("name", wizard.agent_name) or wizard.agent_name or "Unnamed Agent",
        purpose=spec_data.get("purpose", wizard.agent_purpose) or wizard.agent_purpose,
        user_audience=spec_data.get("user_audience", wizard.answers.get("audience", "")),
        data_sources=spec_data.get("data_sources", wizard.answers.get("inferred_data_sources", [])),
        tools=tool_specs,
        risk_level=risk,
        contains_pii=contains_pii,
        approval_required=approval_required,
        needs_supervisor=hints.get("needs_supervisor", False),
        custom_state_required=hints.get("custom_state_required", False),
        decision_points=hints.get("decision_points", 0),
    )


# ──────────────────────────────────────────────
#  Pipeline + Deploy
# ──────────────────────────────────────────────

async def _run_pipeline(spec_id: str):
    pipeline_msg = cl.Message(content="## Pipeline Calistiriliyor...\n")
    await pipeline_msg.send()

    try:
        result = run_pipeline(spec_id)
    except Exception as exc:
        await cl.Message(content=f"Pipeline hatasi: {exc}").send()
        return

    stage_lines = []
    for stage in result.stages:
        icon = "[+]" if stage.status == "pass" else "[x]"
        stage_lines.append(f"{icon} **{stage.name.upper()}**: {stage.status}")

        if stage.name == "policy" and stage.data.get("violations"):
            for v in stage.data["violations"]:
                sev = "[!]" if v["severity"] == "error" else "[~]"
                stage_lines.append(f"  {sev} {v['description']}")

        if stage.name == "architect" and stage.data.get("selected_type"):
            stage_lines.append(f"  Secilen tip: **{stage.data['selected_type']}**")
            stage_lines.append(f"  Gerekce: {stage.data['reason']}")

    pipeline_msg.content = "## Pipeline Sonuclari\n\n" + "\n".join(stage_lines)
    await pipeline_msg.update()

    if result.review_summary:
        await cl.Message(content=result.review_summary).send()

    if result.ready_for_approval:
        cl.user_session.set("pending_spec_id", spec_id)
        cl.user_session.set("pending_definition", result.definition)

        # Agent etkilesim grafigi
        wizard: WizardState = cl.user_session.get("wizard")
        if wizard:
            try:
                fig = build_interaction_graph(
                    new_agent_name=wizard.agent_name or "Yeni Agent",
                    new_agent_purpose=wizard.agent_purpose or wizard.description or "",
                    new_agent_tools=wizard.answers.get("inferred_tools", []),
                )
                if fig:
                    graph_el = cl.Plotly(name="agent_interactions", figure=fig)
                    await cl.Message(
                        content="### Agent Etkilesim Haritasi",
                        elements=[graph_el],
                    ).send()
            except Exception:
                pass  # Grafik olusturulamazsa sessizce gecilir

        actions = [
            cl.Action(name="approve_deploy", payload={"spec_id": spec_id}, label="Onayla ve Deploy Et"),
            cl.Action(name="reject_deploy", payload={"spec_id": spec_id}, label="Iptal Et"),
        ]
        await cl.Message(
            content="Bu agent'i deploy etmek istiyor musun?",
            actions=actions,
        ).send()
    else:
        await cl.Message(
            content="Pipeline tamamlandi ama deploy'a hazir degil."
        ).send()
        await _reset_wizard()


@cl.action_callback("approve_deploy")
async def on_approve(action: cl.Action):
    spec_id = action.payload.get("spec_id")
    if spec_id:
        await _handle_deploy(spec_id)


@cl.action_callback("reject_deploy")
async def on_reject(action: cl.Action):
    cl.user_session.set("pending_spec_id", None)
    cl.user_session.set("pending_definition", None)
    await _reset_wizard("Deploy iptal edildi.")


async def _handle_deploy(spec_id: str):
    definition = cl.user_session.get("pending_definition")
    if not definition:
        await cl.Message(content="Deploy bilgisi bulunamadi.").send()
        return

    deploy_msg = cl.Message(content="## Deployment Baslatiliyor...\n\nAzure AI Foundry'ye deploy ediliyor...")
    await deploy_msg.send()

    try:
        result = deploy_prompt_agent(definition)
    except Exception as exc:
        await cl.Message(content=f"Deploy hatasi: {exc}").send()
        return

    if result.success:
        mock_note = ""
        if result.mock:
            mock_note = "\n\n> **Not:** Mock deployment. Gercek deploy icin `.env`'de `FOUNDRY_PROJECT_ENDPOINT` tanimlayin."
        deploy_msg.content = (
            f"## Deploy Basarili!\n\n"
            f"- **Agent ID:** `{result.foundry_agent_id}`\n"
            f"- **Spec ID:** `{spec_id}`\n"
            f"- **Durum:** Aktif{mock_note}"
        )
        await deploy_msg.update()
    else:
        deploy_msg.content = f"## Deploy Basarisiz\n\nHata: {result.error}"
        await deploy_msg.update()

    cl.user_session.set("pending_spec_id", None)
    cl.user_session.set("pending_definition", None)
    await _reset_wizard()


async def _reset_wizard(message: str = ""):
    """Wizard'i sifirla, yeni agent icin hazir."""
    wizard = WizardState(current_step=-1)
    cl.user_session.set("wizard", wizard)
    text = message + ("\n\n" if message else "") + "Yeni bir agent olusturmak icin yazabilirsin."
    await cl.Message(content=text).send()
