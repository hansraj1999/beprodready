from __future__ import annotations

import logging

from app.core.config import settings
from app.evaluation.providers.openai_provider import OpenAILLMProvider, build_openai_provider
from app.evaluation.providers.protocol import LLMProvider
from app.evaluation.providers.stub_provider import StubLLMProvider

logger = logging.getLogger(__name__)


def get_llm_provider() -> LLMProvider:
    """
    Select LLM backend from settings. Falls back to stub when misconfigured.
    """
    name = settings.EVALUATION_LLM_PROVIDER.strip().lower()
    if name == "openai":
        if not settings.OPENAI_API_KEY.strip():
            logger.warning("evaluation.openai_missing_key_fallback_stub")
            return StubLLMProvider()
        return build_openai_provider()
    if name == "stub":
        return StubLLMProvider()
    logger.warning(
        "evaluation.unknown_provider_fallback_stub",
        extra={"provider": name},
    )
    return StubLLMProvider()
