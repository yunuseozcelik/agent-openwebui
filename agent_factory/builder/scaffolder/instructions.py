"""Instruction & tool generation for agent scaffolding.

Iki mod var:
1. Template-based (fallback): LLM cagrilamadiysa basit template kullanir
2. LLM-based (primary): analyzer.generate_rich_instructions ile zengin prompt uretir
"""

from ..spec.schema import AgentSpec


_TONE_MAP = {
    "formal": "Resmi, profesyonel ve kurumsal bir dil kullan. Kisa ve net cevaplar ver.",
    "friendly": "Sicak, samimi ve anlasılır bir dil kullan. Kullaniciyi yonlendir ve rehberlik et.",
    "technical": "Teknik terminoloji kullan, detayli aciklamalar yap. Uzman seviyesinde iletisim kur.",
    "concise": "Minimum kelime, maksimum bilgi. Gereksiz aciklama yapma, dogrudan sonuca git.",
}

_FORMAT_MAP = {
    "structured": "Cevaplarini tablolar, listeler ve maddeler halinde yapilandir.",
    "report": "Detayli paragraflar halinde rapor formatinda cevap ver.",
    "summary": "Her cevabin 2-3 cumlelik kisa bir ozet olsun.",
    "step_by_step": "Cevaplarini numaralandirilmis adimlar halinde sun.",
    "adaptive": "Sorunun tipine gore en uygun formati sec.",
}

_SCOPE_MAP = {
    "no_financial_advice": "Kesinlikle finansal tavsiye, yatirim onerisi veya kredi degerlendirmesi YAPMA.",
    "no_pii_sharing": "Kisisel verileri (isim, TC, telefon vb.) disariya PAYLASMA veya loglama.",
    "report_only": "Sadece raporla ve bilgilendir. Hicbir sisteme yazma, degistirme veya silme islemi YAPMA.",
    "strict_scope": "Gorev taniminin disindaki konularda yardim ETME. Nazikce kapsam disi oldugunu belirt.",
    "no_restriction": "",
}


def generate_instructions(spec: AgentSpec, wizard_answers: dict | None = None) -> str:
    """Spec + wizard cevaplarından zengin template-based instructions olustur.

    Bu fallback generator — LLM-based instructions uretilemediyse kullanilir.
    """
    answers = wizard_answers or {}

    tools_desc = "\n".join(
        f"  - **{t.name}**: {t.description}" for t in spec.tools
    ) if spec.tools else "  - Ozel tool tanimlanmadi"

    data_sources = ", ".join(spec.data_sources) if spec.data_sources else "belirtilmedi"

    # Tone
    tone_key = answers.get("tone", "friendly")
    tone_instruction = _TONE_MAP.get(tone_key, _TONE_MAP["friendly"])

    # Output format
    format_key = answers.get("output_format", "adaptive")
    format_instruction = _FORMAT_MAP.get(format_key, _FORMAT_MAP["adaptive"])

    # Scope
    scope_key = answers.get("scope", "strict_scope")
    scope_instruction = _SCOPE_MAP.get(scope_key, _SCOPE_MAP["strict_scope"])

    # Example scenario
    example = answers.get("example_scenario", "")
    example_section = ""
    if example and example != "skip":
        example_section = f"""
## ORNEK SENARYO
Tipik bir kullanim senaryosu:
{example}
Bu senaryoyu referans alarak benzer talepleri isleyebilirsin.
"""

    # PII warning
    pii_section = ""
    if spec.contains_pii:
        pii_section = """
## HASSAS VERI UYARISI
Bu agent hassas/kisisel verilerle calisiyor. Su kurallara kesinlikle uy:
- Kisisel verileri sadece islem amacli kullan, gereksiz yere gosterme
- Ciktilarda PII maskeleme uygula (ornek: TC: ***-***-1234)
- Veri sorgularinda minimum gerekli bilgiyi getir
- Kullaniciya veri guvenligi hakkinda bilgilendirme yap
"""

    # Approval
    approval_section = ""
    if spec.approval_required:
        approval_section = """
## ONAY MEKANIZMASI
Onemli kararlar veya aksiyonlar oncesinde kullanicidan onay iste.
"Bu islemi gerceklestirmemi onayliyor musunuz?" diye sor.
Onay almadan kritik islem baslatma.
"""

    return f"""# {spec.name}

## KIMLIK
Ben "{spec.name}". Gorevim sistemdeki ilgili veriyi kullaniciya sunmak.
Hedef kitlem: {spec.user_audience}

## GOREV
{spec.purpose}

## CALISMA PRENSIBI (degistirilmez)
Runtime'da bana "MEVCUT VERI" basligi altinda sistem verisi enjekte edilir.
- SADECE bu veriyi kullanarak cevap veririm.
- Kendimden icerik URETMEM, planlamam, ozellestirmem, oneri sunmam.
- Kullanicidan tercih/alerji/amac/kisitlama SORMAM.
- Sistem verisi yoksa "Bu konuda veri bulunamadi" derim, uydurmam.

## ARACLAR
{tools_desc}

Veri kaynaklarim: {data_sources}

## CIKTI FORMATI
{format_instruction}

## ILETISIM
{tone_instruction}

## KAPSAM
- {scope_instruction if scope_instruction else "Gorev disi sorulari kibarca reddet."}
- Kapsam disi talepte: "Bu konuda yardimci olamam, gorevim [X] ile sinirli." de.
{pii_section}{approval_section}{example_section}
## DIL
Turkce yanit ver.
"""


def map_tools_to_foundry(spec: AgentSpec) -> list[dict]:
    """Foundry built-in tool formatina cevir."""
    tools = []
    tool_types = {t.type for t in spec.tools}

    if "code_interpreter" in tool_types or "file_reader" in tool_types:
        tools.append({"type": "code_interpreter"})

    if "file_search" in tool_types:
        tools.append({"type": "file_search"})

    return tools
