"""Agent & Tool Registry.

Mevcut agent'lari, tool katalogu ve agent ekosistem iliskilerini saglar.
Builder Copilot ve Analyzer bunu kullanarak mevcut durumu bilerek yeni agent olusturur.
"""

from __future__ import annotations

import math

from agent_factory.deployment.foundry_client import list_agents, AgentInfo
from agent_factory.builder.spec.store import list_specs
from agent_factory.builder.spec.schema import AgentSpec


# ──────────────────────────────────────────────
#  Tool Katalogu
# ──────────────────────────────────────────────

TOOL_CATALOG = {
    "file_reader": {
        "label": "Dosya Okuyucu",
        "description": "Excel, CSV, PDF gibi dosyalari okuyabilir",
        "foundry_mapping": "code_interpreter",
        "examples": ["Excel analizi", "CSV parse", "PDF metin cikartma"],
        "compatible_with": ["code_interpreter"],  # Bu tool'la birlikte iyi calisir
    },
    "code_interpreter": {
        "label": "Kod Yorumlayici",
        "description": "Python kodu calistirabilir, hesaplama ve veri analizi yapabilir",
        "foundry_mapping": "code_interpreter",
        "examples": ["Veri analizi", "Grafik olusturma", "Istatistik hesaplama"],
        "compatible_with": ["file_reader", "db_query"],
    },
    "file_search": {
        "label": "Dosya Arama (RAG)",
        "description": "Dokuman koleksiyonu icerisinde arama yapabilir",
        "foundry_mapping": "file_search",
        "examples": ["Dokumantasyon arama", "Bilgi tabani sorgulama"],
        "compatible_with": ["api_call"],
    },
    "api_call": {
        "label": "API Cagrisi",
        "description": "Dis servislere HTTP istegi gonderebilir",
        "foundry_mapping": "function",
        "examples": ["REST API entegrasyonu", "Webhook tetikleme", "Dis veri cekme"],
        "compatible_with": ["db_query", "file_search"],
    },
    "db_query": {
        "label": "Veritabani Sorgusu",
        "description": "Veritabaninda SQL veya NoSQL sorgu calistirabilir",
        "foundry_mapping": "function",
        "examples": ["SQL sorgu", "Veri cekme", "Raporlama"],
        "compatible_with": ["code_interpreter", "api_call"],
    },
}


# ──────────────────────────────────────────────
#  Agent Ekosistem Analizi
# ──────────────────────────────────────────────

def _extract_agent_capabilities(agent: AgentInfo) -> dict:
    """Bir agent'in yeteneklerini cikar."""
    capabilities = {
        "name": agent.name,
        "id": agent.id,
        "tool_types": [],
        "data_domains": [],
        "can_provide": [],   # Bu agent baskalarına ne saglayabilir
        "can_consume": [],   # Bu agent baskalarindan ne alabilir
    }

    # Tool tiplerini cikar
    for t in agent.tools:
        if isinstance(t, dict):
            capabilities["tool_types"].append(t.get("type", "unknown"))

    # Instructions'dan domain cikar
    instr = (agent.instructions or "").lower()
    domain_keywords = {
        "musteri": "musteri_verileri",
        "sikayet": "sikayet_verileri",
        "satis": "satis_verileri",
        "finans": "finansal_veriler",
        "hr": "personel_verileri",
        "rapor": "raporlama",
        "analiz": "veri_analizi",
        "excel": "dosya_isleme",
        "pdf": "dokuman_isleme",
        "api": "dis_sistem_entegrasyonu",
        "veritaban": "veritabani_erisimi",
    }
    for keyword, domain in domain_keywords.items():
        if keyword in instr:
            capabilities["data_domains"].append(domain)

    # Saglayabilecekleri ve tuketebilecekleri
    if "raporlama" in capabilities["data_domains"] or "veri_analizi" in capabilities["data_domains"]:
        capabilities["can_provide"].append("analiz_sonuclari")
        capabilities["can_provide"].append("raporlar")

    if "dosya_isleme" in capabilities["data_domains"]:
        capabilities["can_provide"].append("islennis_veri")

    if "dis_sistem_entegrasyonu" in capabilities["data_domains"]:
        capabilities["can_provide"].append("dis_veri")
        capabilities["can_consume"].append("islennis_veri")

    if "veritabani_erisimi" in capabilities["data_domains"]:
        capabilities["can_provide"].append("ham_veri")

    return capabilities


def get_ecosystem_summary() -> str:
    """Agent ekosisteminin iliskileri ve etkilesim haritasi."""
    agents = list_agents()
    if not agents:
        return "Henuz agent ekosistemi yok."

    capabilities = [_extract_agent_capabilities(a) for a in agents]

    lines = [f"### Agent Ekosistemi ({len(agents)} agent)\n"]

    for cap in capabilities:
        lines.append(f"**{cap['name']}** (`{cap['id']}`)")

        if cap["tool_types"]:
            lines.append(f"  Araclar: {', '.join(cap['tool_types'])}")

        if cap["data_domains"]:
            lines.append(f"  Veri alanlari: {', '.join(cap['data_domains'])}")

        if cap["can_provide"]:
            lines.append(f"  Saglayabilir: {', '.join(cap['can_provide'])}")

        if cap["can_consume"]:
            lines.append(f"  Kullanabilir: {', '.join(cap['can_consume'])}")

        lines.append("")

    # Etkilesim onerileri
    if len(capabilities) >= 2:
        lines.append("### Potansiyel Etkilesimler\n")
        for i, a in enumerate(capabilities):
            for b in capabilities[i+1:]:
                interactions = _find_interactions(a, b)
                if interactions:
                    for interaction in interactions:
                        lines.append(f"- {interaction}")

    return "\n".join(lines)


def _find_interactions(a: dict, b: dict) -> list[str]:
    """Iki agent arasindaki potansiyel etkilesimleri bul."""
    interactions = []

    # A'nin sagladigi seyi B kullanabilir mi?
    for provided in a.get("can_provide", []):
        if provided in b.get("can_consume", []):
            interactions.append(
                f"**{a['name']}** → **{b['name']}**: "
                f"{a['name']} '{provided}' saglayabilir, {b['name']} bunu kullanabilir"
            )

    # B'nin sagladigi seyi A kullanabilir mi?
    for provided in b.get("can_provide", []):
        if provided in a.get("can_consume", []):
            interactions.append(
                f"**{b['name']}** → **{a['name']}**: "
                f"{b['name']} '{provided}' saglayabilir, {a['name']} bunu kullanabilir"
            )

    # Ortak tool'lar varsa paylasim onerebilir
    shared_tools = set(a.get("tool_types", [])) & set(b.get("tool_types", []))
    if shared_tools:
        interactions.append(
            f"**{a['name']}** <-> **{b['name']}**: "
            f"Ortak araclar: {', '.join(shared_tools)}"
        )

    # Tamamlayici domain'ler
    a_domains = set(a.get("data_domains", []))
    b_domains = set(b.get("data_domains", []))
    if a_domains and b_domains and not a_domains & b_domains:
        interactions.append(
            f"**{a['name']}** + **{b['name']}**: "
            f"Farkli alanlarda calisiyorlar, birlestirici bir agent faydali olabilir"
        )

    return interactions


def suggest_integrations_for_new_agent(
    purpose: str,
    tool_types: list[str],
) -> str:
    """Yeni agent icin mevcut agent'larla entegrasyon onerileri."""
    agents = list_agents()
    if not agents:
        return ""

    purpose_lower = purpose.lower()
    suggestions = []

    for agent in agents:
        agent_cap = _extract_agent_capabilities(agent)

        # Tool uyumu
        agent_tools = set(agent_cap.get("tool_types", []))
        new_tools = set(tool_types)
        shared = agent_tools & new_tools
        if shared:
            suggestions.append(
                f"**{agent.name}** ile ortak araclar var ({', '.join(shared)}). "
                f"Veri paylasimi veya birlikte calisma mumkun."
            )

        # Domain uyumu
        for domain in agent_cap.get("data_domains", []):
            if domain.replace("_", " ").split("_")[0] in purpose_lower:
                suggestions.append(
                    f"**{agent.name}** benzer veri alaniyla calisiyor ({domain}). "
                    f"Ciktisini girdi olarak kullanabilir veya birlikte calabilir."
                )
                break

        # Yeni agent'in ciktisini mevcut agent kullanabilir mi
        if agent_cap.get("can_consume"):
            suggestions.append(
                f"**{agent.name}** dis veri tuketebilir — "
                f"yeni agent'in ciktisini besleyebilirsiniz."
            )

    if not suggestions:
        return ""

    # Duplicate'leri kaldir
    unique = list(dict.fromkeys(suggestions))
    return "### Entegrasyon Onerileri\n\n" + "\n".join(f"- {s}" for s in unique[:5])


# ──────────────────────────────────────────────
#  Mevcut Ozet Fonksiyonlari
# ──────────────────────────────────────────────

def get_existing_agents_summary() -> str:
    """Mevcut agent'larin copilot'a verilecek ozet metni."""
    agents = list_agents()

    if not agents:
        return "Henuz hicbir agent olusturulmamis. Bu ilk agent olacak."

    lines = [f"Sistemde {len(agents)} mevcut agent var:\n"]
    for i, agent in enumerate(agents, 1):
        status = ""
        if agent.metadata.get("mock"):
            status = " (mock)"
        elif agent.metadata.get("status") == "draft":
            status = " (taslak)"

        lines.append(f"{i}. **{agent.name}**{status}")
        lines.append(f"   - ID: {agent.id}")
        lines.append(f"   - Model: {agent.model}")

        if agent.instructions:
            summary = agent.instructions.strip().replace("\n", " ")[:150]
            lines.append(f"   - Amac: {summary}...")

        if agent.tools:
            tool_types = [t.get("type", "unknown") if isinstance(t, dict) else str(t) for t in agent.tools]
            lines.append(f"   - Tool'lar: {', '.join(tool_types)}")

        lines.append("")

    return "\n".join(lines)


def get_existing_specs_summary() -> str:
    """Olusturulmus spec'lerin ozeti."""
    specs = list_specs()
    if not specs:
        return ""

    lines = [f"Olusturulmus {len(specs)} agent spec'i:\n"]
    for spec in specs[:10]:
        tools_str = ", ".join(t.name for t in spec.tools) if spec.tools else "yok"
        lines.append(
            f"- **{spec.name}** (ID: {spec.id}) | "
            f"Hedef: {spec.user_audience} | "
            f"Tool: {tools_str} | "
            f"Risk: {spec.risk_level.value}"
        )

    return "\n".join(lines)


def get_tool_catalog_summary() -> str:
    """Kullanilabilir tool tiplerinin ozet metni."""
    lines = ["Kullanilabilir tool tipleri:\n"]
    for tool_type, info in TOOL_CATALOG.items():
        lines.append(f"- **{tool_type}** ({info['label']}): {info['description']}")
        lines.append(f"  Ornekler: {', '.join(info['examples'])}")
        if info.get("compatible_with"):
            lines.append(f"  Uyumlu: {', '.join(info['compatible_with'])}")

    return "\n".join(lines)


def _build_new_agent_cap(
    name: str, purpose: str, tools: list[str],
) -> dict:
    """Yeni agent icin capability dict'i olustur."""
    cap = {
        "name": name,
        "id": "new",
        "tool_types": tools,
        "data_domains": [],
        "can_provide": [],
        "can_consume": [],
    }
    purpose_lower = (purpose or "").lower()
    domain_keywords = {
        "musteri": "musteri_verileri",
        "sikayet": "sikayet_verileri",
        "satis": "satis_verileri",
        "finans": "finansal_veriler",
        "hr": "personel_verileri",
        "rapor": "raporlama",
        "analiz": "veri_analizi",
        "excel": "dosya_isleme",
        "pdf": "dokuman_isleme",
        "api": "dis_sistem_entegrasyonu",
        "veritaban": "veritabani_erisimi",
    }
    for kw, domain in domain_keywords.items():
        if kw in purpose_lower:
            cap["data_domains"].append(domain)
    if "raporlama" in cap["data_domains"] or "veri_analizi" in cap["data_domains"]:
        cap["can_provide"].extend(["analiz_sonuclari", "raporlar"])
    if "dosya_isleme" in cap["data_domains"]:
        cap["can_provide"].append("islennis_veri")
    if "dis_sistem_entegrasyonu" in cap["data_domains"]:
        cap["can_provide"].append("dis_veri")
        cap["can_consume"].append("islennis_veri")
    if "veritabani_erisimi" in cap["data_domains"]:
        cap["can_provide"].append("ham_veri")
    return cap


def _collect_edges(all_caps: list[dict]) -> list[tuple]:
    """Tum agent ciftleri arasindaki edge'leri topla.

    Her agent cifti icin en onemli baglanti tipini sec:
    data_flow > shared_tool > complementary
    """
    # Once tum ham edge'leri topla, sonra cift bazinda birlestir
    raw: dict[tuple[str, str], list[tuple]] = {}
    priority = {"data_flow": 3, "shared_tool": 2, "complementary": 1}

    for i, a in enumerate(all_caps):
        for b in all_caps[i + 1:]:
            pair = (a["name"], b["name"])
            if pair not in raw:
                raw[pair] = []

            for provided in a.get("can_provide", []):
                if provided in b.get("can_consume", []):
                    raw[pair].append((a["name"], b["name"], provided, "data_flow"))
            for provided in b.get("can_provide", []):
                if provided in a.get("can_consume", []):
                    raw[pair].append((b["name"], a["name"], provided, "data_flow"))

            shared = set(a.get("tool_types", [])) & set(b.get("tool_types", []))
            if shared:
                raw[pair].append((a["name"], b["name"], ", ".join(sorted(shared)), "shared_tool"))

            a_d = set(a.get("data_domains", []))
            b_d = set(b.get("data_domains", []))
            if a_d and b_d and not a_d & b_d:
                raw[pair].append((a["name"], b["name"], "tamamlayici", "complementary"))

    # Her cift icin en yuksek oncelikli edge'i sec
    edges = []
    for pair, pair_edges in raw.items():
        if not pair_edges:
            continue
        best = max(pair_edges, key=lambda e: priority.get(e[3], 0))
        edges.append(best)

    return edges


# Tool tipi -> ikon/emoji mapping
_TOOL_ICONS = {
    "file_reader": "Dosya",
    "code_interpreter": "Kod",
    "file_search": "Arama",
    "api_call": "API",
    "db_query": "DB",
}


def build_interaction_graph(
    new_agent_name: str,
    new_agent_purpose: str,
    new_agent_tools: list[str],
):
    """Yeni agent ve mevcut agent'lar arasi etkilesim grafigi olusturur.

    Returns a plotly Figure or None if no existing agents.
    """
    import plotly.graph_objects as go

    agents = list_agents()
    new_cap = _build_new_agent_cap(new_agent_name, new_agent_purpose, new_agent_tools)

    all_caps = [_extract_agent_capabilities(a) for a in agents]
    all_caps.append(new_cap)

    n = len(all_caps)
    if n < 2:
        return None

    # --- Layout: yeni agent merkezde, mevcutlar etrafinda ---
    positions = {}
    existing_count = n - 1
    radius = 3.0
    # Ust taraftan baslat (-pi/2) boylece daha simetrik olur
    for i, cap in enumerate(all_caps[:-1]):
        angle = -math.pi / 2 + 2 * math.pi * i / max(existing_count, 1)
        positions[cap["name"]] = (math.cos(angle) * radius, math.sin(angle) * radius)
    positions[new_agent_name] = (0.0, 0.0)

    edges = _collect_edges(all_caps)

    # --- Renk paleti ---
    EDGE_STYLES = {
        "data_flow":     {"color": "#3B82F6", "width": 2.5, "dash": "solid",  "label": "Veri Akisi"},
        "shared_tool":   {"color": "#10B981", "width": 2.0, "dash": "dash",   "label": "Ortak Arac"},
        "complementary": {"color": "#F59E0B", "width": 1.5, "dash": "dot",    "label": "Tamamlayici"},
    }
    BG_COLOR = "#0F172A"       # koyu lacivert arka plan
    GRID_COLOR = "#1E293B"
    EXISTING_COLOR = "#6366F1"  # indigo
    EXISTING_LINE = "#818CF8"
    NEW_COLOR = "#F43F5E"       # rose/kirmizi
    NEW_LINE = "#FB7185"
    TEXT_COLOR = "#E2E8F0"      # acik gri metin

    fig = go.Figure()

    # --- Edge'ler ---
    # Ayni tip edge'leri birlestir, her tip icin sadece 1 legend entry
    legend_added = set()
    for from_n, to_n, label, etype in edges:
        x0, y0 = positions[from_n]
        x1, y1 = positions[to_n]
        style = EDGE_STYLES[etype]

        show_legend = etype not in legend_added
        legend_added.add(etype)

        # Bezier benzeri hafif kavisli cizgi (midpoint'i hafif kaydir)
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2
        # Hafif kavis icin perpendicular offset
        dx, dy = x1 - x0, y1 - y0
        length = math.sqrt(dx * dx + dy * dy) or 1
        ox = -dy / length * 0.25
        oy = dx / length * 0.25
        cmx, cmy = mx + ox, my + oy

        fig.add_trace(go.Scatter(
            x=[x0, cmx, x1],
            y=[y0, cmy, y1],
            mode="lines",
            line=dict(color=style["color"], width=style["width"], dash=style["dash"]),
            hoverinfo="text",
            hovertext=f"{from_n} ↔ {to_n}<br>{label}",
            name=style["label"] if show_legend else None,
            showlegend=show_legend,
            legendgroup=etype,
        ))

        # Edge label — kavis noktasinda
        _label_display = label.replace("_", " ").title() if len(label) < 20 else label[:18] + "…"
        fig.add_trace(go.Scatter(
            x=[cmx],
            y=[cmy + 0.2],
            mode="text",
            text=[_label_display],
            textfont=dict(size=9, color=style["color"]),
            hoverinfo="skip",
            showlegend=False,
        ))

    # --- Mevcut agent node'lari ---
    for cap in all_caps[:-1]:
        x, y = positions[cap["name"]]
        tools_list = cap.get("tool_types", [])
        tools_badges = " | ".join(_TOOL_ICONS.get(t, t) for t in tools_list) or "—"
        domains = ", ".join(d.replace("_", " ") for d in cap.get("data_domains", [])) or "—"

        hover = (
            f"<b>{cap['name']}</b><br>"
            f"Araclar: {tools_badges}<br>"
            f"Alanlar: {domains}"
        )

        # Dis halka (glow efekti)
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers",
            marker=dict(
                size=52, color=EXISTING_COLOR, opacity=0.15,
                line=dict(width=0),
            ),
            hoverinfo="skip",
            showlegend=False,
        ))
        # Ana node
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            marker=dict(
                size=36, color=EXISTING_COLOR,
                line=dict(width=2, color=EXISTING_LINE),
            ),
            text=[cap["name"]],
            textposition="bottom center",
            textfont=dict(size=11, color=TEXT_COLOR, family="Arial"),
            hoverinfo="text",
            hovertext=hover,
            showlegend=False,
        ))
        # Tool badge'leri node icinde
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="text",
            text=[str(len(tools_list))],
            textfont=dict(size=10, color="white", family="Arial Black"),
            hoverinfo="skip",
            showlegend=False,
        ))

    # --- Yeni agent node (vurgulu) ---
    nx, ny = positions[new_agent_name]
    new_tools_badges = " | ".join(_TOOL_ICONS.get(t, t) for t in new_agent_tools) or "—"
    new_hover = (
        f"<b>✦ {new_agent_name}</b> (YENI)<br>"
        f"Araclar: {new_tools_badges}<br>"
        f"Amac: {new_agent_purpose[:80]}"
    )

    # Dis halka (glow)
    fig.add_trace(go.Scatter(
        x=[nx], y=[ny],
        mode="markers",
        marker=dict(size=68, color=NEW_COLOR, opacity=0.12, line=dict(width=0)),
        hoverinfo="skip",
        showlegend=False,
    ))
    # Orta halka
    fig.add_trace(go.Scatter(
        x=[nx], y=[ny],
        mode="markers",
        marker=dict(size=54, color=NEW_COLOR, opacity=0.25, line=dict(width=0)),
        hoverinfo="skip",
        showlegend=False,
    ))
    # Ana node
    fig.add_trace(go.Scatter(
        x=[nx], y=[ny],
        mode="markers+text",
        marker=dict(
            size=44, color=NEW_COLOR,
            line=dict(width=3, color=NEW_LINE),
        ),
        text=[f"✦ {new_agent_name}"],
        textposition="bottom center",
        textfont=dict(size=12, color=NEW_LINE, family="Arial Black"),
        hoverinfo="text",
        hovertext=new_hover,
        showlegend=False,
    ))
    # "YENI" etiketi
    fig.add_trace(go.Scatter(
        x=[nx], y=[ny + 0.15],
        mode="text",
        text=["YENI"],
        textfont=dict(size=8, color="white", family="Arial Black"),
        hoverinfo="skip",
        showlegend=False,
    ))

    # --- Annotation: connection counts ---
    new_connections = sum(
        1 for e in edges
        if new_agent_name in (e[0], e[1])
    )
    total_edges = len(edges)

    fig.add_annotation(
        x=0.01, y=0.99, xref="paper", yref="paper",
        text=(
            f"<b>{n} Agent</b> · {total_edges} Baglanti<br>"
            f"<span style='color:{NEW_LINE}'>✦ Yeni agent: {new_connections} baglanti</span>"
        ),
        showarrow=False,
        font=dict(size=11, color=TEXT_COLOR),
        align="left",
        bgcolor="rgba(30,41,59,0.8)",
        bordercolor="#334155",
        borderwidth=1,
        borderpad=8,
    )

    # --- Layout ---
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.02,
            xanchor="center", x=0.5,
            font=dict(color=TEXT_COLOR, size=11),
            bgcolor="rgba(30,41,59,0.8)",
            bordercolor="#334155",
            borderwidth=1,
        ),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[-radius - 1.5, radius + 1.5],
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            scaleanchor="x", scaleratio=1,
            range=[-radius - 1.5, radius + 1.5],
        ),
        plot_bgcolor=BG_COLOR,
        paper_bgcolor=BG_COLOR,
        margin=dict(l=10, r=10, t=15, b=40),
        height=520,
        width=650,
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_size=12,
            font_color=TEXT_COLOR,
            bordercolor="#475569",
        ),
    )

    return fig


def build_copilot_context() -> str:
    """Copilot'a verilecek tam baglam metni."""
    sections = []

    # Mevcut agent'lar
    agents_summary = get_existing_agents_summary()
    sections.append(f"## MEVCUT AGENTLAR\n{agents_summary}")

    # Ekosistem
    ecosystem = get_ecosystem_summary()
    if ecosystem and "yok" not in ecosystem:
        sections.append(f"## AGENT EKOSISTEMI\n{ecosystem}")

    # Mevcut spec'ler
    specs_summary = get_existing_specs_summary()
    if specs_summary:
        sections.append(f"## OLUSTURULMUS SPECLER\n{specs_summary}")

    # Tool katalogu
    tools_summary = get_tool_catalog_summary()
    sections.append(f"## KULLANILABILIR TOOL TIPLERI\n{tools_summary}")

    return "\n\n".join(sections)
