from typing import Any

from pydantic import BaseModel, Field, field_validator


class EvaluateRequest(BaseModel):
    nodes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Graph nodes (arbitrary JSON objects).",
    )
    edges: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Graph edges (arbitrary JSON objects).",
    )


class EvaluateResponse(BaseModel):
    score: int = Field(..., ge=0, le=100)
    strengths: list[str]
    weaknesses: list[str]
    questions: list[str]


class EvaluationLLMResult(BaseModel):
    """Expected shape from the LLM (validated before mapping to EvaluateResponse)."""

    score: int = Field(..., ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)

    @field_validator("score", mode="before")
    @classmethod
    def coerce_score(cls, value: Any) -> int:
        x = int(round(float(value)))
        return max(0, min(100, x))

    @field_validator("strengths", "weaknesses", "questions", mode="before")
    @classmethod
    def coerce_str_lists(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return [str(value).strip()] if str(value).strip() else []
        out: list[str] = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out
