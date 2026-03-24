from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnswerEvaluation(BaseModel):
    score: int = Field(..., ge=0, le=100)
    feedback: str = ""
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)

    @field_validator("score", mode="before")
    @classmethod
    def coerce_score(cls, value: Any) -> int:
        x = int(round(float(value)))
        return max(0, min(100, x))

    @field_validator("strengths", "improvements", mode="before")
    @classmethod
    def coerce_str_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            s = str(value).strip()
            return [s] if s else []
        out: list[str] = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out


class InterviewStartResponse(BaseModel):
    session_id: UUID
    message: str
    first_question: str
    turn: int = Field(..., ge=0, description="Interviewer turn counter after opening.")


class InterviewRespondRequest(BaseModel):
    session_id: UUID
    answer: str = Field(..., min_length=1, max_length=50_000)


class InterviewRespondResponse(BaseModel):
    session_id: UUID
    evaluation: AnswerEvaluation
    follow_up_questions: list[str]
    next_question: str
    turn: int = Field(..., ge=0)


class LLMInterviewStart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str
    first_question: str


class LLMInterviewRespond(BaseModel):
    model_config = ConfigDict(extra="ignore")

    evaluation: AnswerEvaluation
    follow_up_questions: list[str] = Field(default_factory=list)
    next_question: str = ""

    @field_validator("follow_up_questions", mode="before")
    @classmethod
    def coerce_followups(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            s = str(value).strip()
            return [s] if s else []
        return [str(x).strip() for x in value if str(x).strip()]
