"""
Heuristic rule engine over graph JSON (nodes + edges).
Uses keyword / pattern matching on serialized node and edge payloads.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleFindings:
    """Signals derived from static analysis of the graph."""

    has_cache: bool = False
    has_load_balancer: bool = False
    datastore_node_count: int = 0
    flags: list[str] = field(default_factory=list)

    @property
    def no_cache(self) -> bool:
        return not self.has_cache

    @property
    def single_db(self) -> bool:
        return self.datastore_node_count == 1

    @property
    def no_load_balancer(self) -> bool:
        return not self.has_load_balancer


_CACHE_PATTERNS = re.compile(
    r"\b(redis|memcached|elasticache|varnish|cdn|cache|caching|"
    r"in[- ]?memory|evcache|hazelcast|ignite)\b",
    re.I,
)

_DATASTORE_PATTERNS = re.compile(
    r"\b(postgres|postgresql|mysql|mariadb|mongo|mongodb|dynamodb|"
    r"cassandra|cockroach|sqlite|oracle|mssql|sql server|neo4j|"
    r"elasticsearch|opensearch|clickhouse|bigquery|snowflake|"
    r"rds|aurora|database|dbms|data store|datastore)\b",
    re.I,
)

# Redis often used as cache; if label is clearly cache-only, exclude from DB count
_REDIS_AS_CACHE_ONLY = re.compile(
    r"\b(redis)\b.*\b(cache|session|caching|ephemeral)\b|\b(cache|session)\b.*\b(redis)\b",
    re.I,
)

_LB_PATTERNS = re.compile(
    r"\b(load[\s_-]?balancer|alb|nlb|elb|haproxy|envoy|traefik|"
    r"nginx|api[\s_-]?gateway|kong|ambassador|istio[\s_-]?gateway|"
    r"aws[\s_-]?gateway|application[\s_-]?gateway)\b",
    re.I,
)


def _blob_from_obj(obj: Any) -> str:
    try:
        return json.dumps(obj, default=str).lower()
    except (TypeError, ValueError):
        return str(obj).lower()


def _iter_node_texts(nodes: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for n in nodes:
        if not isinstance(n, dict):
            texts.append(str(n).lower())
            continue
        parts: list[str] = []
        for key in ("type", "label", "name", "title", "kind", "component"):
            v = n.get(key)
            if isinstance(v, str):
                parts.append(v)
        data = n.get("data")
        if isinstance(data, dict):
            parts.append(json.dumps(data, default=str))
        elif isinstance(data, str):
            parts.append(data)
        parts.append(json.dumps(n, default=str))
        texts.append(" ".join(parts).lower())
    return texts


def _iter_edge_texts(edges: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for e in edges:
        if not isinstance(e, dict):
            texts.append(str(e).lower())
            continue
        texts.append(_blob_from_obj(e))
    return texts


def analyze_graph(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> RuleFindings:
    node_texts = _iter_node_texts(nodes)
    edge_texts = _iter_edge_texts(edges)
    all_text = " ".join(node_texts + edge_texts)

    has_cache = bool(_CACHE_PATTERNS.search(all_text))
    has_lb = bool(_LB_PATTERNS.search(all_text))

    db_hits = 0
    for blob in node_texts:
        if not _DATASTORE_PATTERNS.search(blob):
            continue
        if _REDIS_AS_CACHE_ONLY.search(blob) and "redis" in blob:
            if _CACHE_PATTERNS.search(blob) and not re.search(
                r"\b(persist|primary store|source of truth)\b", blob, re.I
            ):
                continue
        db_hits += 1

    flags: list[str] = []
    if not has_cache:
        flags.append("no_cache")
    if db_hits == 0:
        flags.append("no_explicit_database")
    elif db_hits == 1:
        flags.append("single_db")
    if not has_lb:
        flags.append("no_load_balancer")

    return RuleFindings(
        has_cache=has_cache,
        has_load_balancer=has_lb,
        datastore_node_count=db_hits,
        flags=flags,
    )


def findings_summary(findings: RuleFindings) -> str:
    lines = [
        f"- No cache (heuristic): {findings.no_cache}",
        f"- Single DB only (heuristic): {findings.single_db}",
        f"- No load balancer / gateway (heuristic): {findings.no_load_balancer}",
        f"- Datastore-like nodes counted: {findings.datastore_node_count}",
        f"- Rule flags: {', '.join(findings.flags) if findings.flags else '(none)'}",
    ]
    return "\n".join(lines)
