from ..spec.schema import AgentSpec
from ..architect.selector import ArchitectDecision


_RISK_COLORS = {"low": "#10b981", "medium": "#f59e0b", "high": "#ef4444"}
_RISK_LABELS = {"low": "Dusuk", "medium": "Orta", "high": "Yuksek"}


def build_review_summary(spec: AgentSpec, decision: ArchitectDecision, definition: dict) -> str:
    tools_str = ", ".join(f"`{t.name}`" for t in spec.tools) or "`—`"
    risk_val = spec.risk_level.value
    risk_color = _RISK_COLORS.get(risk_val, "#94a3b8")
    risk_label = _RISK_LABELS.get(risk_val, risk_val)

    data_sources = ", ".join(spec.data_sources) if spec.data_sources else "—"
    pii = "Evet" if spec.contains_pii else "Hayir"
    approval = "Evet" if spec.approval_required else "Hayir"

    return (
        f"### Deployment Ozeti\n\n"
        f"| Ozellik | Deger |\n"
        f"|:--------|:------|\n"
        f"| **Isim** | {spec.name} |\n"
        f"| **Amac** | {spec.purpose} |\n"
        f"| **Hedef Kitle** | {spec.user_audience} |\n"
        f"| **Mimari** | {decision.selected_type.value.upper()} — {decision.reason} |\n"
        f"| **Model** | `{definition['model']}` |\n"
        f"| **Veri Kaynaklari** | {data_sources} |\n"
        f"| **Araclar** | {tools_str} |\n"
        f"| **Risk** | <span style='color:{risk_color}'>{risk_label}</span> |\n"
        f"| **PII** | {pii} |\n"
        f"| **Onay Gerekli** | {approval} |\n"
        f"| **Hedef** | Azure AI Foundry |\n"
        f"| **Spec ID** | `{spec.id}` |\n"
    )
