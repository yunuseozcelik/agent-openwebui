from ..spec.schema import AgentSpec


def generate_instructions(spec: AgentSpec) -> str:
    tools_desc = "\n".join(
        f"- {t.name}: {t.description}" for t in spec.tools
    ) if spec.tools else "- (ozel tool yok)"

    data_sources = ", ".join(spec.data_sources) if spec.data_sources else "yok"

    pii_warning = "\n- Hassas veri (PII) iceren ciktilar uretmekten kacin." if spec.contains_pii else ""

    return f"""Sen "{spec.name}" isimli bir AI agent'sin.

AMAC: {spec.purpose}

KULLANICI KITLESI: {spec.user_audience}

ERISEBILECEGIN VERI KAYNAKLARI: {data_sources}

KULLANABILECEGIN ARACLAR:
{tools_desc}

KURALLAR:
- Gorev taniminin DISINDAKI konularda yardim etme, nazikce kapsam disi oldugunu soyle.
- Cevaplarini net ve kisa tut.
- Emin olmadigin bilgide spekulasyon yapma, kullaniciya sor veya belirsizligi soyle.{pii_warning}

Kullaniciya Turkce yanit ver (kullanici baska dilde yazmadikca).
"""


def map_tools_to_foundry(spec: AgentSpec) -> list[dict]:
    """Foundry built-in tool formatina cev."""
    tools = []
    tool_types = {t.type for t in spec.tools}

    if "code_interpreter" in tool_types or "file_reader" in tool_types:
        tools.append({"type": "code_interpreter"})

    return tools
