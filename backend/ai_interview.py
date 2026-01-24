from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import json
from datetime import datetime

import openai

from database import supabase
from services.email_service import email_service
from config import config

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
Previous answer:
{payload.answer or "None"}
"""

    response = openai.ChatCompletion.create(
        model=os.getenv("AI_MODEL", "gpt-5-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return {"question": response.choices[0].message.content.strip()}


@router.post("/ai-interview/evaluate")
def evaluate_interview(payload: InterviewPayload):
    if not payload.answer:
        raise HTTPException(status_code=400, detail="Answer is required")

    eval_prompt = f"""
Evaluate the candidate interview answer.

Answer:
{payload.answer}

Return STRICT JSON only:
{{
  "skill_score": <0-100>,
  "communication_score": <0-100>,
  "problem_solving_score": <0-100>,
  "culture_fit_score": <0-100>,
  "overall_score": <0-100>,
  "recommendation": "<Strong Fit | Moderate Fit | Not Recommended>",
  "evaluation_notes": "<short explanation>"
}}
"""

    response = openai.ChatCompletion.create(
        model=os.getenv("AI_MODEL", "gpt-5-mini"),
        messages=[{"role": "user", "content": eval_prompt}],
        temperature=0.3
    )

    raw_text = response.choices[0].message.content

    try:
        evaluation = json.loads(raw_text)
    except Exception:
        # fallback (safe default)
        evaluation = {
            "skill_score": 70,
            "communication_score": 70,
            "problem_solving_score": 70,
            "culture_fit_score": 70,
            "overall_score": 70,
            "recommendation": "Moderate Fit",
            "evaluation_notes": "Fallback evaluation due to parsing issue"
        }

    # -----------------------------
    # STORE INTERVIEW IN DATABASE
    # -----------------------------
    candidate = supabase.table("candidates") \
        .select("id, email, name, vacancy_id") \
        .eq("id", payload.candidate_id) \
        .single() \
        .execute()

    candidate_data = candidate.data

    supabase.table("ai_interviews").insert({
        "candidate_id": payload.candidate_id,
        "vacancy_id": candidate_data["vacancy_id"],
        "interview_transcript": [{"answer": payload.answer}],
        "skill_score": evaluation["skill_score"],
        "communication_score": evaluation["communication_score"],
        "problem_solving_score": evaluation["problem_solving_score"],
        "culture_fit_score": evaluation["culture_fit_score"],
        "overall_score": evaluation["overall_score"],
        "recommendation": evaluation["recommendation"],
        "evaluation_notes": evaluation["evaluation_notes"],
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat()
    }).execute()

    supabase.table("candidates").update({
        "status": "interviewed",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", payload.candidate_id).execute()

    # -------------------------------------------------
    # 🔥 AUTO SEND CALENDLY (RULE 3)
    # -------------------------------------------------
    if evaluation["overall_score"] > 75:
        calendly_link = config.CALENDLY_LINK

        email_service.send_final_interview_schedule(
            payload.candidate_id,
            candidate_data["email"],
            candidate_data["name"],
            "Book your final interview using the link below",
            "Online",
            calendly_link
        )

        supabase.table("candidates").update({
            "status": "recommended",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", payload.candidate_id).execute()

    return {
        "success": True,
        "evaluation": evaluation
    }
