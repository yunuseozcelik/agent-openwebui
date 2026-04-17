"""Builder Copilot - MAF Agent ile kullanicidan bilgi toplayip AgentSpec olusturur.

Mevcut agent'lari ve tool katalogu bilerek, akilli oneriler yapar.
"""

from __future__ import annotations

import json
from typing import Annotated

from agent_framework import Agent, tool
from agent_framework.openai import OpenAIChatClient
from pydantic import Field

from ..spec.schema import AgentSpec, ToolSpec, RiskLevel
from ..spec.store import save_spec
from .prompts import COPILOT_SYSTEM_PROMPT
from agent_factory.config import OPENAI_API_KEY, OPENAI_COPILOT_MODEL
from agent_factory.registry import build_copilot_context, get_existing_agents_summary, get_tool_catalog_summary
from utils.portkey import get_maf_client_options


@tool(approval_mode="never_require")
def finalize_spec(
    name: Annotated[str, Field(description="Agent'in kisa ismi")],
    purpose: Annotated[str, Field(description="Agent ne yapacak, 1-2 cumle")],
    user_audience: Annotated[str, Field(description="Kim kullanacak")],
    data_sources: Annotated[str, Field(description="Veri kaynaklari, virgul ile ayrilmis")] = "",
    tools_json: Annotated[str, Field(description="Tool listesi JSON array: [{name, type, description}]")] = "[]",
    risk_level: Annotated[str, Field(description="low, medium veya high")] = "low",
    contains_pii: Annotated[bool, Field(description="PII iceriyor mu")] = False,
    approval_required: Annotated[bool, Field(description="Insan onayi gerekli mi")] = False,
    needs_supervisor: Annotated[bool, Field(description="Coklu agent koordinasyonu gerekli mi")] = False,
    custom_state_required: Annotated[bool, Field(description="Ozel state yonetimi gerekli mi")] = False,
    decision_points: Annotated[int, Field(description="Kosullu dal sayisi")] = 0,
) -> str:
    """Tum bilgiler toplandiginda agent spec'ini olustur ve kaydet."""
    # Tool listesini parse et
    tool_specs = []
    try:
        tools_raw = json.loads(tools_json) if tools_json and tools_json != "[]" else []
        for t in tools_raw:
            if isinstance(t, dict):
                tool_specs.append(ToolSpec(
                    name=t.get("name", ""),
                    type=t.get("type", "file_reader"),
                    description=t.get("description", ""),
                ))
    except (json.JSONDecodeError, ValueError):
        pass

    # Data sources parse
    sources = [s.strip() for s in data_sources.split(",") if s.strip()] if data_sources else []

    # Risk level parse
    try:
        rl = RiskLevel(risk_level.lower())
    except ValueError:
        rl = RiskLevel.LOW

    spec = AgentSpec(
        name=name,
        purpose=purpose,
        user_audience=user_audience,
        data_sources=sources,
        tools=tool_specs,
        risk_level=rl,
        contains_pii=contains_pii,
        approval_required=approval_required,
        needs_supervisor=needs_supervisor,
        custom_state_required=custom_state_required,
        decision_points=decision_points,
    )

    path = save_spec(spec)
    return (
        f"Agent spec basariyla olusturuldu!\n"
        f"Spec ID: {spec.id}\n"
        f"Isim: {spec.name}\n"
        f"Amac: {spec.purpose}\n"
        f"Hedef kitle: {spec.user_audience}\n"
        f"Veri kaynaklari: {', '.join(spec.data_sources) or 'yok'}\n"
        f"Tool sayisi: {len(spec.tools)}\n"
        f"Risk seviyesi: {spec.risk_level.value}\n"
        f"Dosya: {path}"
    )


@tool(approval_mode="never_require")
def list_existing_agents() -> str:
    """Sistemdeki mevcut agent'lari listele. Foundry ve local agent'lari gosterir."""
    return get_existing_agents_summary()


@tool(approval_mode="never_require")
def list_available_tools() -> str:
    """Yeni agent'a atanabilecek tool tiplerini listele."""
    return get_tool_catalog_summary()


def build_copilot() -> Agent:
    """Builder Copilot MAF agent'ini olustur. Mevcut agent/tool baglami enjekte edilir."""
    # Baglami topla
    context = build_copilot_context()

    # Prompt'a baglami enjekte et
    instructions = COPILOT_SYSTEM_PROMPT.replace("{context}", context)

    client = OpenAIChatClient(
        **get_maf_client_options(
            model_id=OPENAI_COPILOT_MODEL,
            primary_api_key=OPENAI_API_KEY,
            engine="agent_factory",
            component="copilot",
        )
    )
    return Agent(
        client=client,
        name="builder_copilot",
        instructions=instructions,
        tools=[finalize_spec, list_existing_agents, list_available_tools],
    )
