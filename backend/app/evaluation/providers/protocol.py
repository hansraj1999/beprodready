from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.evaluation.rule_engine import RuleFindings


@runtime_checkable
class LLMProvider(Protocol):
    """Swappable backend for structured graph evaluation."""

    name: str

    async def complete_evaluation_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        rule_findings: RuleFindings | None = None,
    ) -> dict[str, Any]:
        """
        Return a dict with keys: score, strengths, weaknesses, questions.
        """
        ...
