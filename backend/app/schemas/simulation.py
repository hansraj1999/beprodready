from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SimulateIncidentRequest(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)


Severity = Literal["low", "medium", "high", "critical"]


class SimulatedIncident(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    component: str = ""
    failure_mode: str = ""
    description: str = ""
    severity: Severity = "medium"

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v: Any) -> str:
        s = str(v).strip().lower()
        if s in ("low", "medium", "high", "critical"):
            return s
        return "medium"


class ImpactAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str = ""
    affected_components: list[str] = Field(default_factory=list)
    user_visible_effects: str = ""
    data_risk: str = ""

    @field_validator("affected_components", mode="before")
    @classmethod
    def coerce_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if not isinstance(v, list):
            s = str(v).strip()
            return [s] if s else []
        return [str(x).strip() for x in v if str(x).strip()]


class SimulateIncidentResponse(BaseModel):
    incident: SimulatedIncident
    impact: ImpactAnalysis
    suggested_fixes: list[str]

    @field_validator("suggested_fixes", mode="before")
    @classmethod
    def coerce_fixes(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if not isinstance(v, list):
            s = str(v).strip()
            return [s] if s else []
        return [str(x).strip() for x in v if str(x).strip()]


class LLMSimulationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    incident: SimulatedIncident
    impact: ImpactAnalysis
    suggested_fixes: list[str] = Field(default_factory=list)

    @field_validator("suggested_fixes", mode="before")
    @classmethod
    def coerce_fixes(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if not isinstance(v, list):
            s = str(v).strip()
            return [s] if s else []
        return [str(x).strip() for x in v if str(x).strip()]
