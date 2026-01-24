
from fastapi import APIRouter
from pydantic import BaseModel
import os
import openai
import datetime

router = APIRouter()

openai.api_key = os.getenv("OPENAI_API_KEY")

class InterviewPayload(BaseModel):
    candidate_id: str
    answer: str | None = None

@router.post("/ai-interview/next")
def next_question(payload: InterviewPayload):
    prompt = f"""
You are a professional AI interviewer.

Ask ONE interview question.
Adapt difficulty based on previous answer.
Previous answer: {payload.answer}
"""

    response = openai.ChatCompletion.create(
        model=os.getenv("AI_MODEL", "gpt-5-mini"),
        messages=[{"role": "user", "content": prompt}]
    )

    return {"question": response.choices[0].message.content}


@router.post("/ai-interview/evaluate")
def evaluate_interview(payload: InterviewPayload):
    eval_prompt = f"""
Evaluate the candidate interview answer.

Answer:
{payload.answer}

Return:
Skill Fit:
Communication:
Problem Solving:
Culture Fit:
Overall Verdict:
"""

    response = openai.ChatCompletion.create(
        model=os.getenv("AI_MODEL", "gpt-5-mini"),
        messages=[{"role": "user", "content": eval_prompt}]
    )

    return {"evaluation": response.choices[0].message.content}
