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

MAX_QUESTIONS = 5  # 🔒 interview length


class InterviewPayload(BaseModel):
    candidate_id: str
    answer: str | None = None


# =====================================================
# NEXT QUESTION (WITH COMPLETION + PROGRESS)
# =====================================================
@router.post("/ai-interview/next")
def next_question(payload: InterviewPayload):

    # Fetch or create interview session
    session = supabase.table("ai_interview_sessions") \
        .select("*") \
        .eq("candidate_id", payload.candidate_id) \
        .maybeSingle() \
        .execute()

    if session.data:
        question_count = session.data["question_count"]
        transcript = session.data.get("transcript", [])
    else:
        question_count = 0
        transcript = []
        supabase.table("ai_interview_sessions").insert({
            "candidate_id": payload.candidate_id,
            "question_count": 0,
            "transcript": [],
            "started_at": datetime.utcnow().isoformat()
        }).execute()

    # Interview completed
    if question_count >= MAX_QUESTIONS:
        return {
            "completed": True,
            "message": "Interview completed"
        }

    prompt = f"""
You are a professional AI interviewer.

Ask ONE clear interview question.
Adapt difficulty based on previous answer.

Previous answer:
{payload.answer or "None"}
"""

    response = openai.ChatCompletion.create(
        model=os.getenv("AI_MODEL", "gpt-5-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    question = response.choices[0].message.content.strip()

    # Update session progress
    supabase.table("ai_interview_sessions").update({
        "question_count": question_count + 1,
        "transcript": transcript + [{
            "question": question,
            "answer": payload.answer
        }],
        "updated_at": datetime.utcnow().isoformat()
    }).eq("candidate_id", payload.candidate_id).execute()

    return {
        "completed": False,
        "question": question,
        "current": question_count + 1,
        "total": MAX_QUESTIONS
    }


# =====================================================
# FINAL EVALUATION + AUTO CALENDLY MAIL
# =====================================================
@router.post("/ai-interview/evaluate")
def evaluate_interview(payload: InterviewPayload):

    if not payload.answer:
        raise HTTPException(status_code=400, detail="Answer is required")

    session = supabase.table("ai_interview_sessions") \
        .select("*") \
        .eq("candidate_id", payload.candidate_id) \
        .single() \
        .execute()

    transcript_text = "\n\n".join(
        f"Q: {t.get('question')}\nA: {t.get('answer')}"
        for t in session.data["transcript"]
    )

    eval_prompt = f"""
Evaluate the candidate interview.

Interview Transcript:
{transcript_text}

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
        evaluation = {
            "skill_score": 70,
            "communication_score": 70,
            "problem_solving_score": 70,
            "culture_fit_score": 70,
            "overall_score": 70,
            "recommendation": "Moderate Fit",
            "evaluation_notes": "Fallback evaluation"
        }

    # Fetch candidate
    candidate = supabase.table("candidates") \
        .select("id, email, name, vacancy_id") \
        .eq("id", payload.candidate_id) \
        .single() \
        .execute()

    candidate_data = candidate.data

    # Store final interview
    supabase.table("ai_interviews").insert({
        "candidate_id": payload.candidate_id,
        "vacancy_id": candidate_data["vacancy_id"],
        "interview_transcript": session.data["transcript"],
        "skill_score": evaluation["skill_score"],
        "communication_score": evaluation["communication_score"],
        "problem_solving_score": evaluation["problem_solving_score"],
        "culture_fit_score": evaluation["culture_fit_score"],
        "overall_score": evaluation["overall_score"],
        "recommendation": evaluation["recommendation"],
        "evaluation_notes": evaluation["evaluation_notes"],
        "started_at": session.data["started_at"],
        "completed_at": datetime.utcnow().isoformat()
    }).execute()

    # Update candidate status
    supabase.table("candidates").update({
        "status": "interviewed",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", payload.candidate_id).execute()

    # 🔥 AUTO SEND CALENDLY LINK
    if evaluation["overall_score"] > 75:
        email_service.send_final_interview_schedule(
            payload.candidate_id,
            candidate_data["email"],
            candidate_data["name"],
            "Book your final interview using the link below",
            "Online",
            config.CALENDLY_LINK
        )

        supabase.table("candidates").update({
            "status": "recommended",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", payload.candidate_id).execute()

    return {
        "success": True,
        "evaluation": evaluation
    }
