"""
Agent Factory — AI Agent Builder & Runner Platform

Chat Profiles:
  - "Agent Builder": Yeni agent olustur (wizard flow)
  - Her deploy edilmis agent: O agent ile sohbet et

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
from agent_factory.deployment.foundry_client import (
    deploy_prompt_agent, list_agents, get_agent_detail,
)
from agent_factory.registry import suggest_integrations_for_new_agent, build_interaction_graph
from agent_factory.runner import AgentRunner


# ═══════════════════════════════════════════════
#  Constants & Helpers
# ═══════════════════════════════════════════════

BUILDER_PROFILE = "Agent Builder"

_TOOL_LABELS = {
    "file_reader": ("Dosya Okuyucu", "Dosya"),
    "code_interpreter": ("Kod Yorumlayici", "Kod"),
    "file_search": ("Dokuman Arama", "RAG"),
    "api_call": ("API Entegrasyonu", "API"),
    "db_query": ("Veritabani Sorgusu", "DB"),
}

_TONE_LABELS = {
    "formal": "Resmi / Kurumsal",
    "friendly": "Samimi / Yardimci",
    "technical": "Teknik / Detayli",
    "concise": "Kisa / Ozet",
}

_FORMAT_LABELS = {
    "structured": "Tablo / Yapilandirilmis",
    "report": "Rapor / Detayli",
    "summary": "Kisa Ozet",
    "step_by_step": "Adim Adim",
    "adaptive": "Duruma Gore",
}

_SCOPE_LABELS = {
    "no_financial_advice": "Finansal tavsiye yok",
    "no_pii_sharing": "PII paylasim yok",
    "report_only": "Sadece raporlama",
    "strict_scope": "Siki kapsam siniri",
    "no_restriction": "Kisitlama yok",
}


def _tool_badge(tool_type: str) -> str:
    _, short = _TOOL_LABELS.get(tool_type, (tool_type, tool_type))
    return f"`{short}`"


# ═══════════════════════════════════════════════
#  Chat Profiles
# ═══════════════════════════════════════════════

@cl.set_chat_profiles
async def chat_profiles():
    profiles = [
        cl.ChatProfile(
            name=BUILDER_PROFILE,
            markdown_description="Yeni AI agent olustur",
            icon="/public/icons/builder.svg",
        ),
    ]

    agents = list_agents()
    for agent in agents:
        tools = [
            t.get("type", "?") if isinstance(t, dict) else str(t)
            for t in agent.tools
        ]
        tool_names = ", ".join(
            _TOOL_LABELS.get(t, (t, t))[1] for t in tools
        ) if tools else "—"

        status = " [mock]" if agent.metadata.get("mock") else ""

        profiles.append(
            cl.ChatProfile(
                name=agent.name,
                markdown_description=f"Araclar: {tool_names}{status}",
                icon="/public/icons/agent.svg",
            )
        )

    return profiles


# ═══════════════════════════════════════════════
#  Chat Start
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
    wizard = WizardState(current_step=-1)
    cl.user_session.set("wizard", wizard)
    cl.user_session.set("pending_spec_id", None)
    cl.user_session.set("pending_definition", None)

    agents = list_agents()
    agent_count = len(agents)

    # Agents table
    agents_table = ""
    if agents:
        rows = []
        for agent in agents:
            tools = [
                t.get("type", "?") if isinstance(t, dict) else str(t)
                for t in agent.tools
            ]
            badges = " ".join(_tool_badge(t) for t in tools) if tools else "`—`"

            if agent.metadata.get("mock"):
                status_txt, color = "mock", "#f59e0b"
            elif agent.metadata.get("status") == "draft":
                status_txt, color = "taslak", "#94a3b8"
            else:
                status_txt, color = "aktif", "#10b981"

            rows.append(
                f"| **{agent.name}** | {badges} | `{agent.model}` | "
                f"<span style='color:{color}'>{status_txt}</span> |"
            )

        agents_table = (
            "#### Mevcut Agent Ekosistemi\n\n"
            "| Agent | Araclar | Model | Durum |\n"
            "|:------|:--------|:------|:------|\n"
            + "\n".join(rows)
            + "\n\n> Bir agent ile konusmak icin sol ustteki profil menusunden secin.\n\n"
        )

    hero = "# Agent Factory\n"
    hero += "### Dogal dille AI agent olustur, dogrula ve deploy et\n\n"

    if agent_count > 0:
        hero += f"> **{agent_count}** agent ekosistemde\n\n---\n\n"

    if agents_table:
        hero += agents_table + "---\n\n"

    hero += (
        "#### Yeni Agent Olustur\n\n"
        "Olusturmak istediginiz agent'i **detayli** anlatin. Ne kadar cok detay "
        "verirseniz agent o kadar iyi olur.\n\n"
        "**Ornek detayli tarifler:**\n\n"
        "- *Musteri sikayetlerini Excel'den okuyup kategorilestirecek, "
        "yogunluk analizi yapacak ve haftalik trend raporu cikaracak bir agent istiyorum*\n"
        "- *HR ekibinin izin taleplerini veritabanindan cekip, "
        "onay durumlarini kontrol edecek ve personele bildirim gonderecek bir agent lazim*\n"
        "- *Satis ekibi icin CRM API'sindan musteri verilerini cekip, "
        "churn riski hesaplayacak ve musteriye ozel aksiyon onerecek bir agent olustur*\n"
    )

    await cl.Message(content=hero).send()


async def _start_agent_chat(agent_name: str):
    cl.user_session.set("mode", "agent_chat")

    agents = list_agents()
    agent_info = next((a for a in agents if a.name == agent_name), None)

    if not agent_info:
        await cl.Message(content=f"Agent bulunamadi: {agent_name}").send()
        return

    runner = AgentRunner(agent_info)
    cl.user_session.set("agent_runner", runner)
    cl.user_session.set("agent_info", agent_info)

    tools = [
        t.get("type", "?") if isinstance(t, dict) else str(t)
        for t in agent_info.tools
    ]
    tool_badges = " ".join(_tool_badge(t) for t in tools) if tools else "`—`"

    mock_note = ""
    if agent_info.metadata.get("mock"):
        mock_note = "\n\n> Mock agent — LLM ile simule ediliyor."

    # Instructions preview
    instr_preview = ""
    if agent_info.instructions:
        preview = agent_info.instructions[:300].replace("\n", " ")
        if len(agent_info.instructions) > 300:
            preview += "..."
        instr_preview = f"\n\n<details><summary>Agent Talimatlari</summary>\n\n{agent_info.instructions[:1000]}\n\n</details>"

    welcome = (
        f"# {agent_info.name}\n\n"
        f"| | |\n"
        f"|:--|:--|\n"
        f"| **Model** | `{agent_info.model}` |\n"
        f"| **Araclar** | {tool_badges} |\n"
        f"| **Kaynak** | {agent_info.source} |\n"
        f"\n---\n\n"
        f"Bu agent ile sohbet edebilirsin. Bir soru sor veya gorev ver."
        f"{mock_note}{instr_preview}"
    )

    await cl.Message(content=welcome).send()


# ═══════════════════════════════════════════════
#  Message Router
# ═══════════════════════════════════════════════

@cl.on_message
async def on_message(message: cl.Message):
    mode = cl.user_session.get("mode", "builder")

    if mode == "agent_chat":
        await _handle_agent_chat(message)
    else:
        await _handle_builder_message(message)


# ═══════════════════════════════════════════════
#  Agent Chat Mode
# ═══════════════════════════════════════════════

async def _handle_agent_chat(message: cl.Message):
    runner: AgentRunner = cl.user_session.get("agent_runner")
    if not runner:
        await cl.Message(content="Agent baglantisi koptu. Sayfayi yenileyin.").send()
        return

    thinking_msg = cl.Message(content="")
    await thinking_msg.send()

    try:
        response = await runner.send(message.content)
        thinking_msg.content = response
        await thinking_msg.update()
    except Exception as exc:
        thinking_msg.content = f"Hata: `{exc}`"
        await thinking_msg.update()


# ═══════════════════════════════════════════════
#  Builder Mode
# ═══════════════════════════════════════════════

async def _handle_builder_message(message: cl.Message):
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

    if wizard.is_collecting_description:
        await _handle_initial_description(message.content, wizard)
    elif wizard.is_in_steps:
        step = wizard.current_wizard_step
        if step and step.allow_custom:
            wizard.set_answer(step.id, message.content.strip())
            wizard.advance()
            cl.user_session.set("wizard", wizard)
            await _show_next_step(wizard)
        elif step:
            await cl.Message(
                content="Lutfen yukaridaki seceneklerden birini secin."
            ).send()
        else:
            await _handle_initial_description(message.content, wizard)
    elif wizard.is_ready_for_summary:
        pass
    else:
        wizard = WizardState(current_step=-1)
        cl.user_session.set("wizard", wizard)
        await _handle_initial_description(message.content, wizard)


# ── Step 1: Description ──

async def _handle_initial_description(text: str, wizard: WizardState):
    analyzing_msg = cl.Message(content="Talebiniz analiz ediliyor...")
    await analyzing_msg.send()

    async with cl.Step(name="LLM Analiz", type="llm") as step:
        step.input = text
        try:
            parsed = await parse_description(text)
            step.output = (
                f"Isim: {parsed.get('name', '—')}\n"
                f"Amac: {parsed.get('purpose', '—')}\n"
                f"Araclar: {', '.join(parsed.get('inferred_tools', []))}\n"
                f"Karmasiklik: {parsed.get('complexity_hints', {}).get('estimated_complexity', '—')}"
            )
        except Exception as exc:
            step.output = f"Hata: {exc}"
            analyzing_msg.content = f"Analiz sirasinda hata olustu: `{exc}`"
            await analyzing_msg.update()
            return

    wizard.description = text
    wizard.agent_name = parsed.get("name", "")
    wizard.agent_purpose = parsed.get("purpose", "")
    wizard.answers["inferred_tools"] = parsed.get("inferred_tools", [])
    wizard.answers["inferred_data_sources"] = parsed.get("inferred_data_sources", [])
    wizard.answers["suggested_capabilities"] = parsed.get("suggested_capabilities", [])
    wizard.answers["domain"] = parsed.get("domain", "genel")
    wizard.answers["complexity_hints"] = parsed.get("complexity_hints", {})

    tools_display = " ".join(
        _tool_badge(t) for t in parsed.get("inferred_tools", [])
    ) or "`otomatik`"

    # Capabilities
    caps = parsed.get("suggested_capabilities", [])
    caps_display = ""
    if caps:
        caps_display = "\n**Yetenekler:**\n" + "\n".join(f"- {c}" for c in caps[:6]) + "\n"

    complexity = parsed.get("complexity_hints", {}).get("estimated_complexity", "—")
    complexity_colors = {"simple": "#10b981", "moderate": "#f59e0b", "complex": "#ef4444"}
    complexity_labels = {"simple": "Basit", "moderate": "Orta", "complex": "Karmasik"}

    card = (
        f"### {wizard.agent_name}\n\n"
        f"> {wizard.agent_purpose}\n\n"
        f"| | |\n"
        f"|:--|:--|\n"
        f"| **Araclar** | {tools_display} |\n"
        f"| **Alan** | {parsed.get('domain', 'genel')} |\n"
        f"| **Karmasiklik** | <span style='color:{complexity_colors.get(complexity, '#94a3b8')}'>"
        f"{complexity_labels.get(complexity, complexity)}</span> |\n"
        f"{caps_display}\n"
        "---\n\n"
        "Simdi agent'i kisisellestirmek icin birkaC soru soracagim:"
    )
    analyzing_msg.content = card
    await analyzing_msg.update()

    wizard.current_step = 0
    cl.user_session.set("wizard", wizard)
    await _show_next_step(wizard)


# ── Step 2: Wizard Questions ──

async def _show_next_step(wizard: WizardState):
    if wizard.is_in_steps:
        await _render_step(wizard.current_wizard_step, wizard)
    elif wizard.is_ready_for_summary:
        await _show_summary(wizard)


async def _render_step(step_def, wizard: WizardState):
    total = len(WIZARD_STEPS)
    current = wizard.current_step + 1

    progress_bar = ""
    for i in range(1, total + 1):
        if i < current:
            progress_bar += "●"
        elif i == current:
            progress_bar += "◉"
        else:
            progress_bar += "○"

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

    content = (
        f"`{progress_bar}` **Adim {current}/{total}**\n\n"
        f"### {step_def.title}\n\n"
        f"{step_def.description}"
    )
    if step_def.allow_custom:
        content += "\n\n*Seceneklerden birini secin veya kendi cevabinizi yazin.*"

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

    await cl.Message(content=f"*{action.label or value}*", author="user").send()
    await _show_next_step(wizard)


# ── Step 3: Summary + Spec + Instructions ──

async def _show_summary(wizard: WizardState):
    audience = wizard.answers.get("audience", "belirtilmedi")
    tone = wizard.answers.get("tone", "friendly")
    output_format = wizard.answers.get("output_format", "adaptive")
    pii_raw = wizard.answers.get("pii", "false")
    approval_raw = wizard.answers.get("approval", "false")
    scope = wizard.answers.get("scope", "strict_scope")
    example = wizard.answers.get("example_scenario", "")

    pii_display = {"true": "Evet", "false": "Hayir", "maybe": "Belirsiz"}.get(pii_raw, pii_raw)
    approval_display = {"true": "Evet", "false": "Hayir", "conditional": "Kosullu"}.get(approval_raw, approval_raw)
    tools_badges = " ".join(
        _tool_badge(t) for t in wizard.answers.get("inferred_tools", [])
    ) or "`otomatik`"

    risk_indicator = "Dusuk"
    if pii_raw in ("true", "maybe") and approval_raw in ("true", "conditional"):
        risk_indicator = "Yuksek"
    elif pii_raw in ("true", "maybe") or approval_raw in ("true", "conditional"):
        risk_indicator = "Orta"
    risk_colors = {"Dusuk": "#10b981", "Orta": "#f59e0b", "Yuksek": "#ef4444"}

    summary = (
        f"## {wizard.agent_name}\n\n"
        f"> {wizard.agent_purpose}\n\n"
        f"| Ozellik | Deger |\n"
        f"|:--------|:------|\n"
        f"| **Hedef Kitle** | {audience} |\n"
        f"| **Araclar** | {tools_badges} |\n"
        f"| **Iletisim Tonu** | {_TONE_LABELS.get(tone, tone)} |\n"
        f"| **Cikti Formati** | {_FORMAT_LABELS.get(output_format, output_format)} |\n"
        f"| **Kapsam Siniri** | {_SCOPE_LABELS.get(scope, scope)} |\n"
        f"| **Hassas Veri** | {pii_display} |\n"
        f"| **Insan Onayi** | {approval_display} |\n"
        f"| **Risk** | <span style='color:{risk_colors[risk_indicator]}'>{risk_indicator}</span> |\n"
    )

    if example and example != "skip":
        summary += f"\n**Ornek Senaryo:** {example}\n"

    # Capabilities
    caps = wizard.answers.get("suggested_capabilities", [])
    if caps:
        summary += "\n**Tespit Edilen Yetenekler:**\n" + "\n".join(f"- {c}" for c in caps) + "\n"

    # Integration suggestions
    integrations = suggest_integrations_for_new_agent(
        purpose=wizard.agent_purpose or wizard.description,
        tool_types=wizard.answers.get("inferred_tools", []),
    )
    if integrations:
        summary += f"\n\n{integrations}"

    await cl.Message(content=summary).send()

    # ── Build Spec ──
    spec_msg = cl.Message(content="Agent spec hazirlaniyor...")
    await spec_msg.send()

    async with cl.Step(name="Spec Builder", type="llm") as step:
        step.input = f"Agent: {wizard.agent_name}"
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
                tone=tone,
                output_format=output_format,
                scope=scope,
                example_scenario=example if example != "skip" else "",
            )
            step.output = "Spec olusturuldu"
        except Exception as exc:
            step.output = f"Hata: {exc}"
            spec_msg.content = f"Spec olusturma hatasi: `{exc}`"
            await spec_msg.update()
            return

    spec = _build_spec_from_data(spec_data, wizard)
    save_spec(spec)

    spec_msg.content = f"Spec olusturuldu `{spec.id}`"
    await spec_msg.update()

    # ── Generate Rich Instructions via LLM ──
    instr_msg = cl.Message(content="Agent talimatlari olusturuluyor...")
    await instr_msg.send()

    custom_instructions = None
    async with cl.Step(name="Instruction Generator", type="llm") as step:
        step.input = f"Agent: {wizard.agent_name} | Tone: {tone} | Format: {output_format}"
        try:
            custom_instructions = await generate_rich_instructions(
                name=wizard.agent_name,
                purpose=wizard.agent_purpose,
                audience=audience,
                tone=tone,
                output_format=output_format,
                scope=scope,
                example_scenario=example if example != "skip" else "",
                tools=wizard.answers.get("inferred_tools", []),
                data_sources=wizard.answers.get("inferred_data_sources", []),
                pii=pii_raw,
                approval=approval_raw,
            )
            step.output = f"Instructions olusturuldu ({len(custom_instructions)} karakter)"
        except Exception as exc:
            step.output = f"Fallback kullanilacak: {exc}"
            custom_instructions = None

    if custom_instructions:
        instr_msg.content = (
            f"Agent talimatlari olusturuldu ({len(custom_instructions)} karakter)\n\n"
            f"<details><summary>Talimatlari Gor</summary>\n\n"
            f"```\n{custom_instructions[:2000]}\n```\n\n</details>"
        )
    else:
        instr_msg.content = "Template-based talimatlar kullanilacak."
    await instr_msg.update()

    wizard.completed = True
    cl.user_session.set("wizard", wizard)
    cl.user_session.set("custom_instructions", custom_instructions)

    # ── Run Pipeline ──
    await _run_pipeline(spec.id, wizard.answers, custom_instructions)


def _build_spec_from_data(spec_data: dict, wizard: WizardState) -> AgentSpec:
    tool_specs = []
    tools_raw = spec_data.get("tools", [])
    for t in tools_raw:
        if isinstance(t, dict) and t.get("name"):
            try:
                tool_specs.append(ToolSpec(
                    name=t["name"], type=t.get("type", "file_reader"),
                    description=t.get("description", ""),
                ))
            except Exception:
                pass

    if not tool_specs:
        for tool_type in wizard.answers.get("inferred_tools", []):
            tool_specs.append(ToolSpec(
                name=tool_type, type=tool_type,
                description=f"{tool_type} araci",
            ))

    try:
        risk = RiskLevel(spec_data.get("risk_level", "low"))
    except ValueError:
        risk = RiskLevel.LOW

    pii_answer = wizard.answers.get("pii", "false")
    approval_answer = wizard.answers.get("approval", "false")
    contains_pii = spec_data.get("contains_pii", pii_answer in ("true", "maybe"))
    approval_required = spec_data.get("approval_required", approval_answer in ("true", "conditional"))
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


# ═══════════════════════════════════════════════
#  Step 4: Pipeline + Approval
# ═══════════════════════════════════════════════

async def _run_pipeline(
    spec_id: str,
    wizard_answers: dict | None = None,
    custom_instructions: str | None = None,
):
    pipeline_msg = cl.Message(content="### Pipeline Calistiriliyor\n\n`...`")
    await pipeline_msg.send()

    try:
        result = run_pipeline(spec_id, wizard_answers, custom_instructions)
    except Exception as exc:
        pipeline_msg.content = f"### Pipeline Hatasi\n\n`{exc}`"
        await pipeline_msg.update()
        return

    lines = []
    for stage in result.stages:
        icon = "+" if stage.status == "pass" else "x"
        lines.append(f"[{icon}] {stage.name.upper()}")

        if stage.name == "policy" and stage.data.get("violations"):
            for v in stage.data["violations"]:
                sev = "!" if v["severity"] == "error" else "~"
                lines.append(f"    [{sev}] {v['description']}")

        if stage.name == "architect" and stage.data.get("selected_type"):
            lines.append(
                f"    Mimari: {stage.data['selected_type']} — "
                f"{stage.data.get('reason', '')}"
            )

    all_passed = all(s.status == "pass" for s in result.stages)
    status = "Tum kontroller gecti" if all_passed else "Bazi kontroller basarisiz"

    pipeline_msg.content = (
        f"### Pipeline Sonuclari\n\n"
        f"```\n" + "\n".join(lines) + "\n```\n\n"
        f"**Durum:** {status}"
    )
    await pipeline_msg.update()

    if result.review_summary:
        await cl.Message(content=result.review_summary).send()

    if result.ready_for_approval:
        cl.user_session.set("pending_spec_id", spec_id)
        cl.user_session.set("pending_definition", result.definition)

        # Interaction graph
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
                pass

        actions = [
            cl.Action(name="approve_deploy", payload={"spec_id": spec_id}, label="Deploy Et"),
            cl.Action(name="reject_deploy", payload={"spec_id": spec_id}, label="Iptal"),
        ]
        await cl.Message(
            content="### Onay Bekliyor\n\nAgent'i Azure AI Foundry'ye deploy etmek istiyor musun?",
            actions=actions,
        ).send()
    else:
        await cl.Message(content="### Pipeline Tamamlandi\n\nAgent deploy icin hazir degil.").send()
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


# ═══════════════════════════════════════════════
#  Step 5: Deploy
# ═══════════════════════════════════════════════

async def _handle_deploy(spec_id: str):
    definition = cl.user_session.get("pending_definition")
    if not definition:
        await cl.Message(content="Deploy bilgisi bulunamadi.").send()
        return

    deploy_msg = cl.Message(content="### Deployment\n\nAzure AI Foundry'ye deploy ediliyor...")
    await deploy_msg.send()

    try:
        result = deploy_prompt_agent(definition)
    except Exception as exc:
        deploy_msg.content = f"### Deploy Hatasi\n\n`{exc}`"
        await deploy_msg.update()
        return

    if result.success:
        mock_note = ""
        if result.mock:
            mock_note = (
                "\n\n> Mock deployment. Gercek deploy icin "
                "`.env` dosyasinda `FOUNDRY_PROJECT_ENDPOINT` tanimlayin."
            )

        deploy_msg.content = (
            f"### Deploy Basarili\n\n"
            f"| | |\n"
            f"|:--|:--|\n"
            f"| **Agent ID** | `{result.foundry_agent_id}` |\n"
            f"| **Spec ID** | `{spec_id}` |\n"
            f"| **Platform** | Azure AI Foundry |\n"
            f"| **Durum** | <span style='color:#10b981'>Aktif</span> |\n"
            f"\n> Agent ile konusmak icin sayfayi yenileyip sol ustteki profil menusunden secin."
            f"{mock_note}"
        )
        await deploy_msg.update()
    else:
        deploy_msg.content = f"### Deploy Basarisiz\n\n`{result.error}`"
        await deploy_msg.update()

    cl.user_session.set("pending_spec_id", None)
    cl.user_session.set("pending_definition", None)
    await _reset_wizard()


async def _reset_wizard(message: str = ""):
    wizard = WizardState(current_step=-1)
    cl.user_session.set("wizard", wizard)
    text = f"{message}\n\n" if message else ""
    text += "---\n\nYeni bir agent olusturmak icin yazabilirsin."
    await cl.Message(content=text).send()
