from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class AgentType(str, Enum):
    PROMPT = "prompt"
    WORKFLOW = "workflow"
    HOSTED = "hosted"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolSpec(BaseModel):
    """Agent'in kullanacagi bir arac."""
    name: str = Field(..., description="Kisa insan okunur isim")
    type: Literal[
        "file_reader",
        "code_interpreter",
        "file_search",
        "api_call",
        "db_query",
    ]
    description: str
    config: dict = Field(default_factory=dict)


class AgentSpec(BaseModel):
    """Bir agent'in tam tanimi."""
    id: str = Field(default_factory=lambda: f"spec_{uuid.uuid4().hex[:8]}")
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Temel bilgi
    name: str = Field(..., description="Agent'in kisa ismi, orn: 'Excel Error Analyzer'")
    purpose: str = Field(..., description="Ne is yapacak, 1-2 cumle")

    # Kullanici ve erisim
    user_audience: str = Field(..., description="Kim kullanacak: 'ops ekibi', 'finans', vs.")
    data_sources: list[str] = Field(default_factory=list, description="Erisecegi veri kaynaklari")
    tools: list[ToolSpec] = Field(default_factory=list)

    # Guvenlik ve risk
    risk_level: RiskLevel = RiskLevel.LOW
    approval_required: bool = False
    contains_pii: bool = False

    # Karmasiklik gostergeleri (architect bunlara bakacak)
    needs_supervisor: bool = False
    custom_state_required: bool = False
    decision_points: int = 0

    # Cikti
    suggested_type: AgentType | None = None

    def is_complete(self) -> bool:
        """Spec doldurumus kontrolu."""
        return bool(self.name and self.purpose and self.user_audience)
