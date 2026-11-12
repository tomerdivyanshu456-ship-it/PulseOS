from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_analyst_service import answer_product_question

router = APIRouter(
    prefix="/api/analyst",
    tags=["AI Analyst"],
)


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AnalystQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    history: list[ConversationTurn] = Field(default_factory=list, max_length=8)


@router.post("/ask")
def ask_analyst(payload: AnalystQuestion):
    try:
        history = [turn.model_dump() for turn in payload.history]
        return answer_product_question(payload.question.strip(), history)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The analyst could not process this question.",
        ) from exc
