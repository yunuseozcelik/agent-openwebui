"""Ana orchestrator: pipeline'i calistirir."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field

from .spec.schema import AgentSpec
from .spec.store import load_spec
from .policy.evaluator import evaluate, PolicyResult
from .architect.selector import select_architecture, ArchitectDecision
from .scaffolder.prompt_agent import scaffold_prompt_agent
from .review.reviewer import build_review_summary


@dataclass
class PipelineStage:
    name: str
    status: str  # "pass" | "fail" | "pending"
    data: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    spec_id: str
    stages: list[PipelineStage] = field(default_factory=list)
    ready_for_approval: bool = False
    review_summary: str = ""
    definition: dict = field(default_factory=dict)


def run_pipeline(spec_id: str) -> PipelineResult:
    """
    Policy -> Architect -> Scaffold -> Review
    Tum pipeline'i calistirir.
    """
    spec = load_spec(spec_id)
    stages: list[PipelineStage] = []

    # 1. Policy
    policy_result = evaluate(spec)
    stages.append(PipelineStage(
        name="policy",
        status="pass" if policy_result.passed else "fail",
        data={
            "violations": [asdict(v) for v in policy_result.violations],
        },
    ))
    if not policy_result.passed:
        error_msgs = [f"- {v.description}" for v in policy_result.errors]
        return PipelineResult(
            spec_id=spec_id,
            stages=stages,
            review_summary=f"Policy kontrolu basarisiz:\n" + "\n".join(error_msgs),
        )

    # 2. Architect
    decision = select_architecture(spec)
    stages.append(PipelineStage(
        name="architect",
        status="pass",
        data=asdict(decision),
    ))

    # 3. Scaffold — MVP'de her tip prompt agent olarak deploy edilir.
    # Architect karari bilgilendirme amacli, ileride tip bazli scaffolding eklenecek.
    definition = scaffold_prompt_agent(spec)
    if decision.selected_type.value != "prompt":
        definition["metadata"]["ideal_type"] = decision.selected_type.value
        definition["metadata"]["ideal_type_reason"] = decision.reason
    stages.append(PipelineStage(
        name="scaffold",
        status="pass",
        data={"definition_keys": list(definition.keys())},
    ))

    # 4. Review
    summary = build_review_summary(spec, decision, definition)
    stages.append(PipelineStage(
        name="review",
        status="pass",
        data={"summary": summary},
    ))

    return PipelineResult(
        spec_id=spec_id,
        stages=stages,
        ready_for_approval=True,
        review_summary=summary,
        definition=definition,
    )
