from typing import Any

from pydantic import BaseModel, Field, field_validator


class GenerateSystemRequest(BaseModel):
    """Natural-language brief for a system to diagram."""

    prompt: str = Field(
        ...,
        min_length=3,
        max_length=8_000,
        description="e.g. 'Design Uber backend'",
    )


class GenerateSystemResponse(BaseModel):
    """Graph JSON aligned with canvas export (nodes + edges)."""

    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
