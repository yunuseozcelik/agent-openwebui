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


LUNCH_MENU_DATA_SOURCE = "agent_factory/mock_data/lunch_menu_2026.json"


def _is_lunch_menu_request(text: str) -> bool:
    normalized = (text or "").lower()
    keywords = (
        "yemek",
        "menü",
        "menu",
        "öğle",
        "ogle",
        "lunch",
        "haftalık yemek",
        "haftalik yemek",
    )
    return any(keyword in normalized for keyword in keywords)


def _fallback_parse_description(description: str) -> dict:
    """Rule-based fallback for offline/dev mode when LLM analysis is unavailable."""
    if _is_lunch_menu_request(description):
        wants_excel = any(
            keyword in description.lower()
            for keyword in ("excel", "xlsx", "dosya", "rapor", "yazdır", "yazdir")
        )
        tools = ["file_reader", "code_interpreter"] if wants_excel else ["file_reader"]
        return {
            "name": "Yemek Menusu Asistani",
            "purpose": (
                "Gunun tarihine gore yemek menusunu bulur, haftalik yemek listesini hazirlar "
                "ve istenirse Excel formatinda raporlar. Mock yemek menu verisini tarih bazli kullanir."
            ),
            "inferred_tools": tools,
            "inferred_data_sources": [LUNCH_MENU_DATA_SOURCE],
            "suggested_capabilities": [
                "Bugunun yemek menusunu getirme",
                "Haftalik yemek menusunu listeleme",
                "Haftalik menuyu Excel raporuna donusturme",
                "Tarih bazli menu sorgulama",
            ],
            "domain": "genel_ofis",
            "complexity_hints": {
                "needs_supervisor": False,
                "custom_state_required": False,
                "decision_points": 1,
                "estimated_complexity": "moderate",
            },
        }

    return {
        "name": "Genel Is Asistani",
        "purpose": (
            "Kullanicinin tarif ettigi isi yerine getirmek icin gerekli bilgileri toplar, "
            "uygun araclari kullanir ve sonucu anlasilir bicimde sunar."
        ),
        "inferred_tools": ["file_reader"],
        "inferred_data_sources": [],
        "suggested_capabilities": ["Talep analizi", "Bilgi toplama", "Sonuc raporlama"],
        "domain": "genel",
        "complexity_hints": {
            "needs_supervisor": False,
            "custom_state_required": False,
            "decision_points": 0,
            "estimated_complexity": "simple",
        },
    }


def _fallback_spec_data(
    *,
    description: str,
    name: str,
    purpose: str,
    audience: str,
    inferred_tools: list[str],
    inferred_data_sources: list[str],
    pii: str,
    approval: str,
) -> dict:
    parsed = _fallback_parse_description(description)
    tools = inferred_tools or parsed["inferred_tools"]
    data_sources = inferred_data_sources or parsed["inferred_data_sources"]
    return {
        "name": name or parsed["name"],
        "purpose": purpose or parsed["purpose"],
        "user_audience": audience or "kurumsal kullanicilar",
        "data_sources": data_sources,
        "tools": [
            {
                "name": tool,
                "type": tool,
                "description": f"{tool} araci ile ilgili islemleri gerceklestirir.",
            }
            for tool in tools
        ],
        "risk_level": "low" if pii == "false" else "medium",
        "contains_pii": pii in ("true", "maybe"),
        "approval_required": approval in ("true", "conditional"),
        "needs_supervisor": False,
        "custom_state_required": False,
        "decision_points": parsed.get("complexity_hints", {}).get("decision_points", 0),
    }


# ═══════════════════════════════════════════════
#  Prompt: Description Parse
# ═══════════════════════════════════════════════

PARSE_PROMPT = """Kullanicinin asagidaki agent tarifini derinlemesine analiz et.
Cevabi SADECE JSON olarak don, baska bir sey yazma.

ONEMLI FELSEFE: Olusturulan tum agentlar SISTEMDEN HAZIR VERI CEKEN PRESENTER'lardir.
Agent kendi basina icerik URETMEZ, PLANLAMAZ, OZELLESTIRMEZ. Sadece sistemdeki hazir
veriyi (ornek: haftalik yemek menusu, izin bakiyesi, satis raporu) kullaniciya
iletir. "Olusturur", "planlar", "oneri sunar", "ozellestirilmis" gibi ifadeler
KULLANMA. Bunun yerine "sistemden getirir", "gosterir", "iletir", "raporlar" kullan.

JSON formati:
{{
  "name": "Kisa ve aciklayici agent ismi (Turkce, 2-4 kelime)",
  "purpose": "Agent sistemdeki hangi veriyi kullaniciya sunacak, 1-2 cumle (Turkce). 'Planlar/olusturur' DEGIL 'sistemdeki X verisini getirir/gosterir'",
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

INSTRUCTION_PROMPT = """Asagidaki agent spec bilgilerine gore system prompt olustur.

╔══════════════════════════════════════════════════════════════════════╗
║  KRITIK FELSEFE — HER SEYIN ONUNDE                                   ║
╠══════════════════════════════════════════════════════════════════════╣
║  Bu agent bir PRESENTER / DATA DELIVERY agent'idir.                  ║
║  - Sistem ona runtime'da hazir mock/gercek veri enjekte eder.        ║
║  - Agent'in TEK gorevi: bu veriyi kullaniciya iletmek.               ║
║  - Agent KENDISI icerik URETMEZ, PLANLAMAZ, OZELLESTIRMEZ,           ║
║    HESAPLAMAZ, ONERI SUNMAZ.                                         ║
║  - Kullanicidan "tercih, alerji, besin kisitlamasi, amacin ne" gibi  ║
║    seyler SORMAZ. Sistem verisi neyse onu gosterir.                  ║
║  - Veri gelmediyse "Bu konuda veri bulamadim" der, uydurmaz.         ║
╚══════════════════════════════════════════════════════════════════════╝

## Agent Bilgileri
- Isim: {name}
- Amac: {purpose}
- Hedef Kitle: {audience}
- Iletisim Tonu: {tone}
- Cikti Formati: {output_format}
- Tool'lar: {tools}
- Veri Kaynaklari: {data_sources}

## System prompt bolumleri (kisa tut, her biri 1-3 cumle)

1. KIMLIK: "Ben {name}. Gorevim sistemdeki [X] verisini kullaniciya sunmak."
2. GOREV: Sistemden ne veriyi nasil gosterecegi. "Planlar/ozellestirir"
   DEGIL "sistemden getirir ve sunar".
3. CALISMA PRENSIBI (zorunlu, aynen yaz):
   "Runtime'da sana 'MEVCUT VERI' basligi altinda sistem verisi verilir.
   SADECE bu veriyi kullan. Kendinden icerik uretme, planlama, ozellestirme.
   Kullanicidan tercih/alerji/amac sorma. Veri yoksa 'veri bulunamadi' de."
4. CIKTI FORMATI: Veriyi nasil bicimlendirecegi (tablo/liste).
5. KAPSAM DISI: Kapsam disi sorularda kisaca reddet.

KURALLAR:
- Prompt Turkce, 200-350 kelime arasinda, KISA ve AKSIYON ODAKLI.
- "Ozellestirilmis", "kisiye ozel", "tercihlere gore", "planlama",
  "oneri sunma", "olusturma" kelimelerini KULLANMA.
- "Sistemdeki veriyi", "hazir veriden", "iletir", "raporlar", "gosterir"
  kelimelerini kullan.
- Sadece prompt metnini don, baska aciklama ekleme.
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
    try:
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
    except Exception:
        result = _fallback_parse_description(description)

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
    try:
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
        result = _extract_json(text)
        if result:
            return result
    except Exception:
        pass

    return _fallback_spec_data(
        description=description,
        name=name,
        purpose=purpose,
        audience=audience,
        inferred_tools=inferred_tools,
        inferred_data_sources=inferred_data_sources,
        pii=pii,
        approval=approval,
    )


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
    try:
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
    except Exception:
        return ""

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

    try:
        response = await agent.run(prompt)
        text = getattr(response, "text", "") or str(getattr(response, "value", ""))
    except Exception:
        return ""

    # Eger fence icinde geldiyse cikar
    fence = re.search(r"```(?:markdown|text)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()

    return text.strip()
