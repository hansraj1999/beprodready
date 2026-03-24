"""Prompt templates for graph evaluation LLM."""

from __future__ import annotations

import json
from typing import Any

from app.evaluation.rule_engine import RuleFindings, findings_summary


SYSTEM_PROMPT = """You are a senior staff engineer evaluating system design diagrams.
You receive a JSON graph (nodes and edges) and static rule-engine signals.
Respond with ONLY valid JSON matching this shape (no markdown fences):
{
  "score": <integer 0-100>,
  "strengths": [<string>, ...],
  "weaknesses": [<string>, ...],
  "questions": [<string>, ...]
}
Be specific and reference concrete elements from the graph when possible.
Score reflects production readiness, scalability, reliability, and clarity of the design.
If the graph is minimal or ambiguous, lower the score and add clarifying questions."""


def build_user_prompt(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    findings: RuleFindings,
) -> str:
    graph_json = json.dumps(
        {"nodes": nodes, "edges": edges},
        indent=2,
        default=str,
    )
    rules_block = findings_summary(findings)
    return (
        "Evaluate the following system design graph.\n\n"
        "## Rule engine signals (heuristic; verify against the graph)\n"
        f"{rules_block}\n\n"
        "Pay special attention when signals indicate:\n"
        "- no_cache: no obvious caching layer\n"
        "- single_db / no_explicit_database: one or zero datastore-like components\n"
        "- no_load_balancer: no obvious traffic distribution / gateway / LB\n\n"
        "## Graph JSON\n"
        f"{graph_json}\n"
    )
