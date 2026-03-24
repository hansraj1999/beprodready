from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


async def chat_completion_json(
    *,
    system_prompt: str,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.35,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    """
    OpenAI-compatible chat completions with response_format json_object.
    `messages` must be OpenAI-shaped {role, content} (user/assistant only).
    """
    m = model or settings.OPENAI_EVAL_MODEL
    timeout = timeout_s if timeout_s is not None else settings.OPENAI_EVAL_TIMEOUT_S
    url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": m,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "openai_json.http_error",
            extra={"status": exc.response.status_code, "body": (exc.response.text or "")[:500]},
        )
        raise ValueError("openai_http_error") from exc
    except httpx.RequestError as exc:
        logger.error("openai_json.network_error", extra={"error": str(exc)})
        raise ValueError("openai_network_error") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        logger.error("openai_json.bad_shape", extra={"data": str(data)[:500]})
        raise ValueError("openai_bad_response") from exc

    try:
        return parse_json_content(str(content))
    except json.JSONDecodeError as exc:
        logger.warning("openai_json.invalid_json", extra={"content": str(content)[:500]})
        raise ValueError("openai_invalid_json") from exc
