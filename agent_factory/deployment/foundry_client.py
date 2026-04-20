"""Azure AI Foundry deployment client.

Foundry SDK kurulu degilse veya credential yoksa mock mod calisir.
Mevcut agent'lari listeleyebilir, detay cekebilir.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from agent_factory.config import (
    AZURE_RESOURCE_GROUP,
    AZURE_SUBSCRIPTION_ID,
    FOUNDRY_ACCOUNT_NAME,
    FOUNDRY_ACTIVITY_ENDPOINT,
    FOUNDRY_AGENT_DEPLOYMENT_NAME,
    FOUNDRY_AGENT_DEPLOYMENT_TYPE,
    FOUNDRY_AGENT_MODEL,
    FOUNDRY_APPLICATION_NAME,
    FOUNDRY_MANAGEMENT_API_VERSION,
    FOUNDRY_PROJECT_ENDPOINT,
    FOUNDRY_PROJECT_NAME,
    FOUNDRY_RESPONSES_ENDPOINT,
    FOUNDRY_WORKFLOW_AGENT_NAME,
)
from agent_factory.deployment.seed_agents import SEED_AGENT_DEFINITIONS

AGENT_DIR = Path("generated/agents")
AGENT_DIR.mkdir(parents=True, exist_ok=True)

WORKFLOW_TOPOLOGY_DIR = Path("generated/workflows")
WORKFLOW_TOPOLOGY_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DeploymentResult:
    success: bool
    foundry_agent_id: str | None = None
    error: str | None = None
    mock: bool = False
    application_updated: bool = False
    application_update_error: str | None = None
    application_update_raw: dict | None = None
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


@dataclass
class FoundryEndpointConfig:
    """Resolved Foundry coordinates from env vars and application endpoints."""

    project_endpoint: str = ""
    account_name: str = ""
    project_name: str = ""
    application_name: str = ""
    responses_endpoint: str = ""
    activity_endpoint: str = ""


def _parse_application_endpoint(endpoint: str) -> FoundryEndpointConfig:
    """Parse a Foundry Agent Application protocol endpoint."""
    if not endpoint:
        return FoundryEndpointConfig()

    parsed = urlparse(endpoint)
    parts = [part for part in parsed.path.split("/") if part]
    config = FoundryEndpointConfig()

    if parsed.netloc.endswith(".services.ai.azure.com"):
        config.account_name = parsed.netloc.split(".services.ai.azure.com", 1)[0]

    try:
        project_index = parts.index("projects")
        config.project_name = parts[project_index + 1]
        config.project_endpoint = f"{parsed.scheme}://{parsed.netloc}/api/projects/{config.project_name}"
    except (ValueError, IndexError):
        pass

    try:
        app_index = parts.index("applications")
        config.application_name = parts[app_index + 1]
    except (ValueError, IndexError):
        pass

    return config


def _resolve_foundry_config() -> FoundryEndpointConfig:
    """Resolve Foundry config from explicit vars, then protocol endpoints."""
    inferred = _parse_application_endpoint(FOUNDRY_RESPONSES_ENDPOINT) or FoundryEndpointConfig()
    if not inferred.project_endpoint:
        inferred = _parse_application_endpoint(FOUNDRY_ACTIVITY_ENDPOINT)

    return FoundryEndpointConfig(
        project_endpoint=FOUNDRY_PROJECT_ENDPOINT or inferred.project_endpoint,
        account_name=FOUNDRY_ACCOUNT_NAME or inferred.account_name,
        project_name=FOUNDRY_PROJECT_NAME or inferred.project_name,
        application_name=FOUNDRY_APPLICATION_NAME or inferred.application_name,
        responses_endpoint=FOUNDRY_RESPONSES_ENDPOINT,
        activity_endpoint=FOUNDRY_ACTIVITY_ENDPOINT,
    )


def _missing_management_config(config: FoundryEndpointConfig) -> list[str]:
    missing = []
    required = {
        "AZURE_SUBSCRIPTION_ID": AZURE_SUBSCRIPTION_ID,
        "AZURE_RESOURCE_GROUP": AZURE_RESOURCE_GROUP,
        "FOUNDRY_ACCOUNT_NAME": config.account_name,
        "FOUNDRY_PROJECT_NAME": config.project_name,
        "FOUNDRY_APPLICATION_NAME": config.application_name,
        "FOUNDRY_AGENT_DEPLOYMENT_NAME": FOUNDRY_AGENT_DEPLOYMENT_NAME,
    }
    for key, value in required.items():
        if not value:
            missing.append(key)
    return missing


def _get_access_token(scope: str) -> str:
    """Get an Azure AD token from configured credentials."""
    try:
        return _get_cli_access_token(scope)["accessToken"]
    except Exception:
        pass

    try:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
        return credential.get_token(scope).token
    except Exception as exc:
        raise RuntimeError(f"Azure authentication failed: {exc}") from exc


def _get_cli_access_token(scope: str) -> dict:
    """Get a token with a specific Azure CLI executable path."""
    az_path = os.getenv("AZURE_CLI_PATH") or r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
    resource = scope.removesuffix("/.default")
    env = os.environ.copy()
    config_dir = env.get("AZURE_CONFIG_DIR")
    if config_dir and not os.path.isabs(config_dir):
        env["AZURE_CONFIG_DIR"] = str(Path(config_dir).resolve())

    completed = subprocess.run(
        [
            az_path,
            "account",
            "get-access-token",
            "--resource",
            resource,
            "--output",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "az get-access-token failed").strip())
    return json.loads(completed.stdout)


class AzureCliPathCredential:
    """TokenCredential backed by a configured az.cmd path."""

    def get_token(self, *scopes, **kwargs):
        from azure.core.credentials import AccessToken

        scope = scopes[0] if scopes else "https://management.azure.com/.default"
        data = _get_cli_access_token(scope)
        expires_on = data.get("expires_on") or data.get("expiresOnTimestamp")
        if expires_on is None:
            expires_on = int(time.time()) + 3000
        return AccessToken(data["accessToken"], int(expires_on))


def _management_headers() -> dict[str, str]:
    token = _get_access_token("https://management.azure.com/.default")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _agent_deployment_url(config: FoundryEndpointConfig, deployment_name: str | None = None) -> str:
    name = deployment_name or FOUNDRY_AGENT_DEPLOYMENT_NAME
    return (
        "https://management.azure.com/subscriptions/"
        f"{AZURE_SUBSCRIPTION_ID}/resourceGroups/{AZURE_RESOURCE_GROUP}"
        "/providers/Microsoft.CognitiveServices/accounts/"
        f"{config.account_name}/projects/{config.project_name}"
        f"/applications/{config.application_name}/agentDeployments/{name}"
        f"?api-version={FOUNDRY_MANAGEMENT_API_VERSION}"
    )


def _agent_application_url(config: FoundryEndpointConfig) -> str:
    return (
        "https://management.azure.com/subscriptions/"
        f"{AZURE_SUBSCRIPTION_ID}/resourceGroups/{AZURE_RESOURCE_GROUP}"
        "/providers/Microsoft.CognitiveServices/accounts/"
        f"{config.account_name}/projects/{config.project_name}"
        f"/applications/{config.application_name}"
        f"?api-version={FOUNDRY_MANAGEMENT_API_VERSION}"
    )


def _agent_application_list_agents_url(config: FoundryEndpointConfig) -> str:
    return (
        "https://management.azure.com/subscriptions/"
        f"{AZURE_SUBSCRIPTION_ID}/resourceGroups/{AZURE_RESOURCE_GROUP}"
        "/providers/Microsoft.CognitiveServices/accounts/"
        f"{config.account_name}/projects/{config.project_name}"
        f"/applications/{config.application_name}/listAgents"
        f"?api-version={FOUNDRY_MANAGEMENT_API_VERSION}"
    )


def _get_foundry_client():
    """Foundry SDK varsa client dondur, yoksa None."""
    config = _resolve_foundry_config()
    if not config.project_endpoint:
        return None
    try:
        from azure.ai.projects import AIProjectClient
        return AIProjectClient(
            endpoint=config.project_endpoint,
            credential=AzureCliPathCredential(),
            allow_preview=True,
        )
    except ImportError:
        return None
    except Exception:
        return None


def get_agent_deployment(deployment_name: str | None = None) -> dict:
    """Read an Agent Application deployment from ARM."""
    config = _resolve_foundry_config()
    missing = _missing_management_config(config)
    if missing:
        raise RuntimeError(f"Missing Foundry management config: {', '.join(missing)}")

    response = requests.get(
        _agent_deployment_url(config, deployment_name),
        headers=_management_headers(),
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Foundry deployment GET failed ({response.status_code}): {response.text}")
    return response.json()


def update_agent_deployment(payload: dict, deployment_name: str | None = None) -> dict:
    """Create or update an Agent Application deployment through ARM."""
    config = _resolve_foundry_config()
    missing = _missing_management_config(config)
    if missing:
        raise RuntimeError(f"Missing Foundry management config: {', '.join(missing)}")

    response = requests.put(
        _agent_deployment_url(config, deployment_name),
        headers=_management_headers(),
        data=json.dumps(payload),
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"Foundry deployment PUT failed ({response.status_code}): {response.text}")
    if response.text:
        return response.json()
    return {}


def get_agent_application() -> dict:
    """Read the configured Agent Application from ARM."""
    config = _resolve_foundry_config()
    missing = _missing_management_config(config)
    missing = [item for item in missing if item != "FOUNDRY_AGENT_DEPLOYMENT_NAME"]
    if missing:
        raise RuntimeError(f"Missing Foundry application config: {', '.join(missing)}")

    response = requests.get(
        _agent_application_url(config),
        headers=_management_headers(),
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Foundry application GET failed ({response.status_code}): {response.text}")
    return response.json()


def update_agent_application(payload: dict) -> dict:
    """Update the configured Agent Application through ARM."""
    config = _resolve_foundry_config()
    missing = _missing_management_config(config)
    missing = [item for item in missing if item != "FOUNDRY_AGENT_DEPLOYMENT_NAME"]
    if missing:
        raise RuntimeError(f"Missing Foundry application config: {', '.join(missing)}")

    response = requests.put(
        _agent_application_url(config),
        headers=_management_headers(),
        data=json.dumps(payload),
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"Foundry application PUT failed ({response.status_code}): {response.text}")
    if response.text:
        return response.json()
    return {}


def list_agent_application_agents() -> list[dict]:
    """List agent references exposed by the configured Agent Application."""
    config = _resolve_foundry_config()
    missing = _missing_management_config(config)
    missing = [item for item in missing if item != "FOUNDRY_AGENT_DEPLOYMENT_NAME"]
    if missing:
        raise RuntimeError(f"Missing Foundry application config: {', '.join(missing)}")

    response = requests.post(
        _agent_application_list_agents_url(config),
        headers=_management_headers(),
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Foundry application listAgents failed ({response.status_code}): {response.text}")
    payload = response.json()
    return payload.get("value", [])


def list_agents() -> list[AgentInfo]:
    """Mevcut agent'lari listele. Foundry + local deploy kayitlari."""
    # 1. Foundry Agent Application is the source of truth when available.
    try:
        foundry_agents = _list_foundry_application_agent_infos()
        if foundry_agents:
            return foundry_agents
    except Exception:
        pass

    agents: list[AgentInfo] = []

    # 2. Project-level Foundry fallback.
    client = _get_foundry_client()
    if client:
        try:
            foundry_agents = client.agents.list_agents()
            for a in foundry_agents:
                agents.append(_agent_info_from_foundry_agent(a))
        except Exception:
            pass

    # 3. Local deploy kayitlarindan cek (mock dahil)
    for path in AGENT_DIR.glob("*_deployed*.json"):
        try:
            data = _read_json_file(path)
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

    # 4. Local spec + definition dosyalarindan henuz deploy edilmemisleri de ekle
    for path in AGENT_DIR.glob("*_definition.json"):
        try:
            data = _read_json_file(path)
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
            data = _read_json_file(path)
            spec_id = data.get("spec_id", "")
            if (
                data.get("foundry_agent_id") == agent_id
                or spec_id == agent_id
                or f"draft_{spec_id}" == agent_id
            ):
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


def _metadata_as_strings(metadata: dict) -> dict[str, str]:
    data: dict[str, str] = {}
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        text = str(value)
        data[str(key)[:64]] = text[:512]
        if len(data) >= 16:
            break
    return data


def _read_json_file(path: Path) -> dict:
    for encoding in ("utf-8", "utf-8-sig", "cp1254", "cp1252"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _agent_info_from_foundry_agent(agent, *, fallback_id: str = "", fallback_name: str = "") -> AgentInfo:
    definition = _agent_attr(agent, "definition", None)
    model = (
        _agent_attr(agent, "model", "")
        or _agent_attr(definition, "model", "")
        or FOUNDRY_AGENT_MODEL
        or ""
    )
    instructions = (
        _agent_attr(agent, "instructions", "")
        or _agent_attr(definition, "instructions", "")
        or ""
    )
    tools = (
        _agent_attr(agent, "tools", None)
        or _agent_attr(definition, "tools", None)
        or []
    )
    metadata = _agent_attr(agent, "metadata", {}) or {}
    return AgentInfo(
        id=_agent_attr(agent, "id", None) or fallback_id,
        name=_agent_attr(agent, "name", None) or fallback_name or "Unnamed",
        model=model,
        instructions=instructions,
        tools=tools,
        metadata=dict(metadata) if isinstance(metadata, dict) else {},
        source="foundry",
    )


def _deployment_refs_by_name() -> dict[str, dict]:
    try:
        refs = get_agent_deployment().get("properties", {}).get("agents", []) or []
    except Exception:
        return {}
    return {
        str(ref.get("agentName")): ref
        for ref in refs
        if ref.get("agentName")
    }


def _list_foundry_application_agent_infos() -> list[AgentInfo]:
    """List only agents attached to the configured Foundry application."""
    application = get_agent_application()
    app_refs = application.get("properties", {}).get("agents", []) or []
    deployment_refs = _deployment_refs_by_name()
    agents: list[AgentInfo] = []
    seen_names: set[str] = set()

    for app_ref in app_refs:
        name = _agent_name_from_reference(app_ref)
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        dep_ref = deployment_refs.get(name, {})
        fallback_id = str(dep_ref.get("agentId") or app_ref.get("agentId") or name)
        version = str(dep_ref.get("agentVersion") or "")
        info = AgentInfo(
            id=fallback_id,
            name=name,
            model=FOUNDRY_AGENT_MODEL or "",
            metadata={},
            source="foundry",
        )

        if version:
            info.metadata = {**info.metadata, "agent_version": version}
            if not info.id or info.id.startswith("azureml://"):
                info.id = f"{name}:{version}"
        agents.append(info)

    return agents


def _normalize_foundry_agent_name(name: str, fallback_prefix: str = "Agent") -> str:
    """Keep generated names compatible with Foundry agent-name constraints."""
    transliteration = str.maketrans({
        "ç": "c",
        "Ç": "C",
        "ğ": "g",
        "Ğ": "G",
        "ı": "i",
        "I": "I",
        "İ": "I",
        "ö": "o",
        "Ö": "O",
        "ş": "s",
        "Ş": "S",
        "ü": "u",
        "Ü": "U",
    })
    normalized = (name or "").translate(transliteration)
    normalized = re.sub(r"[^A-Za-z0-9-]+", "-", normalized).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    if not normalized:
        normalized = f"{fallback_prefix}-{uuid.uuid4().hex[:8]}"
    normalized = normalized[:63].strip("-")
    if not normalized:
        normalized = f"{fallback_prefix}-{uuid.uuid4().hex[:8]}"
    return normalized


def _workflow_agent_name() -> str:
    return _normalize_foundry_agent_name(
        FOUNDRY_WORKFLOW_AGENT_NAME
        or f"{FOUNDRY_APPLICATION_NAME or FOUNDRY_AGENT_DEPLOYMENT_NAME or 'Agent-Factory'}-Workflow",
        fallback_prefix="Workflow",
    )


def _excluded_workflow_names() -> set[str]:
    return {
        name for name in {
            FOUNDRY_APPLICATION_NAME,
            FOUNDRY_AGENT_DEPLOYMENT_NAME,
            _workflow_agent_name(),
        }
        if name
    }


def _agent_attr(agent, name: str, default=None):
    if isinstance(agent, dict):
        return agent.get(name, default)
    return getattr(agent, name, default)


def _list_project_agents_raw() -> list:
    client = _get_foundry_client()
    if not client:
        return []
    try:
        return list(client.agents.list_agents())
    except Exception:
        return []


def _find_project_agent_by_name(name: str):
    client = _get_foundry_client()
    if not client:
        return None
    try:
        versions = list(client.agents.list_versions(name, limit=1, order="desc"))
        if versions:
            return versions[0]
    except Exception:
        pass
    return None


def _tool_types(tools: list[dict]) -> set[str]:
    types = set()
    for tool in tools or []:
        if isinstance(tool, dict) and tool.get("type"):
            types.add(str(tool["type"]))
    return types


def _wants_standalone(definition: dict) -> bool:
    text = " ".join([
        definition.get("name", ""),
        definition.get("instructions", ""),
        json.dumps(definition.get("metadata", {}), ensure_ascii=False),
    ]).lower()
    keywords = ("standalone", "bagimsiz", "bağımsız", "tek basina", "tek başına")
    return any(keyword in text for keyword in keywords)


def _select_parent_agent(definition: dict) -> AgentInfo | None:
    """Pick the most relevant existing agent for ecosystem metadata."""
    if _wants_standalone(definition):
        return None

    excluded_names = _excluded_workflow_names() | {"Synthesis-Agent"}
    candidates = [
        agent for agent in list_agents()
        if not agent.id.startswith("draft_") and agent.name not in excluded_names
    ]
    if not candidates:
        supervisor = _find_project_agent_by_name("Supervisor-Agent")
        if supervisor:
            return AgentInfo(
                id=_agent_attr(supervisor, "id", ""),
                name=_agent_attr(supervisor, "name", "Supervisor-Agent"),
                model=FOUNDRY_AGENT_MODEL or "",
                metadata=_agent_attr(supervisor, "metadata", {}) or {},
            )
        return None

    definition_text = f"{definition.get('name', '')} {definition.get('instructions', '')}".lower()
    new_tools = _tool_types(definition.get("tools", []))

    best_agent = None
    best_score = 0
    for agent in candidates:
        score = 0
        agent_text = f"{agent.name} {agent.instructions}".lower()
        shared_words = set(definition_text.split()) & set(agent_text.split())
        score += min(len(shared_words), 5)
        score += 3 * len(new_tools & _tool_types(agent.tools))

        if score > best_score:
            best_score = score
            best_agent = agent

    if best_score > 0:
        return best_agent

    for agent in candidates:
        if agent.name == "Supervisor-Agent":
            return agent

    return None


def _apply_ecosystem_metadata(definition: dict) -> dict:
    """Annotate the generated agent as standalone or attached to a parent."""
    updated = dict(definition)
    metadata = dict(updated.get("metadata", {}))
    parent = _select_parent_agent(updated)

    if parent:
        metadata["ecosystem_mode"] = "attached"
        metadata["parent_agent_id"] = parent.id
        metadata["parent_agent_name"] = parent.name
    else:
        metadata["ecosystem_mode"] = "standalone"

    updated["metadata"] = metadata
    return updated


def _versioned_agent_reference(agent, definition: dict) -> dict:
    metadata = definition.get("metadata", {})
    version = (
        getattr(agent, "version", None)
        or getattr(agent, "agent_version", None)
        or metadata.get("agent_version")
        or metadata.get("version")
        or "1.0.0"
    )
    return {
        "agentId": getattr(agent, "id", "") or "",
        "agentName": getattr(agent, "name", None) or definition.get("name", ""),
        "agentVersion": str(version),
    }


def _default_protocols() -> list[dict]:
    return [{"protocol": "Responses", "version": "1.0"}]


def _writable_deployment_properties(properties: dict) -> dict:
    """Keep only fields accepted by Agent Deployment create/update."""
    allowed = {
        "description",
        "tags",
        "displayName",
        "protocols",
        "agents",
        "deploymentType",
        "state",
    }
    return {key: value for key, value in (properties or {}).items() if key in allowed}


def _agent_factory_tags(existing: dict | None = None) -> dict:
    data = dict(existing or {})
    data["agentFactoryEnabled"] = "true"
    data["agentFactorySchemaVersion"] = "1"
    data["agentFactoryManagedBy"] = "agent-factory"
    data["agentFactoryIntegrationMode"] = "managed-agent-deployment"
    data["agentFactoryUpdatedAt"] = datetime.now(timezone.utc).isoformat()
    data["agentFactoryNewAgentBehavior"] = "attach-or-standalone"
    return data


def sync_agent_factory_deployment() -> dict:
    """Mark the configured Foundry deployment as managed by this Agent Factory."""
    deployment = get_agent_deployment()
    existing = deployment.get("properties") or {}
    properties = _writable_deployment_properties(existing)

    properties["displayName"] = properties.get("displayName") or FOUNDRY_APPLICATION_NAME or "Agent Factory"
    properties["description"] = (
        "Agent Factory managed deployment. New generated agents can be attached "
        "to this application or kept standalone based on the builder decision."
    )
    properties["deploymentType"] = properties.get("deploymentType") or FOUNDRY_AGENT_DEPLOYMENT_TYPE or "Managed"
    properties["protocols"] = properties.get("protocols") or _default_protocols()
    properties["agents"] = properties.get("agents") or []
    properties["tags"] = _agent_factory_tags(properties.get("tags"))

    raw = update_agent_deployment({"properties": properties})
    return raw


def _writable_application_properties(properties: dict) -> dict:
    allowed = {
        "agents",
        "description",
        "displayName",
        "isEnabled",
        "tags",
        "trafficRoutingPolicy",
    }
    return {key: value for key, value in (properties or {}).items() if key in allowed}


def sync_agent_factory_application() -> dict:
    """Mark the configured Foundry application as managed by this Agent Factory."""
    application = get_agent_application()
    existing = application.get("properties") or {}
    properties = _writable_application_properties(existing)
    properties["displayName"] = properties.get("displayName") or FOUNDRY_APPLICATION_NAME or "Agent Factory"
    properties["description"] = (
        "Agent Factory application. Generated agents are created from the local builder, "
        "then attached to the configured Foundry deployment when approved."
    )
    properties["isEnabled"] = existing.get("isEnabled", True)
    properties["tags"] = _agent_factory_tags(properties.get("tags"))

    return update_agent_application({"properties": properties})


def sync_agent_factory_foundry() -> dict:
    """Sync both application metadata and deployment readiness."""
    application = sync_agent_factory_application()
    deployment = sync_agent_factory_deployment()
    return {
        "application": application,
        "deployment": deployment,
    }


def _try_attach_agent_to_deployment(agent, definition: dict) -> dict:
    """Attach a created Foundry agent to the configured Agent Deployment when possible."""
    config = _resolve_foundry_config()
    missing = _missing_management_config(config)
    if missing:
        return {
            "updated": False,
            "skipped": True,
            "reason": f"Missing Foundry management config: {', '.join(missing)}",
        }

    try:
        deployment = get_agent_deployment()
    except Exception as exc:
        # 404 can mean the deployment does not exist yet; create a managed deployment.
        if "404" not in str(exc):
            return {"updated": False, "error": str(exc)}
        deployment = {}

    properties = _writable_deployment_properties(dict(deployment.get("properties", {})))
    deployment_type = properties.get("deploymentType") or FOUNDRY_AGENT_DEPLOYMENT_TYPE or "Managed"

    if str(deployment_type).lower() == "hosted" and "agents" not in properties:
        return {
            "updated": False,
            "skipped": True,
            "reason": "Hosted Agent Deployment does not expose an agents array in the management API.",
            "deploymentType": deployment_type,
        }

    ref = _versioned_agent_reference(agent, definition)
    agents = list(properties.get("agents", []))
    agents = [
        existing for existing in agents
        if existing.get("agentId") != ref["agentId"] and existing.get("agentName") != ref["agentName"]
    ]
    agents.append(ref)

    properties["agents"] = agents
    properties["deploymentType"] = deployment_type
    properties.setdefault("displayName", config.application_name or "Agent Factory Deployment")
    properties.setdefault("protocols", _default_protocols())
    properties["tags"] = _agent_factory_tags(properties.get("tags"))

    payload = {"properties": properties}
    raw = update_agent_deployment(payload)
    return {"updated": True, "raw": raw, "agentReference": ref}


def _try_attach_agent_to_application(agent, definition: dict) -> dict:
    """Attach a created Foundry agent to the configured Agent Application."""
    config = _resolve_foundry_config()
    missing = _missing_management_config(config)
    missing = [item for item in missing if item != "FOUNDRY_AGENT_DEPLOYMENT_NAME"]
    if missing:
        return {
            "updated": False,
            "skipped": True,
            "reason": f"Missing Foundry application config: {', '.join(missing)}",
        }

    try:
        application = get_agent_application()
    except Exception as exc:
        return {"updated": False, "error": str(exc)}

    properties = _writable_application_properties(dict(application.get("properties", {})))
    agent_id = getattr(agent, "id", "") or ""
    agent_name = getattr(agent, "name", None) or definition.get("name", "")
    ref = {"agentId": agent_id, "agentName": agent_name}

    agents = list(properties.get("agents", []))
    agents = [
        existing for existing in agents
        if existing.get("agentId") != agent_id and existing.get("agentName") != agent_name
    ]
    agents.append(ref)

    properties["agents"] = agents
    properties.setdefault("displayName", config.application_name or "Agent Factory")
    properties["isEnabled"] = properties.get("isEnabled", True)
    properties["tags"] = _agent_factory_tags(properties.get("tags"))

    raw = update_agent_application({"properties": properties})
    return {"updated": True, "raw": raw, "agentReference": ref}


def _seed_agent_metadata(seed: dict) -> dict[str, str]:
    metadata = {
        "generated_by": "agent-factory-seed",
        "ecosystem": "fnss-corporate-agents",
        "purpose": seed.get("purpose", ""),
        "legacy_name": seed.get("legacy_name", seed.get("name", "")),
        "instruction_hash": hashlib.sha256(seed["instructions"].encode("utf-8")).hexdigest()[:16],
    }
    metadata.update(seed.get("metadata", {}))
    if seed.get("tools"):
        metadata["logical_tools"] = ",".join(seed["tools"])
    return _metadata_as_strings(metadata)


def _create_or_get_seed_agent(seed: dict):
    existing = _find_project_agent_by_name(seed["name"])
    if existing:
        metadata = _agent_attr(existing, "metadata", {}) or {}
        current_hash = str(metadata.get("instruction_hash", ""))
        next_hash = hashlib.sha256(seed["instructions"].encode("utf-8")).hexdigest()[:16]
        if current_hash == next_hash:
            return existing, False

    client = _get_foundry_client()
    if not client:
        raise RuntimeError("Foundry project client is not available. Check Azure auth and FOUNDRY_PROJECT_ENDPOINT.")

    from azure.ai.projects.models import PromptAgentDefinition

    definition = PromptAgentDefinition(
        kind="prompt",
        model=FOUNDRY_AGENT_MODEL or "deepseek-V3.1",
        instructions=seed["instructions"],
    )
    agent = client.agents.create_version(
        agent_name=seed["name"],
        definition=definition,
        metadata=_seed_agent_metadata(seed),
        description=seed.get("purpose", ""),
    )
    return agent, True


def _application_ref_for_agent(agent, seed: dict) -> dict:
    return {
        "agentId": _agent_attr(agent, "id", "") or "",
        "agentName": _agent_attr(agent, "name", None) or seed["name"],
    }


def _deployment_ref_for_agent(agent, seed: dict) -> dict:
    metadata = seed.get("metadata", {})
    return {
        "agentId": _agent_attr(agent, "id", "") or "",
        "agentName": _agent_attr(agent, "name", None) or seed["name"],
        "agentVersion": str(
            _agent_attr(agent, "version", None)
            or _agent_attr(agent, "agent_version", None)
            or metadata.get("agent_version")
            or "1.0.0"
        ),
    }


def _merge_application_agent_refs(existing: list[dict], refs: list[dict]) -> list[dict]:
    merged = list(existing or [])
    for ref in refs:
        merged = [
            item for item in merged
            if item.get("agentId") != ref.get("agentId") and item.get("agentName") != ref.get("agentName")
        ]
        merged.append(ref)
    return merged


def _merge_deployment_agent_refs(existing: list[dict], refs: list[dict]) -> list[dict]:
    merged = list(existing or [])
    for ref in refs:
        merged = [
            item for item in merged
            if item.get("agentId") != ref.get("agentId") and item.get("agentName") != ref.get("agentName")
        ]
        merged.append(ref)
    return merged


def _agent_name_from_reference(ref: dict) -> str:
    return str(ref.get("agentName") or ref.get("name") or "").strip()


def _agent_version_from_project(name: str) -> str:
    agent = _find_project_agent_by_name(name)
    return str(
        _agent_attr(agent, "version", None)
        or _agent_attr(agent, "agent_version", None)
        or "1"
    )


def _project_agent_metadata(name: str) -> dict:
    agent = _find_project_agent_by_name(name)
    metadata = _agent_attr(agent, "metadata", {}) or {}
    return dict(metadata) if isinstance(metadata, dict) else {}


def _seed_order() -> list[str]:
    return [seed["name"] for seed in SEED_AGENT_DEFINITIONS]


def _seed_metadata_by_name() -> dict[str, dict]:
    return {seed["name"]: dict(seed.get("metadata", {})) for seed in SEED_AGENT_DEFINITIONS}


def _workflow_action_id(agent_name: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", agent_name.lower()).strip("_") or "agent"
    action_id = base[:48].strip("_") or "agent"
    candidate = action_id
    index = 2
    while candidate in used:
        suffix = f"_{index}"
        candidate = f"{action_id[:48 - len(suffix)]}{suffix}".strip("_")
        index += 1
    used.add(candidate)
    return candidate


def _seed_label_by_name() -> dict[str, str]:
    return {seed["name"]: seed.get("label", seed["name"]) for seed in SEED_AGENT_DEFINITIONS}


def _route_keywords(agent_name: str) -> list[str]:
    fixed = {
        "HR-Agent": ["HR-AGENT", "HR", "IK", "INSAN KAYNAKLARI", "IZIN", "MAAS", "BORDRO"],
        "IT-Agent": ["IT-AGENT", "IT", "TEKNIK", "ARIZA", "TICKET", "EKIPMAN", "PARCA"],
        "Finance-Agent": ["FINANCE-AGENT", "FINANS", "AVANS", "MASRAF", "ODEME", "HARCAMA"],
        "Math-Agent": ["MATH-AGENT", "MATEMATIK", "HESAP", "ISTATISTIK", "DONUSUM"],
        "General-Agent": ["GENERAL-AGENT", "GENEL", "YEMEK", "SERVIS", "OFIS"],
        "Chat-Agent": ["CHAT-AGENT", "SOHBET", "SELAM", "YARDIM", "BELIRSIZ"],
    }
    if agent_name in fixed:
        return fixed[agent_name]
    words = re.split(r"[^A-Za-z0-9]+", agent_name.upper())
    return [agent_name.upper(), *[word for word in words if len(word) > 2]]


def _route_condition(agent_name: str) -> str:
    target = "Upper(Text(Local.SupervisorResult))"
    checks = [
        f'IsMatch({target}, "{re.escape(keyword)}")'
        for keyword in _route_keywords(agent_name)[:8]
    ]
    return f"=Or({', '.join(checks)})" if checks else "=false"


def _display_name_for_node(node: dict) -> str:
    labels = _seed_label_by_name()
    label = labels.get(node["agent_name"], node["agent_name"])
    role = str(node.get("role") or "agent")
    parent = node.get("parent_agent_name")
    if parent:
        return f"{node['agent_name']} under {parent} - {label} ({role})"
    return f"{node['agent_name']} - {label} ({role})"


def _application_agent_names() -> list[str]:
    try:
        application = get_agent_application()
        refs = application.get("properties", {}).get("agents", []) or []
        names = [_agent_name_from_reference(ref) for ref in refs]
        names = [name for name in names if name]
    except Exception:
        names = []

    if not names:
        names = _seed_order()

    excluded = _excluded_workflow_names()
    ordered: list[str] = []
    for name in names + _seed_order():
        if name in excluded or not name:
            continue
        if name not in ordered:
            ordered.append(name)
    return ordered


def build_workflow_topology() -> dict:
    """Build a tree-shaped workflow topology from the current Foundry application agents."""
    names = _application_agent_names()
    if not names:
        raise RuntimeError("No application agents found to build a workflow.")

    seed_order = _seed_order()
    seed_metadata = _seed_metadata_by_name()
    root_name = "Supervisor-Agent" if "Supervisor-Agent" in names else names[0]
    synthesis_name = "Synthesis-Agent" if "Synthesis-Agent" in names else ""

    ordered_names = sorted(
        names,
        key=lambda item: (
            0 if item == root_name else 2 if item == synthesis_name else 1,
            seed_order.index(item) if item in seed_order else len(seed_order),
            item.lower(),
        ),
    )

    used_action_ids: set[str] = set()
    name_to_action_id = {
        name: _workflow_action_id(name, used_action_ids)
        for name in ordered_names
    }

    nodes = []
    edges = []
    for name in ordered_names:
        metadata = dict(seed_metadata.get(name, {}))
        metadata.update(_project_agent_metadata(name))
        ecosystem_mode = str(metadata.get("ecosystem_mode", "")).lower()
        explicit_parent = (
            metadata.get("parent_agent_name")
            or metadata.get("parent_agent")
            or metadata.get("parent")
        )
        parent_name = str(explicit_parent).strip() if explicit_parent else ""

        if name == root_name or ecosystem_mode == "standalone":
            parent_name = ""
        elif parent_name not in names:
            parent_name = root_name

        node = {
            "id": name_to_action_id[name],
            "agent_name": name,
            "agent_version": _agent_version_from_project(name),
            "parent_id": name_to_action_id.get(parent_name, ""),
            "parent_agent_name": parent_name,
            "role": metadata.get("role", "agent"),
            "ecosystem_mode": ecosystem_mode or ("root" if name == root_name else "attached"),
        }
        nodes.append(node)
        if parent_name:
            edges.append({
                "source": parent_name,
                "target": name,
                "source_id": name_to_action_id[parent_name],
                "target_id": name_to_action_id[name],
            })

    if synthesis_name:
        for name in ordered_names:
            if name not in {root_name, synthesis_name}:
                edges.append({
                    "source": name,
                    "target": synthesis_name,
                    "source_id": name_to_action_id[name],
                    "target_id": name_to_action_id[synthesis_name],
                    "semantic": "synthesizes_output",
                })

    return {
        "name": _workflow_agent_name(),
        "root_agent": root_name,
        "synthesis_agent": synthesis_name,
        "nodes": nodes,
        "edges": edges,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _yaml_string(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)


def render_workflow_yaml(topology: dict) -> str:
    """Render Foundry workflow CSDL YAML accepted by WorkflowAgentDefinition."""
    root_node = next((node for node in topology["nodes"] if node["agent_name"] == topology["root_agent"]), None)
    synthesis_node = next(
        (node for node in topology["nodes"] if node["agent_name"] == topology.get("synthesis_agent")),
        None,
    )
    specialist_nodes = [
        node for node in topology["nodes"]
        if node is not root_node and node is not synthesis_node
    ]

    lines = [
        "kind: Workflow",
        "trigger:",
        "  kind: OnConversationStart",
        f"  id: {_yaml_string(_workflow_action_id(topology['name'], set()))}",
        "  actions:",
    ]

    if root_node:
        lines.extend([
            "    - kind: InvokeAzureAgent",
            f"      id: {_yaml_string(root_node['id'])}",
            f"      displayName: {_yaml_string(_display_name_for_node(root_node))}",
            "      conversationId: =System.ConversationId",
            "      agent:",
            f"        name: {_yaml_string(root_node['agent_name'])}",
            "      input:",
            "        arguments:",
            "          workflow_role: supervisor",
            "          expected_output: Return the selected child agent names and a short routing reason.",
            "      output:",
            "        responseObject: Local.SupervisorResult",
            "        messages: Local.SupervisorMessages",
            "        autoSend: false",
        ])

    for node in specialist_nodes:
        lines.extend([
            "    - kind: InvokeAzureAgent",
            f"      id: {_yaml_string(node['id'])}",
            f"      displayName: {_yaml_string(_display_name_for_node(node))}",
            "      conversationId: =System.ConversationId",
            "      agent:",
            f"        name: {_yaml_string(node['agent_name'])}",
            "      input:",
            "        arguments:",
            "          supervisor_result: =Text(Local.SupervisorResult)",
            f"          parent_agent: {_yaml_string(node.get('parent_agent_name') or topology.get('root_agent') or '')}",
            f"          route_condition: {_yaml_string(_route_condition(node['agent_name']))}",
            "          routing_instruction: Only handle this request when supervisor_result selects this agent; otherwise return NOT_APPLICABLE briefly.",
            "      output:",
            f"        responseObject: Local.{node['id']}Result",
            f"        messages: Local.{node['id']}Messages",
            "        autoSend: false",
        ])

    if synthesis_node:
        lines.extend([
            "    - kind: InvokeAzureAgent",
            f"      id: {_yaml_string(synthesis_node['id'])}",
            f"      displayName: {_yaml_string(_display_name_for_node(synthesis_node))}",
            "      conversationId: =System.ConversationId",
            "      agent:",
            f"        name: {_yaml_string(synthesis_node['agent_name'])}",
            "      input:",
            "        arguments:",
            "          supervisor_result: =Text(Local.SupervisorResult)",
            "          synthesis_instruction: Merge applicable child-agent outputs and ignore NOT_APPLICABLE outputs.",
            "      output:",
            "        responseObject: Local.SynthesisResult",
            "        messages: Local.SynthesisMessages",
            "        autoSend: true",
        ])
    return "\n".join(lines) + "\n"


def _write_workflow_artifacts(topology: dict, workflow_yaml: str) -> dict[str, str]:
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", topology["name"]).strip("_") or "workflow"
    json_path = WORKFLOW_TOPOLOGY_DIR / f"{safe_name}_topology.json"
    yaml_path = WORKFLOW_TOPOLOGY_DIR / f"{safe_name}.yaml"
    json_path.write_text(json.dumps(topology, indent=2, ensure_ascii=False), encoding="utf-8")
    yaml_path.write_text(workflow_yaml, encoding="utf-8")
    return {"topology_json": str(json_path), "workflow_yaml": str(yaml_path)}


def sync_workflow_agent_to_foundry() -> dict:
    """Create/update the Foundry workflow agent and attach it to the FNSS app/deployment."""
    client = _get_foundry_client()
    if not client:
        raise RuntimeError("Foundry project client is not available. Check Azure auth and FOUNDRY_PROJECT_ENDPOINT.")

    from azure.ai.projects.models import WorkflowAgentDefinition

    topology = build_workflow_topology()
    workflow_yaml = render_workflow_yaml(topology)
    artifacts = _write_workflow_artifacts(topology, workflow_yaml)

    agent = client.agents.create_version(
        agent_name=topology["name"],
        definition=WorkflowAgentDefinition(workflow=workflow_yaml),
        metadata=_metadata_as_strings({
            "generated_by": "agent-factory",
            "workflow_role": "topology",
            "schema_version": "1",
            "node_count": len(topology["nodes"]),
            "root_agent": topology.get("root_agent", ""),
            "synthesis_agent": topology.get("synthesis_agent", ""),
        }),
        description="FNSS Agent Factory workflow graph",
    )

    definition = {
        "name": topology["name"],
        "metadata": {"agent_version": _agent_attr(agent, "version", None) or "1"},
    }
    application_update = _try_attach_agent_to_application(agent, definition)
    deployment_update = _try_attach_agent_to_deployment(agent, definition)

    return {
        "workflow_agent": {
            "id": _agent_attr(agent, "id", ""),
            "name": _agent_attr(agent, "name", topology["name"]),
            "version": _agent_attr(agent, "version", None),
        },
        "topology": topology,
        "artifacts": artifacts,
        "application_update": application_update,
        "deployment_update": deployment_update,
    }


def migrate_seed_agent_system_to_foundry() -> dict:
    """Create the bundled corporate agents and attach them to FNSS."""
    created = []
    reused = []
    application_refs = []
    deployment_refs = []

    for seed in SEED_AGENT_DEFINITIONS:
        agent, was_created = _create_or_get_seed_agent(seed)
        item = {
            "name": _agent_attr(agent, "name", seed["name"]),
            "id": _agent_attr(agent, "id", ""),
        }
        if was_created:
            created.append(item)
        else:
            reused.append(item)
        application_refs.append(_application_ref_for_agent(agent, seed))
        deployment_refs.append(_deployment_ref_for_agent(agent, seed))

    application = get_agent_application()
    app_properties = _writable_application_properties(application.get("properties") or {})
    app_properties["agents"] = _merge_application_agent_refs(app_properties.get("agents", []), application_refs)
    app_properties.setdefault("displayName", FOUNDRY_APPLICATION_NAME or "FNSS")
    app_properties["isEnabled"] = app_properties.get("isEnabled", True)
    app_properties["tags"] = _agent_factory_tags(app_properties.get("tags"))
    updated_application = update_agent_application({"properties": app_properties})

    deployment = get_agent_deployment()
    dep_properties = _writable_deployment_properties(deployment.get("properties") or {})
    dep_properties["agents"] = _merge_deployment_agent_refs(dep_properties.get("agents", []), deployment_refs)
    dep_properties["deploymentType"] = dep_properties.get("deploymentType") or FOUNDRY_AGENT_DEPLOYMENT_TYPE or "Managed"
    dep_properties.setdefault("displayName", FOUNDRY_APPLICATION_NAME or "FNSS")
    dep_properties.setdefault("protocols", _default_protocols())
    dep_properties["tags"] = _agent_factory_tags(dep_properties.get("tags"))
    updated_deployment = update_agent_deployment({"properties": dep_properties})
    workflow = sync_workflow_agent_to_foundry()

    return {
        "created": created,
        "reused": reused,
        "application": updated_application,
        "deployment": updated_deployment,
        "workflow": workflow,
    }


def deploy_prompt_agent(definition: dict) -> DeploymentResult:
    """Foundry'ye deploy et. SDK yoksa mock sonuc don."""
    definition = _apply_ecosystem_metadata(definition)
    requested_name = definition.get("name", "")
    foundry_name = _normalize_foundry_agent_name(requested_name)
    if foundry_name != requested_name:
        metadata = dict(definition.get("metadata", {}))
        metadata["requested_name"] = requested_name
        definition["metadata"] = metadata
        definition["name"] = foundry_name

    client = _get_foundry_client()
    if not client:
        return _mock_deploy(definition)

    try:
        from azure.ai.projects.models import PromptAgentDefinition

        metadata = dict(definition.get("metadata", {}))
        if definition.get("tools"):
            metadata["logical_tools"] = ",".join(
                str(tool.get("name") or tool.get("type") or "tool")
                for tool in definition.get("tools", [])
                if isinstance(tool, dict)
            )

        prompt_definition = PromptAgentDefinition(
            model=definition["model"],
            instructions=definition["instructions"],
        )
        agent = client.agents.create_version(
            agent_name=definition["name"],
            definition=prompt_definition,
            metadata=_metadata_as_strings(metadata),
            description=(definition.get("purpose") or definition.get("instructions", ""))[:512],
        )

        application_update = _try_attach_agent_to_application(agent, definition)
        deployment_update = _try_attach_agent_to_deployment(agent, definition)
        workflow_update = None
        workflow_update_error = None
        try:
            workflow_update = sync_workflow_agent_to_foundry()
        except Exception as exc:
            workflow_update_error = str(exc)

        result_data = {
            "foundry_agent_id": agent.id,
            "name": getattr(agent, "name", definition["name"]),
            "model": getattr(agent, "model", definition["model"]),
            "created_at": str(getattr(agent, "created_at", "")),
            "metadata": definition.get("metadata", {}),
            "application_update": application_update,
            "deployment_update": deployment_update,
            "workflow_update": workflow_update,
            "workflow_update_error": workflow_update_error,
        }

        log_path = AGENT_DIR / f"{definition['spec_id']}_deployed.json"
        log_path.write_text(json.dumps(result_data, indent=2, ensure_ascii=False), encoding="utf-8")

        return DeploymentResult(
            success=True,
            foundry_agent_id=agent.id,
            application_updated=bool(application_update.get("updated")) and bool(deployment_update.get("updated")),
            application_update_error=(
                application_update.get("error")
                or application_update.get("reason")
                or deployment_update.get("error")
                or deployment_update.get("reason")
                or workflow_update_error
            ),
            application_update_raw={
                "application": application_update,
                "deployment": deployment_update,
                "workflow": workflow_update,
            },
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
    log_path.write_text(json.dumps(result_data, indent=2, ensure_ascii=False), encoding="utf-8")

    return DeploymentResult(
        success=True,
        foundry_agent_id=mock_id,
        mock=True,
        raw=result_data,
    )
