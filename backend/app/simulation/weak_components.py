"""
Detect likely weak components / SPOFs from graph JSON for incident simulation.
Combines evaluation rule findings with per-tier node counts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.evaluation.rule_engine import RuleFindings, analyze_graph, findings_summary

_QUEUE_PATTERNS = re.compile(
    r"\b(kafka|kinesis|sqs|rabbitmq|nats|pulsar|eventbridge|pubsub|message queue|mq)\b",
    re.I,
)

_APP_PATTERNS = re.compile(
    r"\b(service|microservice|api|backend|worker|app server|application)\b",
    re.I,
)

_HA_PATTERNS = re.compile(
    r"\b(replica|replicas|ha\b|high availability|standby|multi-az|active-active|"
    r"active-passive|failover|cluster)\b",
    re.I,
)


def _node_blobs(nodes: list[dict[str, Any]]) -> list[str]:
    blobs: list[str] = []
    for n in nodes:
        if not isinstance(n, dict):
            blobs.append(str(n).lower())
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
        blobs.append(" ".join(parts).lower())
    return blobs


def _count_matches(blobs: list[str], pattern: re.Pattern[str]) -> int:
    return sum(1 for b in blobs if pattern.search(b))


@dataclass
class WeakComponentReport:
    findings: RuleFindings
    cache_node_count: int
    queue_node_count: int
    app_node_count: int
    ha_signals_present: bool
    weak_spots: list[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        lines = [
            "## Static analysis",
            findings_summary(self.findings),
            f"- Cache-like nodes (count): {self.cache_node_count}",
            f"- Queue / stream-like nodes (count): {self.queue_node_count}",
            f"- App / service-like nodes (count): {self.app_node_count}",
            f"- HA / replication language detected in graph: {self.ha_signals_present}",
            "## Weak spots (heuristic)",
        ]
        if self.weak_spots:
            for w in self.weak_spots:
                lines.append(f"- {w}")
        else:
            lines.append("- (none flagged — still pick a plausible production incident)")
        return "\n".join(lines)


_CACHE_NODE = re.compile(
    r"\b(redis|memcached|elasticache|varnish|cdn|cache|caching)\b",
    re.I,
)


def build_weak_report(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> WeakComponentReport:
    findings = analyze_graph(nodes, edges)
    blobs = _node_blobs(nodes)
    all_text = " ".join(blobs).lower()
    for e in edges:
        try:
            all_text += " " + json.dumps(e, default=str).lower()
        except (TypeError, ValueError):
            all_text += " " + str(e).lower()

    cache_nodes = _count_matches(blobs, _CACHE_NODE)
    queue_nodes = _count_matches(blobs, _QUEUE_PATTERNS)
    app_nodes = _count_matches(blobs, _APP_PATTERNS)
    ha = bool(_HA_PATTERNS.search(all_text))

    weak: list[str] = []
    if findings.no_cache:
        weak.append("No dedicated cache tier — hot read paths may hammer databases.")
    if findings.flags and "single_db" in findings.flags:
        weak.append("Single datastore component — SPOF and limited horizontal scale-out.")
    if findings.flags and "no_explicit_database" in findings.flags:
        weak.append("Persistence tier unclear — backup/restore and DR story undefined.")
    if findings.no_load_balancer:
        weak.append("No load balancer / gateway — uneven load and risky deploys.")
    if cache_nodes == 1:
        weak.append("Only one cache-like node — failure evicts sessions/ratelimits for all.")
    elif cache_nodes > 1 and not ha:
        weak.append("Multiple caches but no HA/replication language — split-brain / cold cache risk.")
    if queue_nodes == 1:
        weak.append("Single message bus / queue — backlog and consumer stall become systemic.")
    if queue_nodes == 0 and app_nodes >= 2:
        weak.append("No async / queue tier — spikes may cascade as synchronous coupling.")
    if app_nodes == 1:
        weak.append("Single application node — deploys and crashes are user-visible outages.")

    return WeakComponentReport(
        findings=findings,
        cache_node_count=cache_nodes,
        queue_node_count=queue_nodes,
        app_node_count=app_nodes,
        ha_signals_present=ha,
        weak_spots=weak,
    )
