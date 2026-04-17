"""
Agent Factory — AI Agent Builder & Runner Platform

Run:
    chainlit run app_chainlit.py -w --port 8501
"""

from __future__ import annotations

import chainlit as cl

from agent_factory.builder.copilot.wizard import WIZARD_STEPS, WizardState
from agent_factory.builder.copilot.analyzer import (
    parse_description, build_final_spec_data, generate_rich_instructions,
)
from agent_factory.builder.spec.schema import AgentSpec, ToolSpec, RiskLevel
from agent_factory.builder.spec.store import save_spec
from agent_factory.builder.workflow import run_pipeline
from agent_factory.deployment.foundry_client import deploy_prompt_agent, list_agents
from agent_factory.registry import suggest_integrations_for_new_agent, build_interaction_graph
from agent_factory.runner import AgentRunner


# ═══════════════════════════════════════════════
#  Sabitler
# ═══════════════════════════════════════════════

BUILDER_PROFILE = "Agent Oluşturucu"

_TOOL_LABELS = {
    "file_reader": "Dosya",
    "code_interpreter": "Kod",
    "file_search": "Arama",
    "api_call": "API",
    "db_query": "Veritabanı",
}

_TONE_LABELS = {
    "formal": "Resmî / Kurumsal",
    "friendly": "Samimi / Yardımcı",
    "technical": "Teknik / Detaylı",
    "concise": "Kısa / Özet",
}

_FORMAT_LABELS = {
    "structured": "Tablo / Yapılandırılmış",
    "report": "Rapor / Detaylı",
    "summary": "Kısa Özet",
    "step_by_step": "Adım Adım",
    "adaptive": "Duruma Göre",
}

_SCOPE_LABELS = {
    "no_financial_advice": "Finansal tavsiye yok",
    "no_pii_sharing": "Kişisel veri paylaşımı yok",
    "report_only": "Sadece raporlama",
    "strict_scope": "Sıkı kapsam sınırı",
    "no_restriction": "Kısıtlama yok",
}


def _tool_badge(t: str) -> str:
    return f"`{_TOOL_LABELS.get(t, t)}`"


# ═══════════════════════════════════════════════
#  Profiller
# ═══════════════════════════════════════════════

@cl.set_chat_profiles
async def chat_profiles():
    profiles = [
        cl.ChatProfile(
            name=BUILDER_PROFILE,
            markdown_description="Yeni bir AI agent oluştur",
            icon="/public/icons/builder.svg",
        ),
    ]

    for agent in list_agents():
        tools = [t.get("type", "?") if isinstance(t, dict) else str(t) for t in agent.tools]
        tool_txt = ", ".join(_TOOL_LABELS.get(t, t) for t in tools) if tools else "—"
        tag = " · mock" if agent.metadata.get("mock") else ""

        profiles.append(
            cl.ChatProfile(
                name=agent.name,
                markdown_description=f"{tool_txt}{tag}",
                icon="/public/icons/agent.svg",
            )
        )

    return profiles


# ═══════════════════════════════════════════════
#  Başlangıç
# ═══════════════════════════════════════════════

@cl.on_chat_start
async def on_chat_start():
    profile = cl.user_session.get("chat_profile")
    if profile == BUILDER_PROFILE or profile is None:
        await _start_builder()
    else:
        await _start_agent_chat(profile)


async def _start_builder():
    cl.user_session.set("mode", "builder")
    cl.user_session.set("wizard", WizardState(current_step=-1))
    cl.user_session.set("pending_spec_id", None)
    cl.user_session.set("pending_definition", None)

    agents = list_agents()

    # Tablo
    table = ""
    if agents:
        rows = []
        for a in agents:
            tools = [t.get("type", "?") if isinstance(t, dict) else str(t) for t in a.tools]
            badges = " ".join(_tool_badge(t) for t in tools) if tools else "`—`"
            if a.metadata.get("mock"):
                s, c = "mock", "#f59e0b"
            elif a.metadata.get("status") == "draft":
                s, c = "taslak", "#94a3b8"
            else:
                s, c = "aktif", "#10b981"
            rows.append(f"| **{a.name}** | {badges} | `{a.model}` | <span style='color:{c}'>{s}</span> |")

        table = (
            "#### Mevcut Agent'lar\n\n"
            "| Agent | Araçlar | Model | Durum |\n"
            "|:------|:--------|:------|:------|\n"
            + "\n".join(rows)
            + "\n\n> Bir agent ile konuşmak için sol üstteki profil menüsünden seçin.\n\n---\n\n"
        )

    msg = (
        "# Agent Factory\n\n"
        f"> Ekosistemde **{len(agents)}** agent bulunuyor\n\n---\n\n"
        f"{table}"
        "#### Yeni Agent Oluştur\n\n"
        "Oluşturmak istediğiniz agent'ı **detaylı** anlatın.\n\n"
        "**Örnek:**\n"
        "- *Müşteri şikâyetlerini Excel'den okuyup kategorileştirecek ve haftalık trend raporu çıkaracak bir agent*\n"
        "- *Satış ekibi için CRM API'sinden veri çekip churn riski hesaplayacak bir agent*\n"
        "- *HR ekibinin izin taleplerini veritabanından kontrol edecek bir agent*\n"
    )
    await cl.Message(content=msg).send()


async def _start_agent_chat(agent_name: str):
    cl.user_session.set("mode", "agent_chat")

    agent_info = next((a for a in list_agents() if a.name == agent_name), None)
    if not agent_info:
        await cl.Message(content=f"Agent bulunamadı: {agent_name}").send()
        return

    runner = AgentRunner(agent_info)
    cl.user_session.set("agent_runner", runner)
    cl.user_session.set("agent_info", agent_info)

    tools = [t.get("type", "?") if isinstance(t, dict) else str(t) for t in agent_info.tools]
    badges = " ".join(_tool_badge(t) for t in tools) if tools else "`—`"
    mock = "\n\n> Mock agent — LLM ile simüle ediliyor." if agent_info.metadata.get("mock") else ""

    instr_block = ""
    if agent_info.instructions:
        instr_block = (
            f"\n\n<details><summary>Agent Talimatlarını Gör</summary>\n\n"
            f"```\n{agent_info.instructions[:2000]}\n```\n\n</details>"
        )

    await cl.Message(content=(
        f"# {agent_info.name}\n\n"
        f"| | |\n|:--|:--|\n"
        f"| **Model** | `{agent_info.model}` |\n"
        f"| **Araçlar** | {badges} |\n\n"
        f"---\n\nBu agent ile sohbet edebilirsiniz. Sorunuzu yazın."
        f"{mock}{instr_block}"
    )).send()


# ═══════════════════════════════════════════════
#  Mesaj Yönlendirici
# ═══════════════════════════════════════════════

@cl.on_message
async def on_message(msg: cl.Message):
    if cl.user_session.get("mode") == "agent_chat":
        await _handle_agent_chat(msg)
    else:
        await _handle_builder(msg)


# ═══════════════════════════════════════════════
#  Agent Sohbet
# ═══════════════════════════════════════════════

async def _handle_agent_chat(msg: cl.Message):
    runner: AgentRunner = cl.user_session.get("agent_runner")
    if not runner:
        await cl.Message(content="Bağlantı koptu. Sayfayı yenileyin.").send()
        return

    reply = cl.Message(content="")
    await reply.send()

    try:
        text = await runner.send(msg.content)
        reply.content = text
        await reply.update()
    except Exception as exc:
        reply.content = f"Hata: `{exc}`"
        await reply.update()


# ═══════════════════════════════════════════════
#  Builder Akışı
# ═══════════════════════════════════════════════

async def _handle_builder(msg: cl.Message):
    # Onay/red kontrolü
    pending = cl.user_session.get("pending_spec_id")
    if pending:
        t = (msg.content or "").strip().lower()
        if t in ("evet", "onay", "onayla", "deploy", "yes"):
            await _handle_deploy(pending)
            return
        if t in ("hayır", "red", "iptal", "no", "cancel"):
            cl.user_session.set("pending_spec_id", None)
            cl.user_session.set("pending_definition", None)
            await _reset("Deploy iptal edildi.")
            return

    wizard: WizardState = cl.user_session.get("wizard")
    if not wizard:
        wizard = WizardState(current_step=-1)
        cl.user_session.set("wizard", wizard)

    if wizard.is_collecting_description:
        await _step_description(msg.content, wizard)
    elif wizard.is_in_steps:
        step = wizard.current_wizard_step
        if step and step.allow_custom:
            wizard.set_answer(step.id, msg.content.strip())
            wizard.advance()
            cl.user_session.set("wizard", wizard)
            await _next_step(wizard)
        elif step:
            await cl.Message(content="Lütfen yukarıdaki seçeneklerden birini seçin.").send()
        else:
            await _step_description(msg.content, wizard)
    elif not wizard.is_ready_for_summary:
        wizard = WizardState(current_step=-1)
        cl.user_session.set("wizard", wizard)
        await _step_description(msg.content, wizard)


# ── Adım 1: Analiz ──

async def _step_description(text: str, wizard: WizardState):
    status = cl.Message(content="🔍 Talebiniz analiz ediliyor...")
    await status.send()

    async with cl.Step(name="Analiz", type="llm") as step:
        step.input = text
        try:
            parsed = await parse_description(text)
            step.output = f"✓ {parsed.get('name', '—')}"
        except Exception as exc:
            step.output = f"Hata: {exc}"
            status.content = f"Analiz hatası: `{exc}`"
            await status.update()
            return

    wizard.description = text
    wizard.agent_name = parsed.get("name", "")
    wizard.agent_purpose = parsed.get("purpose", "")
    wizard.answers["inferred_tools"] = parsed.get("inferred_tools", [])
    wizard.answers["inferred_data_sources"] = parsed.get("inferred_data_sources", [])
    wizard.answers["suggested_capabilities"] = parsed.get("suggested_capabilities", [])
    wizard.answers["domain"] = parsed.get("domain", "genel")
    wizard.answers["complexity_hints"] = parsed.get("complexity_hints", {})

    tools_display = " ".join(_tool_badge(t) for t in parsed.get("inferred_tools", [])) or "`otomatik`"

    caps = parsed.get("suggested_capabilities", [])
    caps_txt = "\n".join(f"- {c}" for c in caps[:5]) if caps else ""

    cx = parsed.get("complexity_hints", {}).get("estimated_complexity", "—")
    cx_map = {"simple": ("Basit", "#10b981"), "moderate": ("Orta", "#f59e0b"), "complex": ("Karmaşık", "#ef4444")}
    cx_label, cx_color = cx_map.get(cx, (cx, "#94a3b8"))

    card = (
        f"### {wizard.agent_name}\n\n"
        f"> {wizard.agent_purpose}\n\n"
        f"| | |\n|:--|:--|\n"
        f"| **Araçlar** | {tools_display} |\n"
        f"| **Alan** | {parsed.get('domain', 'genel')} |\n"
        f"| **Karmaşıklık** | <span style='color:{cx_color}'>{cx_label}</span> |\n"
    )
    if caps_txt:
        card += f"\n**Yetenekler:**\n{caps_txt}\n"

    card += "\n---\n\nŞimdi agent'ı kişiselleştirmek için birkaç soru soracağım:"

    status.content = card
    await status.update()

    wizard.current_step = 0
    cl.user_session.set("wizard", wizard)
    await _next_step(wizard)


# ── Adım 2: Wizard Soruları ──

async def _next_step(wizard: WizardState):
    if wizard.is_in_steps:
        await _render_step(wizard)
    elif wizard.is_ready_for_summary:
        await _step_summary(wizard)


async def _render_step(wizard: WizardState):
    step_def = wizard.current_wizard_step
    total = len(WIZARD_STEPS)
    cur = wizard.current_step + 1

    # Progress
    bar = ""
    for i in range(1, total + 1):
        bar += "● " if i < cur else ("◉ " if i == cur else "○ ")

    actions = [
        cl.Action(
            name="wz",
            payload={"sid": step_def.id, "val": ch.value},
            label=ch.label,
            tooltip=ch.description,
        )
        for ch in step_def.choices
    ]

    content = f"{bar.strip()}  `{cur}/{total}`\n\n### {step_def.title}\n\n{step_def.description}"
    if step_def.allow_custom:
        content += "\n\n*Seçeneklerden birini seçin veya kendi cevabınızı yazın.*"

    await cl.Message(content=content, actions=actions).send()


@cl.action_callback("wz")
async def on_wz(action: cl.Action):
    wizard: WizardState = cl.user_session.get("wizard")
    if not wizard:
        return

    wizard.set_answer(action.payload["sid"], action.payload["val"])
    wizard.advance()
    cl.user_session.set("wizard", wizard)

    await cl.Message(content=f"✓ *{action.label}*", author="user").send()
    await _next_step(wizard)


# ── Adım 3: Özet + Spec + Talimatlar ──

async def _step_summary(wizard: WizardState):
    a = wizard.answers
    audience = a.get("audience", "—")
    tone = a.get("tone", "friendly")
    fmt = a.get("output_format", "adaptive")
    pii = a.get("pii", "false")
    approval = a.get("approval", "false")
    scope = a.get("scope", "strict_scope")
    example = a.get("example_scenario", "")

    pii_d = {"true": "Evet", "false": "Hayır", "maybe": "Belirsiz"}.get(pii, pii)
    appr_d = {"true": "Evet", "false": "Hayır", "conditional": "Koşullu"}.get(approval, approval)
    tools_b = " ".join(_tool_badge(t) for t in a.get("inferred_tools", [])) or "`otomatik`"

    risk = "Düşük"
    if pii in ("true", "maybe") and approval in ("true", "conditional"):
        risk = "Yüksek"
    elif pii in ("true", "maybe") or approval in ("true", "conditional"):
        risk = "Orta"
    rc = {"Düşük": "#10b981", "Orta": "#f59e0b", "Yüksek": "#ef4444"}

    summary = (
        f"## {wizard.agent_name}\n\n"
        f"> {wizard.agent_purpose}\n\n"
        f"| Özellik | Değer |\n|:--------|:------|\n"
        f"| **Hedef Kitle** | {audience} |\n"
        f"| **Araçlar** | {tools_b} |\n"
        f"| **İletişim Tonu** | {_TONE_LABELS.get(tone, tone)} |\n"
        f"| **Çıktı Formatı** | {_FORMAT_LABELS.get(fmt, fmt)} |\n"
        f"| **Kapsam Sınırı** | {_SCOPE_LABELS.get(scope, scope)} |\n"
        f"| **Hassas Veri** | {pii_d} |\n"
        f"| **İnsan Onayı** | {appr_d} |\n"
        f"| **Risk** | <span style='color:{rc[risk]}'>{risk}</span> |\n"
    )

    if example and example != "skip":
        summary += f"\n**Örnek Senaryo:** {example}\n"

    caps = a.get("suggested_capabilities", [])
    if caps:
        summary += "\n**Yetenekler:**\n" + "\n".join(f"- {c}" for c in caps) + "\n"

    integrations = suggest_integrations_for_new_agent(
        purpose=wizard.agent_purpose or wizard.description,
        tool_types=a.get("inferred_tools", []),
    )
    if integrations:
        summary += f"\n\n{integrations}"

    await cl.Message(content=summary).send()

    # ── Spec oluştur ──
    status = cl.Message(content="⚙️ Agent spec oluşturuluyor...")
    await status.send()

    async with cl.Step(name="Spec", type="llm") as step:
        step.input = wizard.agent_name
        try:
            spec_data = await build_final_spec_data(
                description=wizard.description,
                name=wizard.agent_name,
                purpose=wizard.agent_purpose,
                audience=audience, pii=pii, approval=approval,
                inferred_tools=a.get("inferred_tools", []),
                inferred_data_sources=a.get("inferred_data_sources", []),
                tone=tone, output_format=fmt, scope=scope,
                example_scenario=example if example != "skip" else "",
            )
            step.output = "✓"
        except Exception as exc:
            status.content = f"Spec hatası: `{exc}`"
            await status.update()
            return

    spec = _build_spec(spec_data, wizard)
    save_spec(spec)
    status.content = f"✓ Spec oluşturuldu: `{spec.id}`"
    await status.update()

    # ── Talimatlar oluştur ──
    instr_msg = cl.Message(content="✍️ Agent talimatları oluşturuluyor...")
    await instr_msg.send()

    custom_instr = None
    async with cl.Step(name="Talimatlar", type="llm") as step:
        step.input = f"{wizard.agent_name} | {tone} | {fmt}"
        try:
            custom_instr = await generate_rich_instructions(
                name=wizard.agent_name, purpose=wizard.agent_purpose,
                audience=audience, tone=tone, output_format=fmt,
                scope=scope,
                example_scenario=example if example != "skip" else "",
                tools=a.get("inferred_tools", []),
                data_sources=a.get("inferred_data_sources", []),
                pii=pii, approval=approval,
            )
            step.output = f"✓ {len(custom_instr)} karakter"
        except Exception:
            custom_instr = None

    if custom_instr:
        instr_msg.content = (
            f"✓ Talimatlar oluşturuldu ({len(custom_instr)} karakter)\n\n"
            f"<details><summary>Talimatları Gör</summary>\n\n"
            f"```\n{custom_instr[:2000]}\n```\n\n</details>"
        )
    else:
        instr_msg.content = "Şablon tabanlı talimatlar kullanılacak."
    await instr_msg.update()

    wizard.completed = True
    cl.user_session.set("wizard", wizard)

    # ── Pipeline ──
    await _step_pipeline(spec.id, wizard.answers, custom_instr)


def _build_spec(data: dict, wiz: WizardState) -> AgentSpec:
    tool_specs = []
    for t in data.get("tools", []):
        if isinstance(t, dict) and t.get("name"):
            try:
                tool_specs.append(ToolSpec(
                    name=t["name"], type=t.get("type", "file_reader"),
                    description=t.get("description", ""),
                ))
            except Exception:
                pass
    if not tool_specs:
        for tt in wiz.answers.get("inferred_tools", []):
            tool_specs.append(ToolSpec(name=tt, type=tt, description=f"{tt} aracı"))

    try:
        risk = RiskLevel(data.get("risk_level", "low"))
    except ValueError:
        risk = RiskLevel.LOW

    pii_a = wiz.answers.get("pii", "false")
    appr_a = wiz.answers.get("approval", "false")
    hints = wiz.answers.get("complexity_hints", {})

    return AgentSpec(
        name=data.get("name", wiz.agent_name) or wiz.agent_name or "İsimsiz Agent",
        purpose=data.get("purpose", wiz.agent_purpose) or wiz.agent_purpose,
        user_audience=data.get("user_audience", wiz.answers.get("audience", "")),
        data_sources=data.get("data_sources", wiz.answers.get("inferred_data_sources", [])),
        tools=tool_specs, risk_level=risk,
        contains_pii=data.get("contains_pii", pii_a in ("true", "maybe")),
        approval_required=data.get("approval_required", appr_a in ("true", "conditional")),
        needs_supervisor=hints.get("needs_supervisor", False),
        custom_state_required=hints.get("custom_state_required", False),
        decision_points=hints.get("decision_points", 0),
    )


# ═══════════════════════════════════════════════
#  Adım 4: Pipeline + Onay
# ═══════════════════════════════════════════════

async def _step_pipeline(spec_id, wiz_answers=None, custom_instr=None):
    pm = cl.Message(content="### Pipeline Çalıştırılıyor\n\n`...`")
    await pm.send()

    try:
        result = run_pipeline(spec_id, wiz_answers, custom_instr)
    except Exception as exc:
        pm.content = f"### Pipeline Hatası\n\n`{exc}`"
        await pm.update()
        return

    lines = []
    for s in result.stages:
        icon = "✓" if s.status == "pass" else "✗"
        lines.append(f"  {icon}  {s.name.upper()}")
        if s.name == "policy" and s.data.get("violations"):
            for v in s.data["violations"]:
                lines.append(f"      {'⚠' if v['severity'] == 'error' else '○'} {v['description']}")
        if s.name == "architect" and s.data.get("selected_type"):
            lines.append(f"      Mimari: {s.data['selected_type']} — {s.data.get('reason', '')}")

    ok = all(s.status == "pass" for s in result.stages)

    pm.content = (
        f"### Pipeline Sonuçları\n\n"
        f"```\n" + "\n".join(lines) + "\n```\n\n"
        f"**Durum:** {'✓ Tüm kontroller geçti' if ok else '✗ Bazı kontroller başarısız'}"
    )
    await pm.update()

    if result.review_summary:
        await cl.Message(content=result.review_summary).send()

    if not result.ready_for_approval:
        await cl.Message(content="Pipeline tamamlandı ama deploy'a hazır değil.").send()
        await _reset()
        return

    cl.user_session.set("pending_spec_id", spec_id)
    cl.user_session.set("pending_definition", result.definition)

    # Etkileşim grafiği
    wizard: WizardState = cl.user_session.get("wizard")
    if wizard:
        try:
            fig = build_interaction_graph(
                new_agent_name=wizard.agent_name or "Yeni Agent",
                new_agent_purpose=wizard.agent_purpose or "",
                new_agent_tools=wizard.answers.get("inferred_tools", []),
            )
            if fig:
                await cl.Message(
                    content="### Agent Etkileşim Haritası",
                    elements=[cl.Plotly(name="graph", figure=fig)],
                ).send()
        except Exception:
            pass

    await cl.Message(
        content="### Onay Bekliyor\n\nAgent'ı deploy etmek istiyor musunuz?",
        actions=[
            cl.Action(name="deploy_yes", payload={"sid": spec_id}, label="✓ Deploy Et"),
            cl.Action(name="deploy_no", payload={"sid": spec_id}, label="✗ İptal"),
        ],
    ).send()


@cl.action_callback("deploy_yes")
async def on_deploy_yes(action: cl.Action):
    await _handle_deploy(action.payload["sid"])


@cl.action_callback("deploy_no")
async def on_deploy_no(action: cl.Action):
    cl.user_session.set("pending_spec_id", None)
    cl.user_session.set("pending_definition", None)
    await _reset("Deploy iptal edildi.")


# ═══════════════════════════════════════════════
#  Adım 5: Deploy
# ═══════════════════════════════════════════════

async def _handle_deploy(spec_id: str):
    definition = cl.user_session.get("pending_definition")
    if not definition:
        await cl.Message(content="Deploy bilgisi bulunamadı.").send()
        return

    dm = cl.Message(content="🚀 Azure AI Foundry'ye deploy ediliyor...")
    await dm.send()

    try:
        result = deploy_prompt_agent(definition)
    except Exception as exc:
        dm.content = f"### Deploy Hatası\n\n`{exc}`"
        await dm.update()
        return

    if result.success:
        mock = ""
        if result.mock:
            mock = "\n\n> Mock deployment. Gerçek deploy için `.env`'de `FOUNDRY_PROJECT_ENDPOINT` tanımlayın."

        dm.content = (
            f"### ✓ Deploy Başarılı\n\n"
            f"| | |\n|:--|:--|\n"
            f"| **Agent ID** | `{result.foundry_agent_id}` |\n"
            f"| **Spec ID** | `{spec_id}` |\n"
            f"| **Platform** | Azure AI Foundry |\n"
            f"| **Durum** | <span style='color:#10b981'>Aktif</span> |\n"
            f"\n**Agent ile konuşmak için sayfayı yenileyip sol üstteki menüden seçin.**"
            f"{mock}"
        )
        await dm.update()
    else:
        dm.content = f"### Deploy Başarısız\n\n`{result.error}`"
        await dm.update()

    cl.user_session.set("pending_spec_id", None)
    cl.user_session.set("pending_definition", None)
    await _reset()


async def _reset(message: str = ""):
    cl.user_session.set("wizard", WizardState(current_step=-1))
    txt = f"{message}\n\n" if message else ""
    txt += "---\n\nYeni bir agent oluşturmak için yazabilirsiniz."
    await cl.Message(content=txt).send()
