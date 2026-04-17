from dataclasses import dataclass
from ..spec.schema import AgentSpec, AgentType


@dataclass
class ArchitectDecision:
    selected_type: AgentType
    reason: str
    confidence: str  # "high" | "medium" | "low"


def select_architecture(spec: AgentSpec) -> ArchitectDecision:
    # 1. Hosted agent gereken durumlar
    if spec.needs_supervisor or spec.custom_state_required:
        return ArchitectDecision(
            selected_type=AgentType.HOSTED,
            reason="Supervisor veya ozel state yonetimi gerekiyor",
            confidence="high",
        )

    # 2. Workflow gereken durumlar — coklu karar noktasi varsa
    if spec.decision_points >= 3:
        return ArchitectDecision(
            selected_type=AgentType.WORKFLOW,
            reason=(
                f"{spec.decision_points} karar noktasi var. "
                "Workflow ile kontrollu akis uygun."
            ),
            confidence="high",
        )

    # 2b. Approval + coklu karar noktasi birlikte
    if spec.approval_required and spec.decision_points >= 2:
        return ArchitectDecision(
            selected_type=AgentType.WORKFLOW,
            reason="Approval + coklu karar noktasi, workflow uygun",
            confidence="high",
        )

    # 3. Yogun custom tool kombinasyonu varsa hosted olabilir
    tool_types = {t.type for t in spec.tools}
    if len(tool_types) >= 4:
        return ArchitectDecision(
            selected_type=AgentType.HOSTED,
            reason=f"Coklu tool turu ({len(tool_types)}), custom orchestration uygun",
            confidence="medium",
        )

    # 4. Default: prompt agent
    return ArchitectDecision(
        selected_type=AgentType.PROMPT,
        reason="Tekil amac, sinirli tool seti, instruction + built-in tools yeterli",
        confidence="high",
    )
