from __future__ import annotations

import logging
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.interview.prompts import (
    SYSTEM_INTERVIEWER,
    USER_RESPOND_TEMPLATE,
    USER_START_TEMPLATE,
)
from app.llm.openai_json import chat_completion_json
from app.models.interview_session import InterviewSession
from app.schemas.interview import (
    AnswerEvaluation,
    InterviewStartResponse,
    InterviewRespondResponse,
    LLMInterviewRespond,
    LLMInterviewStart,
)

logger = logging.getLogger(__name__)


class InterviewNotFoundError(Exception):
    pass


class InterviewLLMError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _use_openai() -> bool:
    return (
        settings.EVALUATION_LLM_PROVIDER.strip().lower() == "openai"
        and bool(settings.OPENAI_API_KEY.strip())
    )


def _normalize_messages(raw: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for m in raw:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        c = content.strip()
        if not c:
            continue
        out.append({"role": role, "content": c})
    return out


def _trim_messages(msgs: list[dict[str, str]], max_messages: int) -> list[dict[str, str]]:
    if len(msgs) <= max_messages:
        return msgs
    return msgs[-max_messages:]


def _stub_start() -> LLMInterviewStart:
    return LLMInterviewStart(
        message=(
            "Welcome to the system design interview. We'll work through one problem; "
            "think out loud about tradeoffs and ask clarifying questions if needed."
        ),
        first_question=(
            "Design a real-time collaborative document editor (like a simplified Google Docs) "
            "for 10 million monthly active users. Cover sync, storage, conflict handling, and offline support."
        ),
    )


def _stub_respond(assistant_count: int, answer: str) -> LLMInterviewRespond:
    score = max(55, 88 - assistant_count * 6)
    return LLMInterviewRespond(
        evaluation=AnswerEvaluation(
            score=score,
            feedback=(
                "Stub mode: your answer was recorded. In production, an LLM would give "
                "detailed feedback on requirements, data model, scaling, and failure modes."
            ),
            strengths=["You provided a substantive response to move the interview forward."]
            if len(answer) > 80
            else ["You engaged with the prompt."],
            improvements=[
                "Quantify scale (reads/writes, payload sizes, latency targets).",
                "Call out consistency model and failure scenarios explicitly.",
            ],
        ),
        follow_up_questions=[
            "What consistency guarantees do users expect when two editors type simultaneously?",
            "How would you detect and recover from network partitions?",
        ],
        next_question=(
            f"(Turn {assistant_count + 1}) How would you shard and index the document storage tier as usage grows?"
        ),
    )


async def _llm_start() -> LLMInterviewStart:
    if not _use_openai():
        return _stub_start()
    try:
        raw = await chat_completion_json(
            system_prompt=SYSTEM_INTERVIEWER,
            messages=[{"role": "user", "content": USER_START_TEMPLATE}],
            temperature=0.4,
        )
    except ValueError as exc:
        code = str(exc)
        logger.warning("interview.start_llm_error", extra={"code": code})
        raise InterviewLLMError(code) from exc
    try:
        return LLMInterviewStart.model_validate(raw)
    except ValidationError as exc:
        raise InterviewLLMError("llm_schema_invalid") from exc


async def _llm_respond(
    history: list[dict[str, str]],
    latest_answer: str,
) -> LLMInterviewRespond:
    if not _use_openai():
        assistant_n = len([m for m in history if m["role"] == "assistant"])
        return _stub_respond(assistant_n, latest_answer)

    trimmed = _trim_messages(history, settings.INTERVIEW_MAX_MESSAGES)
    user_tail = USER_RESPOND_TEMPLATE.format(latest_answer=latest_answer.strip())
    messages = [*trimmed, {"role": "user", "content": user_tail}]
    try:
        raw = await chat_completion_json(
            system_prompt=SYSTEM_INTERVIEWER,
            messages=messages,
            temperature=0.35,
        )
    except ValueError as exc:
        code = str(exc)
        logger.warning("interview.respond_llm_error", extra={"code": code})
        raise InterviewLLMError(code) from exc
    try:
        return LLMInterviewRespond.model_validate(raw)
    except ValidationError as exc:
        raise InterviewLLMError("llm_schema_invalid") from exc


def _assistant_opening_text(message: str, first_question: str) -> str:
    return f"{message.strip()}\n\n**Question:**\n{first_question.strip()}"


def _assistant_followup_text(parsed: LLMInterviewRespond) -> str:
    ev = parsed.evaluation
    strengths = "\n".join(f"- {s}" for s in ev.strengths) or "- (none listed)"
    improvements = "\n".join(f"- {s}" for s in ev.improvements) or "- (none listed)"
    follow = "\n".join(f"- {s}" for s in parsed.follow_up_questions) or "- (none)"
    return (
        f"**Score:** {ev.score}/100\n\n"
        f"**Feedback:**\n{ev.feedback.strip()}\n\n"
        f"**Strengths:**\n{strengths}\n\n"
        f"**Improvements:**\n{improvements}\n\n"
        f"**Follow-up ideas:**\n{follow}\n\n"
        f"**Next question:**\n{parsed.next_question.strip()}"
    )


async def start_interview(db: AsyncSession, user_id: uuid.UUID) -> InterviewStartResponse:
    parsed = await _llm_start()
    opening = _assistant_opening_text(parsed.message, parsed.first_question)
    session = InterviewSession(
        user_id=user_id,
        messages=[{"role": "assistant", "content": opening}],
        turn_count=1,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info("interview.started", extra={"session_id": str(session.id), "user_id": str(user_id)})
    return InterviewStartResponse(
        session_id=session.id,
        message=parsed.message,
        first_question=parsed.first_question,
        turn=session.turn_count,
    )


async def respond_interview(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    answer: str,
) -> InterviewRespondResponse:
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise InterviewNotFoundError

    history = _normalize_messages(list(session.messages or []))
    history.append({"role": "user", "content": answer.strip()})

    parsed = await _llm_respond(history[:-1], answer)
    if not parsed.next_question.strip():
        parsed.next_question = "How would you evolve this design for 10x traffic?"

    assistant_body = _assistant_followup_text(parsed)
    session.messages = [*history, {"role": "assistant", "content": assistant_body}]
    session.turn_count = int(session.turn_count or 0) + 1

    await db.commit()
    await db.refresh(session)

    return InterviewRespondResponse(
        session_id=session.id,
        evaluation=parsed.evaluation,
        follow_up_questions=parsed.follow_up_questions,
        next_question=parsed.next_question.strip(),
        turn=session.turn_count,
    )
