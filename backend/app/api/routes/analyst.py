from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_analyst_service import answer_product_question

router = APIRouter(
    prefix="/api/analyst",
    tags=["AI Analyst"],
)


class AnalystQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@router.post("/ask")
def ask_analyst(payload: AnalystQuestion):
    try:
        return answer_product_question(payload.question.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The analyst could not process this question.",
        ) from exc
