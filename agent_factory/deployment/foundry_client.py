"""Azure AI Foundry deployment client.

Foundry SDK kurulu degilse veya credential yoksa mock mod calisir.
Mevcut agent'lari listeleyebilir, detay cekebilir.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from agent_factory.config import FOUNDRY_PROJECT_ENDPOINT

AGENT_DIR = Path("generated/agents")
AGENT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DeploymentResult:
    success: bool
    foundry_agent_id: str | None = None
    error: str | None = None
    mock: bool = False
    raw: dict | None = None


@dataclass
class AgentInfo:
    """Foundry'deki veya local'deki bir agent'in ozet bilgisi."""
    id: str
    name: str
    model: str
    instructions: str = ""
    tools: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    source: str = "foundry"  # "foundry" | "local"


def _get_foundry_client():
    """Foundry SDK varsa client dondur, yoksa None."""
    if not FOUNDRY_PROJECT_ENDPOINT:
        return None
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
        return AIProjectClient(
            endpoint=FOUNDRY_PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )
    except ImportError:
        return None
    except Exception:
        return None


def list_agents() -> list[AgentInfo]:
    """Mevcut agent'lari listele. Foundry + local deploy kayitlari."""
    agents: list[AgentInfo] = []

    # 1. Foundry'den cek
    client = _get_foundry_client()
    if client:
        try:
            foundry_agents = client.agents.list_agents()
            for a in foundry_agents:
                agents.append(AgentInfo(
                    id=a.id,
                    name=a.name or "Unnamed",
                    model=a.model or "",
                    instructions=getattr(a, "instructions", "") or "",
                    tools=getattr(a, "tools", []) or [],
                    metadata=getattr(a, "metadata", {}) or {},
                    source="foundry",
                ))
        except Exception:
            pass

    # 2. Local deploy kayitlarindan cek (mock dahil)
    for path in AGENT_DIR.glob("*_deployed*.json"):
        try:
            data = json.loads(path.read_text())
            agent_id = data.get("foundry_agent_id", "")
            # Foundry'den zaten cektiysek duplicate yapma
            if any(a.id == agent_id for a in agents):
                continue
            agents.append(AgentInfo(
                id=agent_id,
                name=data.get("name", "Unknown"),
                model=data.get("model", ""),
                instructions=data.get("instructions", ""),
                tools=data.get("tools", []),
                source="local",
                metadata={"mock": data.get("mock", False)},
            ))
        except Exception:
            continue

    # 3. Local spec + definition dosyalarindan henuz deploy edilmemisleri de ekle
    for path in AGENT_DIR.glob("*_definition.json"):
        try:
            data = json.loads(path.read_text())
            spec_id = data.get("spec_id", "")
            agent_name = data.get("name", "Unknown")
            # Zaten deploy edilmis mi kontrol et
            if any(a.name == agent_name for a in agents):
                continue
            agents.append(AgentInfo(
                id=f"draft_{spec_id}",
                name=agent_name,
                model=data.get("model", ""),
                instructions=data.get("instructions", ""),
                tools=data.get("tools", []),
                metadata={**data.get("metadata", {}), "status": "draft"},
                source="local",
            ))
        except Exception:
            continue

    return agents


def get_agent_detail(agent_id: str) -> AgentInfo | None:
    """Tek bir agent'in detayini cek."""
    # Foundry'den dene
    client = _get_foundry_client()
    if client and not agent_id.startswith(("mock_", "draft_")):
        try:
            a = client.agents.get_agent(agent_id)
            return AgentInfo(
                id=a.id,
                name=a.name or "Unnamed",
                model=a.model or "",
                instructions=getattr(a, "instructions", "") or "",
                tools=getattr(a, "tools", []) or [],
                metadata=getattr(a, "metadata", {}) or {},
                source="foundry",
            )
        except Exception:
            pass

    # Local'den ara
    for path in AGENT_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            if data.get("foundry_agent_id") == agent_id or data.get("spec_id") == agent_id:
                return AgentInfo(
                    id=agent_id,
                    name=data.get("name", "Unknown"),
                    model=data.get("model", ""),
                    instructions=data.get("instructions", ""),
                    tools=data.get("tools", []),
                    metadata=data.get("metadata", {}),
                    source="local",
                )
        except Exception:
            continue

    return None


def deploy_prompt_agent(definition: dict) -> DeploymentResult:
    """Foundry'ye deploy et. SDK yoksa mock sonuc don."""
    client = _get_foundry_client()
    if not client:
        return _mock_deploy(definition)

    try:
        agent = client.agents.create_agent(
            model=definition["model"],
            name=definition["name"],
            instructions=definition["instructions"],
            tools=definition["tools"],
            metadata=definition.get("metadata", {}),
        )

        result_data = {
            "foundry_agent_id": agent.id,
            "name": agent.name,
            "model": agent.model,
            "created_at": str(agent.created_at),
        }

        log_path = AGENT_DIR / f"{definition['spec_id']}_deployed.json"
        log_path.write_text(json.dumps(result_data, indent=2, ensure_ascii=False))

        return DeploymentResult(
            success=True,
            foundry_agent_id=agent.id,
            raw=result_data,
        )
    except Exception as e:
        return DeploymentResult(success=False, error=str(e))


def _mock_deploy(definition: dict) -> DeploymentResult:
    """Foundry SDK olmadan mock deployment."""
    mock_id = f"mock_agent_{uuid.uuid4().hex[:8]}"

    result_data = {
        "foundry_agent_id": mock_id,
        "name": definition["name"],
        "model": definition["model"],
        "instructions": definition.get("instructions", ""),
        "tools": definition.get("tools", []),
        "metadata": definition.get("metadata", {}),
        "mock": True,
    }

    log_path = AGENT_DIR / f"{definition['spec_id']}_deployed_mock.json"
    log_path.write_text(json.dumps(result_data, indent=2, ensure_ascii=False))

    return DeploymentResult(
        success=True,
        foundry_agent_id=mock_id,
        mock=True,
        raw=result_data,
    )
