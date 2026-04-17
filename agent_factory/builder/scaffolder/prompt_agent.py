import json
from pathlib import Path
from ..spec.schema import AgentSpec
from .instructions import generate_instructions, map_tools_to_foundry
from agent_factory.config import OPENAI_WORKER_MODEL

AGENT_DIR = Path("generated/agents")
AGENT_DIR.mkdir(parents=True, exist_ok=True)


def scaffold_prompt_agent(spec: AgentSpec) -> dict:
    """AgentSpec'ten Foundry create_agent API'si icin definition uret."""
    definition = {
        "spec_id": spec.id,
        "name": spec.name,
        "model": OPENAI_WORKER_MODEL,
        "instructions": generate_instructions(spec),
        "tools": map_tools_to_foundry(spec),
        "metadata": {
            "generated_by": "agent-factory",
            "spec_version": str(spec.version),
            "risk_level": spec.risk_level.value,
        },
    }

    path = AGENT_DIR / f"{spec.id}_definition.json"
    path.write_text(json.dumps(definition, indent=2, ensure_ascii=False))

    return definition
