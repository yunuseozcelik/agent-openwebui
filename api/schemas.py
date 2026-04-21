"""Pydantic request/response models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Analysis ──

class AnalyzeRequest(BaseModel):
    description: str


class AnalyzeResponse(BaseModel):
    name: str = ""
    purpose: str = ""
    inferred_tools: list[str] = []
    inferred_data_sources: list[str] = []
    suggested_capabilities: list[str] = []
    domain: str = "genel"
    complexity_hints: dict[str, Any] = {}
    inferred_parent: str = ""


# ── Build (finalize) ──

class BuildRequest(BaseModel):
    description: str
    name: str
    purpose: str
    audience: str
    tone: str = "friendly"
    output_format: str = "adaptive"
    scope: str = "strict_scope"
    pii: str = "false"
    approval: str = "false"
    example_scenario: str = ""
    inferred_tools: list[str] = []
    inferred_data_sources: list[str] = []
    suggested_capabilities: list[str] = []
    complexity_hints: dict[str, Any] = {}


class BuildResponse(BaseModel):
    spec_id: str
    spec: dict
    instructions: str
    pipeline: dict
    ready_for_approval: bool
    integrations: list[str] = []
    graph: dict | None = None
    warnings: list[str] = []


# ── Deploy ──

class DeployRequest(BaseModel):
    spec_id: str


class DeployResponse(BaseModel):
    success: bool
    foundry_agent_id: str | None = None
    name: str | None = None
    mock: bool = False
    error: str | None = None
    application_updated: bool = False
    application_update_error: str | None = None
    workflow_update: dict | None = None


# ── Chat ──

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    agent_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    content: str


# ── Templates ──

class TemplateDeployRequest(BaseModel):
    template_id: str
    overrides: dict[str, Any] = Field(default_factory=dict)


# ── Agent summary ──

class AgentSummary(BaseModel):
    id: str
    name: str
    model: str = ""
    instructions: str = ""
    tools: list[dict] = []
    metadata: dict = {}
    source: str = "local"
    status: str = "active"  # active | mock | draft


class AgentUpdateRequest(BaseModel):
    instructions: str | None = None
    name: str | None = None
    purpose: str | None = None


class AgentUpdateResponse(BaseModel):
    success: bool
    agent: AgentSummary | None = None
    error: str | None = None


class AgentDeleteResponse(BaseModel):
    success: bool
    error: str | None = None
