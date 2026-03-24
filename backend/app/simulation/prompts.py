SYSTEM_SIMULATOR = """You simulate **realistic production incidents** for system architecture diagrams.
Use the weak-component analysis as hints, but ground the scenario in the actual nodes/edges.
Output **only valid JSON** (no markdown) matching the user's schema.
Severity must be one of: low, medium, high, critical.
Be specific: name components, failure modes, blast radius, and mitigations that match the diagram."""

USER_SIMULATE_TEMPLATE = """{weak_block}

## Graph JSON
{graph_json}

Return JSON with exactly this shape:
{{
  "incident": {{
    "title": string,
    "component": string (which node/tier fails),
    "failure_mode": string (e.g. "partial outage", "latency spike", "data corruption risk"),
    "description": string (2-5 sentences, ops/on-call style),
    "severity": "low" | "medium" | "high" | "critical"
  }},
  "impact": {{
    "summary": string,
    "affected_components": [string, ...],
    "user_visible_effects": string,
    "data_risk": string
  }},
  "suggested_fixes": [string, ...]
}}

Pick a failure that is **credible** given weak spots (e.g. Redis memory pressure, DB failover delay, LB health-check flapping, Kafka ISR shrink). If the diagram is sparse, still propose a plausible incident tied to labeled components."""
