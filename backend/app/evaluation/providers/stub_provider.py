from __future__ import annotations

from typing import Any

from app.evaluation.rule_engine import RuleFindings


class StubLLMProvider:
    """Offline provider for CI/local use when no API key is configured."""

    name = "stub"

    async def complete_evaluation_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        rule_findings: RuleFindings | None = None,
    ) -> dict[str, Any]:
        del system_prompt, user_prompt

        base = 74
        weaknesses: list[str] = []
        strengths: list[str] = [
            "Diagram is structured as nodes and edges suitable for automated checks.",
        ]
        questions: list[str] = [
            "What traffic and data volume growth do you expect in 12 months?",
            "Which parts require strong consistency vs eventual consistency?",
        ]

        f = rule_findings
        if f is not None:
            if f.no_cache:
                base -= 6
                weaknesses.append(
                    "No obvious cache / CDN layer detected in node labels or metadata."
                )
            if "single_db" in f.flags:
                base -= 8
                weaknesses.append(
                    "Only one datastore-like component — consider replicas, failover, and scaling."
                )
            if "no_explicit_database" in f.flags:
                base -= 10
                weaknesses.append(
                    "No explicit database / persistence tier found — clarify durable storage."
                )
            if f.no_load_balancer:
                base -= 7
                weaknesses.append(
                    "No load balancer or API gateway detected — ingress routing and blast-radius control unclear."
                )

        if not weaknesses:
            weaknesses.append(
                "Stub mode: set EVALUATION_LLM_PROVIDER=openai and OPENAI_API_KEY for deeper qualitative review."
            )

        score = max(0, min(100, base))

        return {
            "score": score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "questions": questions,
        }
