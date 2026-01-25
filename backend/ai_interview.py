from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json

from openai import OpenAI

from database import supabase
from services.email_service import email_service
from config import config
from services.ai_service import ai_service

router = APIRouter()

client = OpenAI(api_key=config.OPENAI_API_KEY)

MAX_QUESTIONS = 5


class InterviewPayload(BaseModel):
    candidate_id: str
    answer: str | None = None


# =====================================================
# NEXT QUESTION
# =====================================================
@router.post("/ai-interview/next")
def next_question(payload: InterviewPayload):

    # 1️⃣ Load or create session
    session_res = (
        supabase.table("ai_interview_sessions")
        .select("*")
        .eq("candidate_id", payload.candidate_id)
        .execute()
    )

    session = session_res.data[0] if session_res.data else None



    if session_res.data:
        session = session_res.data
        question_count = session["question_count"]
        transcript = session.get("transcript", [])
    else:
        question_count = 0
        transcript = []
        completed = False
        supabase.table("ai_interview_sessions").insert({
            "candidate_id": payload.candidate_id,
            "question_count": 0,
            "transcript": [],
            "started_at": datetime.utcnow().isoformat()
        }).execute()

    # 2️⃣ Stop if interview completed
    # Stop if interview finished
    if question_count >= MAX_QUESTIONS:
        return {"completed": True}



    # 3️⃣ Save previous answer safely
    if payload.answer and transcript:
        transcript[-1]["answer"] = payload.answer

    # 4️⃣ Generate next question (GPT-5-mini SAFE)
    prompt = f"""
You are a professional AI interviewer.

Ask ONE clear interview question.
This is question {question_count + 1} of {MAX_QUESTIONS}.
Adapt difficulty based on previous answers.
"""

    question = ai_service.generate_completion(prompt)



    # 5️⃣ Append new question
    transcript.append({
        "question": question,
        "answer": None
    })

    # 6️⃣ Update session
    supabase.table("ai_interview_sessions").update({
        "question_count": question_count + 1,
        "transcript": transcript,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("candidate_id", payload.candidate_id).execute()

    return {
        "completed": False,
        "question": question,
        "current": question_count + 1,
        "total": MAX_QUESTIONS
    }


# =====================================================
# FINAL EVALUATION
# =====================================================
@router.post("/ai-interview/evaluate")
def evaluate_interview(payload: InterviewPayload):

    session_res = (
        supabase.table("ai_interview_sessions")
        .select("*")
        .eq("candidate_id", payload.candidate_id)
        .execute()
    )

    if not session_res.data:
        raise HTTPException(status_code=400, detail="Interview session not found")

    session = session_res.data[0]



    transcript = session["transcript"]

    # 🔒 Save last answer
    if payload.answer and transcript:
        transcript[-1]["answer"] = payload.answer

    transcript_text = "\n\n".join(
        f"Q: {t['question']}\nA: {t['answer']}"
        for t in transcript if t.get("answer")
    )

    eval_prompt = f"""
Evaluate the candidate interview.

Interview Transcript:
{transcript_text}

Return STRICT JSON ONLY:
{{
  "skill_score": 0,
  "communication_score": 0,
  "problem_solving_score": 0,
  "culture_fit_score": 0,
  "overall_score": 0,
  "recommendation": "Strong Fit | Moderate Fit | Not Recommended",
  "evaluation_notes": ""
}}
"""

    response = client.responses.create(
        model=config.AI_MODEL,
        input=eval_prompt
    )

    raw = response.output_text.strip()

    try:
        evaluation = json.loads(raw)
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

    # 1️⃣ Fetch candidate
    candidate = (
        supabase.table("candidates")
        .select("id, email, name, vacancy_id")
        .eq("id", payload.candidate_id)
        .single()
        .execute()
    ).data

    # 2️⃣ Store interview
    supabase.table("ai_interviews").insert({
        "candidate_id": payload.candidate_id,
        "vacancy_id": candidate["vacancy_id"],
        "interview_transcript": transcript,
        "skill_score": evaluation["skill_score"],
        "communication_score": evaluation["communication_score"],
        "problem_solving_score": evaluation["problem_solving_score"],
        "culture_fit_score": evaluation["culture_fit_score"],
        "overall_score": evaluation["overall_score"],
        "recommendation": evaluation["recommendation"],
        "evaluation_notes": evaluation["evaluation_notes"],
        "started_at": session["started_at"],
        "completed_at": datetime.utcnow().isoformat()
    }).execute()

    # 3️⃣ Close session
    supabase.table("ai_interview_sessions").update({
        "transcript": transcript,
        "updated_at": datetime.utcnow().isoformat()
    }).eq("candidate_id", payload.candidate_id).execute()

    # 4️⃣ Update candidate
    supabase.table("candidates").update({
        "status": "interviewed",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", payload.candidate_id).execute()

    # 5️⃣ Auto-Calendly
    if evaluation["overall_score"] >= 75:
        email_service.send_final_interview_schedule(
            payload.candidate_id,
            candidate["email"],
            candidate["name"],
            "Final Interview",
            "Online",
            config.CALENDLY_LINK
        )

        supabase.table("candidates").update({
            "status": "recommended"
        }).eq("id", payload.candidate_id).execute()

    return {"success": True, "evaluation": evaluation}
