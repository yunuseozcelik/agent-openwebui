from ..spec.schema import AgentSpec
from ..architect.selector import ArchitectDecision


def build_review_summary(spec: AgentSpec, decision: ArchitectDecision, definition: dict) -> str:
    tools_str = ", ".join(t.name for t in spec.tools) or "yok"
    return f"""
**AGENT DEPLOYMENT OZET**

| Alan | Deger |
|---|---|
| Isim | {spec.name} |
| Amac | {spec.purpose} |
| Kullanici | {spec.user_audience} |
| Secilen Mimari | {decision.selected_type.value.upper()} |
| Gerekce | {decision.reason} |
| Model | {definition['model']} |
| Veri Kaynaklari | {', '.join(spec.data_sources) or 'yok'} |
| Tool'lar | {tools_str} |
| Risk Seviyesi | {spec.risk_level.value} |
| PII Iceriyor mu | {'Evet' if spec.contains_pii else 'Hayir'} |
| Approval Gerekli | {'Evet' if spec.approval_required else 'Hayir'} |
| Deploy Hedefi | Azure AI Foundry |

**Spec ID:** `{spec.id}`
"""
