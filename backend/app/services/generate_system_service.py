from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import settings
from app.generate_system.prompts import SYSTEM_GENERATE_GRAPH, USER_GENERATE_TEMPLATE
from app.llm.openai_json import chat_completion_json
from app.schemas.generate_system import GenerateSystemResponse
from app.schemas.graph import GraphPayload

logger = logging.getLogger(__name__)

_ALLOWED_TYPES = frozenset({"api", "db", "cache", "queue"})


class GenerateSystemError(Exception):
    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        self.message = message or code
        super().__init__(self.message)


class _RawNode(BaseModel):
    model_config = {"extra": "ignore"}

    id: str = ""
    type: str = "api"
    label: str = ""
    position: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "label", mode="before")
    @classmethod
    def strip_str(cls, v: Any) -> str:
        return str(v).strip() if v is not None else ""

    @field_validator("type", mode="before")
    @classmethod
    def coerce_type(cls, v: Any) -> str:
        s = str(v).lower().strip()
        return s if s in _ALLOWED_TYPES else "api"


class _RawEdge(BaseModel):
    model_config = {"extra": "ignore"}

    id: str = ""
    source: str = ""
    target: str = ""
    label: str | None = None

    @field_validator("id", "source", "target", mode="before")
    @classmethod
    def strip_str(cls, v: Any) -> str:
        return str(v).strip() if v is not None else ""

    @field_validator("label", mode="before")
    @classmethod
    def opt_label(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None


class _LLMGraphShape(BaseModel):
    model_config = {"extra": "ignore"}

    nodes: list[_RawNode] = Field(default_factory=list)
    edges: list[_RawEdge] = Field(default_factory=list)


def _use_openai() -> bool:
    return (
        settings.EVALUATION_LLM_PROVIDER.strip().lower() == "openai"
        and bool(settings.OPENAI_API_KEY.strip())
    )


def _slug(s: str, max_len: int = 24) -> str:
    t = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return (t[:max_len] or "system") if t else "system"


def _stub_graph(prompt: str) -> GraphPayload:
    """Deterministic placeholder graph when OpenAI is not configured."""
    slug = _slug(prompt)
    nodes_spec: list[tuple[str, str, str, str, float, float]] = [
        ("n_gateway", "api", "API Gateway", "Ingress, auth, rate limits", 80.0, 120.0),
        ("n_core", "api", "Core Service", f"Main domain logic for: {prompt[:120]}", 320.0, 80.0),
        ("n_cache", "cache", "Redis", "Hot reads, sessions, idempotency keys", 320.0, 240.0),
        ("n_queue", "queue", "Event Bus", "Async jobs, notifications, analytics pipeline", 520.0, 160.0),
        ("n_db", "db", "Primary DB", "Transactional store, strong consistency where needed", 520.0, 320.0),
        ("n_search", "api", "Search / Geo", "Indexes, nearby drivers / listings (if applicable)", 720.0, 120.0),
    ]
    nodes: list[dict[str, Any]] = []
    for nid, kind, label, desc, x, y in nodes_spec:
        nodes.append(
            {
                "id": nid,
                "type": kind,
                "label": label,
                "position": {"x": x, "y": y},
                "data": {
                    "kind": kind,
                    "label": label,
                    "description": desc,
                },
            }
        )
    edges: list[dict[str, Any]] = [
        {"id": "e1", "source": "n_gateway", "target": "n_core", "label": "HTTPS"},
        {"id": "e2", "source": "n_core", "target": "n_cache", "label": "read/write"},
        {"id": "e3", "source": "n_core", "target": "n_queue", "label": "publish"},
        {"id": "e4", "source": "n_core", "target": "n_db", "label": "SQL"},
        {"id": "e5", "source": "n_queue", "target": "n_search", "label": "index"},
        {"id": "e6", "source": "n_queue", "target": "n_db", "label": "consume"},
    ]
    logger.info(
        "generate_system.stub",
        extra={"slug": slug, "prompt_len": len(prompt)},
    )
    return GraphPayload(nodes=nodes, edges=edges)


def _parse_position(pos: dict[str, Any], index: int) -> tuple[float, float]:
    try:
        x = float(pos.get("x", 0))
        y = float(pos.get("y", 0))
    except (TypeError, ValueError):
        x, y = 0.0, 0.0
    if x == 0 and y == 0:
        col = index % 4
        row = index // 4
        x = 80.0 + col * 200.0
        y = 80.0 + row * 140.0
    return x, y


def _normalize_and_build(nodes_in: list[_RawNode], edges_in: list[_RawEdge]) -> GraphPayload:
    seen_ids: set[str] = set()
    nodes: list[dict[str, Any]] = []

    for i, n in enumerate(nodes_in):
        nid = n.id or f"n_{i}"
        base = nid
        suffix = 0
        while nid in seen_ids:
            suffix += 1
            nid = f"{base}_{suffix}"
        seen_ids.add(nid)

        kind = n.type if n.type in _ALLOWED_TYPES else "api"
        label = n.label or kind.upper()
        x, y = _parse_position(n.position, i)
        data = dict(n.data) if isinstance(n.data, dict) else {}
        data.setdefault("kind", kind)
        data["label"] = str(data.get("label", label))[:200]
        if "description" in data and data["description"] is not None:
            data["description"] = str(data["description"])[:2000]
        else:
            data["description"] = ""

        nodes.append(
            {
                "id": nid,
                "type": kind,
                "label": label[:200],
                "position": {"x": x, "y": y},
                "data": data,
            }
        )

    id_set = {n["id"] for n in nodes}
    edges: list[dict[str, Any]] = []
    for i, e in enumerate(edges_in):
        if not e.source or not e.target or e.source not in id_set or e.target not in id_set:
            continue
        eid = e.id or f"e_{uuid.uuid4().hex[:10]}"
        edge_obj: dict[str, Any] = {
            "id": eid,
            "source": e.source,
            "target": e.target,
        }
        if e.label:
            edge_obj["label"] = e.label[:200]
        edges.append(edge_obj)

    if not nodes:
        raise GenerateSystemError("empty_graph", "Model returned no nodes")

    return GraphPayload(nodes=nodes, edges=edges)


async def generate_system_from_prompt(prompt: str) -> GenerateSystemResponse:
    prompt = prompt.strip()
    if not prompt:
        raise GenerateSystemError("empty_prompt", "Prompt is empty")

    if not _use_openai():
        gp = _stub_graph(prompt)
        return GenerateSystemResponse(nodes=gp.nodes, edges=gp.edges)

    user_msg = USER_GENERATE_TEMPLATE.format(prompt=prompt)
    try:
        raw = await chat_completion_json(
            system_prompt=SYSTEM_GENERATE_GRAPH,
            messages=[{"role": "user", "content": user_msg}],
            temperature=0.45,
        )
    except ValueError as exc:
        code = str(exc)
        logger.warning("generate_system.llm_transport", extra={"code": code})
        raise GenerateSystemError("llm_error", code) from exc

    if not isinstance(raw, dict):
        raise GenerateSystemError("llm_invalid_shape", "Expected JSON object")

    inner = raw.get("graph")
    if isinstance(inner, dict) and isinstance(inner.get("nodes"), list):
        raw = inner

    try:
        parsed = _LLMGraphShape.model_validate(raw)
    except ValidationError as exc:
        logger.warning("generate_system.validation", extra={"errors": exc.errors()})
        raise GenerateSystemError("llm_payload_invalid", "Graph JSON failed validation") from exc

    try:
        gp = _normalize_and_build(parsed.nodes, parsed.edges)
    except GenerateSystemError:
        raise
    except Exception as exc:
        logger.exception("generate_system.normalize")
        raise GenerateSystemError("normalize_failed", str(exc)) from exc

    return GenerateSystemResponse(nodes=gp.nodes, edges=gp.edges)
