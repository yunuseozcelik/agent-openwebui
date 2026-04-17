from dataclasses import dataclass
from typing import Callable
from ..spec.schema import AgentSpec


@dataclass
class Rule:
    id: str
    description: str
    check: Callable[[AgentSpec], bool]  # True = gecti, False = ihlal
    severity: str  # "error" | "warning"


RULES: list[Rule] = [
    Rule(
        id="pii_requires_approval",
        description="PII iceren agent'lar approval zorunludur",
        check=lambda s: not s.contains_pii or s.approval_required,
        severity="error",
    ),
    Rule(
        id="high_risk_requires_approval",
        description="Yuksek riskli agent'lar approval zorunludur",
        check=lambda s: s.risk_level != "high" or s.approval_required,
        severity="error",
    ),
    Rule(
        id="max_tools",
        description="Agent'a 10'dan fazla tool tanimlanamaz",
        check=lambda s: len(s.tools) <= 10,
        severity="error",
    ),
    Rule(
        id="has_purpose",
        description="Agent'in purpose'u en az 10 karakter olmali",
        check=lambda s: len(s.purpose) >= 10,
        severity="error",
    ),
    Rule(
        id="name_format",
        description="Agent ismi sadece harf, rakam, bosluk, tire icermeli",
        check=lambda s: all(c.isalnum() or c in " -_" for c in s.name),
        severity="warning",
    ),
]
