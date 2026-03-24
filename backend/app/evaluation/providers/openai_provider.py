from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


class OpenAILLMProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_s: float = 120.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    async def complete_evaluation_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        rule_findings: object = None,
    ) -> dict[str, Any]:
        del rule_findings
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.25,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "openai.http_error",
                extra={"status": exc.response.status_code, "body": (exc.response.text or "")[:500]},
            )
            raise ValueError("openai_http_error") from exc
        except httpx.RequestError as exc:
            logger.error("openai.network_error", extra={"error": str(exc)})
            raise ValueError("openai_network_error") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("openai.unexpected_response_shape", extra={"data": str(data)[:500]})
            raise ValueError("openai_bad_response") from exc

        try:
            return _parse_json_content(str(content))
        except json.JSONDecodeError as exc:
            logger.warning("openai.invalid_json_content", extra={"content": str(content)[:500]})
            raise ValueError("openai_invalid_json") from exc


def build_openai_provider() -> OpenAILLMProvider:
    return OpenAILLMProvider(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_EVAL_MODEL,
        base_url=settings.OPENAI_BASE_URL,
        timeout_s=settings.OPENAI_EVAL_TIMEOUT_S,
    )
