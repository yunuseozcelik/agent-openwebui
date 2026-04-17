from dataclasses import dataclass
from ..spec.schema import AgentSpec
from .rules import RULES


@dataclass
class Violation:
    rule_id: str
    description: str
    severity: str


@dataclass
class PolicyResult:
    passed: bool
    violations: list[Violation]

    @property
    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "error"]

    @property
    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity == "warning"]


def evaluate(spec: AgentSpec) -> PolicyResult:
    violations = [
        Violation(rule.id, rule.description, rule.severity)
        for rule in RULES
        if not rule.check(spec)
    ]
    has_errors = any(v.severity == "error" for v in violations)
    return PolicyResult(passed=not has_errors, violations=violations)
