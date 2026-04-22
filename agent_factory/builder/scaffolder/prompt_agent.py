import json
from pathlib import Path
from ..spec.schema import AgentSpec
from .instructions import generate_instructions, map_tools_to_foundry
from agent_factory.config import AZURE_OPENAI_DEPLOYMENT, FOUNDRY_AGENT_MODEL, OPENAI_WORKER_MODEL

AGENT_DIR = Path("generated/agents")
AGENT_DIR.mkdir(parents=True, exist_ok=True)


def scaffold_prompt_agent(
    spec: AgentSpec,
    wizard_answers: dict | None = None,
    custom_instructions: str | None = None,
) -> dict:
    """AgentSpec'ten Foundry create_agent API'si icin definition uret.

    custom_instructions: LLM tarafindan olusturulmus zengin prompt (varsa).
    Yoksa template-based fallback kullanilir.
    """
    instructions = custom_instructions or generate_instructions(spec, wizard_answers)
    model = FOUNDRY_AGENT_MODEL or AZURE_OPENAI_DEPLOYMENT or OPENAI_WORKER_MODEL

    answers = wizard_answers or {}
    definition = {
        "spec_id": spec.id,
        "name": spec.name,
        "model": model,
        "instructions": instructions,
        "tools": map_tools_to_foundry(spec),
        "metadata": {
            "generated_by": "agent-factory",
            "spec_version": str(spec.version),
            "risk_level": spec.risk_level.value,
            "audience": answers.get("audience", ""),
            "tone": answers.get("tone", ""),
            "output_format": answers.get("output_format", ""),
            "scope": answers.get("scope", ""),
        },
    }

    path = AGENT_DIR / f"{spec.id}_definition.json"
    path.write_text(json.dumps(definition, indent=2, ensure_ascii=False), encoding="utf-8")

    return definition
