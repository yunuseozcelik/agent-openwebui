"""LLM-based analysis for the wizard flow.

LLM sadece iki noktada calisir:
1. Kullanicinin ilk tarifini parse edip isim + amac cikarir
2. Toplanan cevaplardan tool/data_source/risk otomatik belirler
"""

from __future__ import annotations

import json
import re

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from agent_factory.config import OPENAI_API_KEY, OPENAI_COPILOT_MODEL
from utils.portkey import get_maf_client_options


PARSE_PROMPT = """Kullanicinin asagidaki agent tarifini analiz et.
Cevabi SADECE JSON olarak don, baska bir sey yazma.

JSON formati:
{{
  "name": "Kisa ve aciklayici agent ismi (Turkce, 2-4 kelime)",
  "purpose": "Agent ne yapacak, 1-2 cumle (Turkce)",
  "inferred_tools": ["file_reader", "code_interpreter", "file_search", "api_call", "db_query"],
  "inferred_data_sources": ["kaynak1", "kaynak2"],
  "complexity_hints": {{
    "needs_supervisor": false,
    "custom_state_required": false,
    "decision_points": 0
  }}
}}

Tool secim kurallari:
- Dosya isleme (Excel, CSV, PDF) bahsediliyorsa -> "file_reader"
- Hesaplama, analiz, istatistik, grafik -> "code_interpreter"
- Dokuman arama, bilgi tabani -> "file_search"
- Dis sistem, API, entegrasyon -> "api_call"
- Veritabani, SQL, sorgu -> "db_query"
- Birden fazla secebilirsin

Kullanici tarifi:
{description}
"""


SPEC_PROMPT = """Asagidaki bilgilere gore bir agent spec'i olustur.
Cevabi SADECE JSON olarak don.

Kullanici tarifi: {description}
Agent ismi: {name}
Agent amaci: {purpose}
Hedef kitle: {audience}
Hassas veri (PII): {pii}
Insan onayi: {approval}
Cikarilmis tool'lar: {tools}
Cikarilmis veri kaynaklari: {data_sources}

JSON formati:
{{
  "name": "agent ismi",
  "purpose": "agent amaci",
  "user_audience": "hedef kitle",
  "data_sources": ["kaynak1"],
  "tools": [
    {{"name": "tool adi", "type": "tool_tipi", "description": "ne yapar"}}
  ],
  "risk_level": "low|medium|high",
  "contains_pii": true|false,
  "approval_required": true|false,
  "needs_supervisor": true|false,
  "custom_state_required": true|false,
  "decision_points": 0
}}

Risk seviyesi belirleme:
- PII var + aksiyon var -> high
- PII var + sadece rapor -> medium
- PII yok + sadece rapor -> low
- PII yok + aksiyon var -> medium
"""


def _create_client() -> OpenAIChatClient:
    return OpenAIChatClient(
        **get_maf_client_options(
            model_id=OPENAI_COPILOT_MODEL,
            primary_api_key=OPENAI_API_KEY,
            engine="agent_factory",
            component="analyzer",
        )
    )


def _extract_json(text: str) -> dict:
    """Metinden JSON cikar."""
    if not text:
        return {}

    # Fence icinde mi
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else text

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


async def parse_description(description: str) -> dict:
    """Kullanicinin ilk tarifini parse et -> isim, amac, tool, data_source cikar."""
    client = _create_client()
    agent = Agent(
        client=client,
        name="description_parser",
        instructions="Sen bir JSON uretici aracsin. Sadece JSON dondur, baska bir sey yazma.",
    )

    prompt = PARSE_PROMPT.replace("{description}", description)
    response = await agent.run(prompt)

    text = getattr(response, "text", "") or str(getattr(response, "value", ""))
    result = _extract_json(text)

    return {
        "name": result.get("name", ""),
        "purpose": result.get("purpose", ""),
        "inferred_tools": result.get("inferred_tools", []),
        "inferred_data_sources": result.get("inferred_data_sources", []),
        "complexity_hints": result.get("complexity_hints", {}),
    }


async def build_final_spec_data(
    description: str,
    name: str,
    purpose: str,
    audience: str,
    pii: str,
    approval: str,
    inferred_tools: list[str],
    inferred_data_sources: list[str],
) -> dict:
    """Toplanan cevaplardan final spec verisi olustur."""
    client = _create_client()
    agent = Agent(
        client=client,
        name="spec_builder",
        instructions="Sen bir JSON uretici aracsin. Sadece JSON dondur, baska bir sey yazma.",
    )

    prompt = SPEC_PROMPT.format(
        description=description,
        name=name,
        purpose=purpose,
        audience=audience,
        pii=pii,
        approval=approval,
        tools=json.dumps(inferred_tools),
        data_sources=json.dumps(inferred_data_sources),
    )

    response = await agent.run(prompt)
    text = getattr(response, "text", "") or str(getattr(response, "value", ""))
    return _extract_json(text)
