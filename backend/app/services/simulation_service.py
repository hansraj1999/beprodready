from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.llm.openai_json import chat_completion_json
from app.schemas.simulation import LLMSimulationResult, SimulateIncidentResponse
from app.simulation.prompts import SYSTEM_SIMULATOR, USER_SIMULATE_TEMPLATE
from app.simulation.weak_components import WeakComponentReport, build_weak_report

logger = logging.getLogger(__name__)


class SimulationLLMError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _use_openai() -> bool:
    return (
        settings.EVALUATION_LLM_PROVIDER.strip().lower() == "openai"
        and bool(settings.OPENAI_API_KEY.strip())
    )


def _stub_result(report: WeakComponentReport) -> LLMSimulationResult:
    """Rule-driven fallback incident when no LLM is configured."""
    weak_text = " ".join(report.weak_spots).lower()
    findings = report.findings

    if report.cache_node_count >= 1 or "cache" in weak_text or "redis" in weak_text:
        incident = {
            "title": "Redis / cache tier degradation",
            "component": "cache",
            "failure_mode": "memory pressure + eviction storm",
            "description": (
                "A hot key pattern caused memory pressure on the shared Redis cluster. "
                "Evictions spiked and application timeouts rose as clients hammered the backing database."
            ),
            "severity": "high",
        }
        impact = {
            "summary": "Read latency increased; DB load spiked as cache miss rate climbed.",
            "affected_components": ["cache", "application services", "primary database"],
            "user_visible_effects": "Slower page loads; elevated error rates on read-heavy endpoints.",
            "data_risk": "Low for durability; moderate for consistency if cache was used as session store.",
        }
        fixes = [
            "Add memory limits, eviction policy review, and shard hot keys; consider client-side caching.",
            "Introduce replication / HA for Redis with health checks and automated failover drills.",
            "Circuit-break DB access on cache failures; bulkhead thread pools for read paths.",
        ]
    elif report.queue_node_count >= 1 or "queue" in weak_text or "kafka" in weak_text:
        incident = {
            "title": "Message broker consumer lag incident",
            "component": "message_queue",
            "failure_mode": "broker partition under-replicated + consumer stall",
            "description": (
                "A broker restart left some partitions under-replicated while a poison message "
                "caused a consumer group to stall, growing backlog and delaying downstream workflows."
            ),
            "severity": "high",
        }
        impact = {
            "summary": "Async pipelines delayed; dependent services saw stale state and retries amplified load.",
            "affected_components": ["message bus", "workers", "downstream processors"],
            "user_visible_effects": "Delayed notifications or async features; intermittent timeouts on workflows.",
            "data_risk": "At-least-once delivery may duplicate side effects without idempotency keys.",
        }
        fixes = [
            "DLQ + poison message handling; consumer concurrency tuned per partition.",
            "Broker HA (RF>=3), ISR monitoring, and automated partition rebalancing runbooks.",
            "Backpressure from workers to producers; rate limits on enqueue paths.",
        ]
    elif "single_db" in findings.flags or findings.datastore_node_count == 1:
        incident = {
            "title": "Primary database failover during maintenance",
            "component": "database",
            "failure_mode": "failover latency + connection pool exhaustion",
            "description": (
                "Planned maintenance triggered a failover. Connection pools in services were not sized "
                "for reconnect storms, causing cascading timeouts while the new primary warmed caches."
            ),
            "severity": "critical",
        }
        impact = {
            "summary": "Write and read paths degraded; retries increased lock contention briefly.",
            "affected_components": ["primary database", "application tier", "batch jobs"],
            "user_visible_effects": "Elevated 5xx and slow transactions during the failover window.",
            "data_risk": "Split-brain risk if apps not using correct writer endpoint; verify RPO/RTO.",
        }
        fixes = [
            "Pool sizing + aggressive timeouts with jittered retries; fast-fail to read replicas for reads.",
            "Rehearse failover quarterly; enforce single writer via discovery / proxy.",
            "Add read replicas and caching for read-heavy paths to shed load from primary.",
        ]
    elif findings.no_load_balancer:
        incident = {
            "title": "Uneven traffic after deploy",
            "component": "ingress",
            "failure_mode": "missing LB / bad routing weights",
            "description": (
                "A deploy shifted traffic unevenly across instances. One node saturated while others idled, "
                "triggering CPU throttling and elevated latency without a clear single-component crash."
            ),
            "severity": "medium",
        }
        impact = {
            "summary": "Partial capacity loss perceived as intermittent slowness.",
            "affected_components": ["edge routing", "application instances"],
            "user_visible_effects": "Intermittent latency spikes correlated with traffic shifts.",
            "data_risk": "Low unless sticky sessions misrouted authenticated users.",
        }
        fixes = [
            "Introduce an L7 load balancer with health checks and consistent hashing if needed.",
            "Autoscaling tied to CPU/RPS with warm pools; blue/green or canary deploys.",
            "Service mesh traffic splitting for safer rollouts.",
        ]
    else:
        incident = {
            "title": "Service instance crash loop",
            "component": "application",
            "failure_mode": "OOM / bad config rollout",
            "description": (
                "A configuration change increased memory usage on stateful workers. Kubernetes restarted pods "
                "in a tight loop until the change was rolled back."
            ),
            "severity": "medium",
        }
        impact = {
            "summary": "Reduced effective capacity; retries increased load on dependencies.",
            "affected_components": ["workers", "dependencies hit by retries"],
            "user_visible_effects": "Degraded throughput for batch/async features.",
            "data_risk": "Duplicate processing if jobs lack idempotency.",
        }
        fixes = [
            "Progressive rollout with feature flags; memory limits and profiling on canary.",
            "Add readiness vs liveness probes tuned to avoid restart storms.",
            "Bulkhead dependencies and retry budgets.",
        ]

    return LLMSimulationResult.model_validate(
        {
            "incident": incident,
            "impact": impact,
            "suggested_fixes": fixes,
        }
    )


async def simulate_incident(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> SimulateIncidentResponse:
    report = build_weak_report(nodes, edges)
    weak_block = report.to_prompt_block()

    if _use_openai():
        graph_json = json.dumps({"nodes": nodes, "edges": edges}, indent=2, default=str)
        user_content = USER_SIMULATE_TEMPLATE.format(
            weak_block=weak_block,
            graph_json=graph_json,
        )
        try:
            raw = await chat_completion_json(
                system_prompt=SYSTEM_SIMULATOR,
                messages=[{"role": "user", "content": user_content}],
                temperature=0.45,
            )
        except ValueError as exc:
            code = str(exc)
            logger.warning("simulation.llm_error", extra={"code": code})
            raise SimulationLLMError(code) from exc
        try:
            parsed = LLMSimulationResult.model_validate(raw)
        except ValidationError as exc:
            raise SimulationLLMError("llm_schema_invalid") from exc
    else:
        parsed = _stub_result(report)

    return SimulateIncidentResponse(
        incident=parsed.incident,
        impact=parsed.impact,
        suggested_fixes=parsed.suggested_fixes,
    )
