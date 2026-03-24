from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.evaluation.exceptions import EvaluationFailed
from app.evaluation.prompts import SYSTEM_PROMPT, build_user_prompt
from app.evaluation.providers.protocol import LLMProvider
from app.evaluation.rule_engine import analyze_graph
from app.schemas.evaluation import EvaluateRequest, EvaluateResponse, EvaluationLLMResult

logger = logging.getLogger(__name__)


def _normalize_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for item in values:
        s = str(item).strip()
        if s:
            out.append(s)
    return out


async def evaluate_graph(
    body: EvaluateRequest,
    provider: LLMProvider,
) -> EvaluateResponse:
    findings = analyze_graph(body.nodes, body.edges)
    user_prompt = build_user_prompt(body.nodes, body.edges, findings)

    try:
        raw = await provider.complete_evaluation_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            rule_findings=findings,
        )
    except ValueError as exc:
        code = str(exc)
        logger.warning("evaluation.provider_value_error", extra={"code": code})
        raise EvaluationFailed("llm_provider_error", code) from exc

    if not isinstance(raw, dict):
        raise EvaluationFailed("llm_invalid_shape", "Expected JSON object from LLM")

    try:
        parsed = EvaluationLLMResult.model_validate(raw)
    except ValidationError as exc:
        logger.warning("evaluation.llm_validation", extra={"errors": exc.errors()})
        raise EvaluationFailed("llm_payload_invalid", "LLM output failed validation") from exc

    return EvaluateResponse(
        score=parsed.score,
        strengths=_normalize_str_list(parsed.strengths),
        weaknesses=_normalize_str_list(parsed.weaknesses),
        questions=_normalize_str_list(parsed.questions),
    )


def safe_preview_for_logs(body: EvaluateRequest, max_len: int = 2000) -> str:
    try:
        s = json.dumps(
            {"nodes": body.nodes, "edges": body.edges},
            default=str,
        )
    except (TypeError, ValueError):
        s = str(body)
    return s[:max_len]
