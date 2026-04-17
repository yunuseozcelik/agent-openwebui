"""LLM-based analysis for the wizard flow.

LLM uc noktada calisir:
1. Kullanicinin ilk tarifini parse edip isim + amac cikarir
2. Toplanan cevaplardan final spec verisi olusturur
3. Spec'ten zengin agent instructions uretir
"""

from __future__ import annotations

import json
import re

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from agent_factory.config import OPENAI_API_KEY, OPENAI_COPILOT_MODEL
from utils.portkey import get_maf_client_options


# ═══════════════════════════════════════════════
#  Prompt: Description Parse
# ═══════════════════════════════════════════════

PARSE_PROMPT = """Kullanicinin asagidaki agent tarifini derinlemesine analiz et.
Cevabi SADECE JSON olarak don, baska bir sey yazma.

JSON formati:
{{
  "name": "Kisa ve aciklayici agent ismi (Turkce, 2-4 kelime)",
  "purpose": "Agent ne yapacak, 2-3 cumle ile detayli aciklama (Turkce)",
  "inferred_tools": ["tool_tipi1", "tool_tipi2"],
  "inferred_data_sources": ["kaynak1", "kaynak2"],
  "suggested_capabilities": ["yetenek1", "yetenek2", "yetenek3"],
  "domain": "ise ait alan (ornek: musteri_hizmetleri, finans, hr, operasyon, it, satis, genel)",
  "complexity_hints": {{
    "needs_supervisor": false,
    "custom_state_required": false,
    "decision_points": 0,
    "estimated_complexity": "simple|moderate|complex"
  }}
}}

Tool secim kurallari:
- Dosya isleme (Excel, CSV, PDF okuma/yazma) -> "file_reader"
- Hesaplama, analiz, istatistik, grafik, veri manipulasyonu -> "code_interpreter"
- Dokuman arama, bilgi tabani, RAG, metin icinde arama -> "file_search"
- Dis sistem, API, entegrasyon, webhook, HTTP -> "api_call"
- Veritabani, SQL, NoSQL, sorgu, tablo -> "db_query"
- Birden fazla sec, tipik senaryolarda en az 2-3 tool gerekir

suggested_capabilities: Agent'in yapabilecegi spesifik isler (3-6 madde).
Ornek: ["Excel dosyalarini analiz etme", "Hata kodlarini siniflandirma", "Trend raporu olusturma"]

Complexity belirleme:
- simple: Tek tool, tek veri kaynagi, soru-cevap
- moderate: 2-3 tool, birden fazla veri kaynagi, islem adimlari var
- complex: 4+ tool, karar agiaci, dis sistemlerle entegrasyon, coklu adim

Kullanici tarifi:
{description}
"""


# ═══════════════════════════════════════════════
#  Prompt: Final Spec Build
# ═══════════════════════════════════════════════

SPEC_PROMPT = """Asagidaki bilgilere gore detayli bir agent spec'i olustur.
Cevabi SADECE JSON olarak don.

## Toplanan Bilgiler
- Kullanici tarifi: {description}
- Agent ismi: {name}
- Agent amaci: {purpose}
- Hedef kitle: {audience}
- Iletisim tonu: {tone}
- Cikti formati: {output_format}
- Hassas veri (PII): {pii}
- Insan onayi: {approval}
- Kapsam siniri: {scope}
- Ornek senaryo: {example_scenario}
- Tespit edilen tool'lar: {tools}
- Tespit edilen veri kaynaklari: {data_sources}

## JSON formati:
{{
  "name": "agent ismi",
  "purpose": "detayli agent amaci (2-3 cumle)",
  "user_audience": "hedef kitle aciklamasi",
  "data_sources": ["kaynak1", "kaynak2"],
  "tools": [
    {{"name": "tool adi", "type": "tool_tipi", "description": "ne yapar, nasil kullanir"}}
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


# ═══════════════════════════════════════════════
#  Prompt: Instruction Generation
# ═══════════════════════════════════════════════

INSTRUCTION_PROMPT = """Asagidaki agent spec bilgilerine gore, agent'in calisma zamaninda
kullanacagi MUKEMMEL bir system prompt olustur.

## Agent Bilgileri
- Isim: {name}
- Amac: {purpose}
- Hedef Kitle: {audience}
- Iletisim Tonu: {tone}
- Cikti Formati: {output_format}
- Kapsam Siniri: {scope}
- Ornek Senaryo: {example_scenario}
- Tool'lar: {tools}
- Veri Kaynaklari: {data_sources}
- PII Var mi: {pii}
- Onay Gerekli mi: {approval}

## Talimatlar
Olusturacagin system prompt su bolumlerden olusmali:

1. KIMLIK: Agent'in kim oldugu, adi, rolu (1-2 cumle)
2. GOREV TANIMI: Ne yapacagi detayli aciklama (3-5 cumle)
3. HEDEF KITLE: Kiminle konustugu ve onlarin beklentileri
4. YETENEKLER: Yapabilecegi spesifik isler (madde madde)
5. KULLANILABILIR ARACLAR: Her tool'u nasil ve ne zaman kullanacagi
6. CIKTI FORMATI: Cevaplari nasil yapilandirmali
7. ILETISIM TARZI: Nasil konusmali, ton ve uslup
8. KURALLAR VE SINIRLAR: Kesinlikle yapmamasi gerekenler
9. HATA YONETIMI: Belirsizlik veya hata durumunda ne yapmali
10. ORNEK ETKILESIM: Tipik bir soru-cevap ornegi (varsa)

ONEMLI:
- Prompt Turkce olmali
- Cok spesifik ve aksiyon odakli olmali
- "Yapabilirsin" yerine "Yapacaksin" gibi kesin ifadeler kullan
- Agent'in kendi basina karar verebilecegi ve kullaniciya danismasi gereken durumlari net ayir
- Sadece prompt metnini don, baska aciklama ekleme
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
    """Kullanicinin ilk tarifini parse et."""
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
        "suggested_capabilities": result.get("suggested_capabilities", []),
        "domain": result.get("domain", "genel"),
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
    tone: str = "friendly",
    output_format: str = "adaptive",
    scope: str = "strict_scope",
    example_scenario: str = "",
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
        tone=tone,
        output_format=output_format,
        pii=pii,
        approval=approval,
        scope=scope,
        example_scenario=example_scenario or "belirtilmedi",
        tools=json.dumps(inferred_tools),
        data_sources=json.dumps(inferred_data_sources),
    )

    response = await agent.run(prompt)
    text = getattr(response, "text", "") or str(getattr(response, "value", ""))
    return _extract_json(text)


async def generate_rich_instructions(
    name: str,
    purpose: str,
    audience: str,
    tone: str,
    output_format: str,
    scope: str,
    example_scenario: str,
    tools: list[str],
    data_sources: list[str],
    pii: str,
    approval: str,
) -> str:
    """LLM ile zengin agent instructions olustur."""
    client = _create_client()
    agent = Agent(
        client=client,
        name="instruction_generator",
        instructions=(
            "Sen bir AI agent system prompt uzmanisun. "
            "Verilen bilgilerle mukemmel, detayli ve spesifik bir system prompt olustur. "
            "Sadece prompt metnini don, baska aciklama ekleme."
        ),
    )

    _tone_labels = {
        "formal": "Resmi ve kurumsal",
        "friendly": "Samimi ve yardimci",
        "technical": "Teknik ve detayli",
        "concise": "Kisa ve ozet odakli",
    }
    _format_labels = {
        "structured": "Tablo ve listeler",
        "report": "Detayli rapor",
        "summary": "Kisa ozet",
        "step_by_step": "Adim adim rehber",
        "adaptive": "Duruma gore uygun format",
    }
    _scope_labels = {
        "no_financial_advice": "Finansal tavsiye vermemeli",
        "no_pii_sharing": "Kisisel bilgi paylasmamalı",
        "report_only": "Sadece raporlamalı, aksiyon almamali",
        "strict_scope": "Kapsam disi sorulara cevap vermemeli",
        "no_restriction": "Genel kurallar yeterli",
    }

    prompt = INSTRUCTION_PROMPT.format(
        name=name,
        purpose=purpose,
        audience=audience,
        tone=_tone_labels.get(tone, tone),
        output_format=_format_labels.get(output_format, output_format),
        scope=_scope_labels.get(scope, scope),
        example_scenario=example_scenario or "belirtilmedi",
        tools=json.dumps(tools, ensure_ascii=False),
        data_sources=json.dumps(data_sources, ensure_ascii=False),
        pii=pii,
        approval=approval,
    )

    response = await agent.run(prompt)
    text = getattr(response, "text", "") or str(getattr(response, "value", ""))

    # Eger fence icinde geldiyse cikar
    fence = re.search(r"```(?:markdown|text)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()

    return text.strip()
