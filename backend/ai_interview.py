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



    if session:
        question_count = session["question_count"]
        transcript = session.get("transcript", [])
    else:
        question_count = 0
        transcript = []


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


    last_answer = (
        transcript[-1]["answer"]
        if transcript and transcript[-1].get("answer")
        else "No previous answer yet."
    )

    # 4️⃣ Generate next question (GPT-5-mini SAFE)
    prompt = f"""
You are a senior human interviewer conducting a real hiring interview.

Interview Context:
- Job Role: {vacancy_data['job_role']}
- Experience Level Target: {vacancy_data['experience_level']}
- Required Skills: {', '.join(vacancy_data['required_skills'])}
- Job Description: {vacancy_data.get('description', 'N/A')}

Candidate Resume Summary:
{candidate_data.get('resume_text', '')}

Interview Progress:
- This is question {question_count + 1} out of {MAX_QUESTIONS}
- Previous answer (if any):
{last_answer}

INTERVIEW BEHAVIOR RULES (STRICT):
1. Ask ONLY ONE question at a time.
2. The question MUST be directly grounded in:
   - the candidate’s resume
   - the job requirements
3. NEVER repeat:
   - a previously asked question
   - a previously covered topic
4. Adapt dynamically based on the last answer:
   - If the answer was strong → go deeper, add complexity, edge cases, or real-world constraints
   - If the answer was weak, vague, or incorrect → probe gently, clarify, or simplify
5. Progress naturally like a human interview:
   - Early phase: verify resume claims, fundamentals, understanding
   - Middle phase: real-world experience, decision-making, problem solving
   - Advanced phase: ownership, trade-offs, failure handling, role-critical challenges
6. Prefer scenario-based and experience-driven questions over theory.
7. Avoid generic or HR-style questions (e.g., “Tell me about yourself”).
8. Assume the interview can continue indefinitely until stopped externally.
9. Maintain a professional, intelligent, human tone.

OUTPUT RULES:
- Return ONLY the interview question.
- No explanations.
- No numbering.
- No formatting.
- No extra text.

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
You are a senior hiring panel conducting a final interview evaluation.

Your task is to evaluate the candidate’s interview performance
in relation to the job requirements and their resume background.

Job Context:
- Role: {vacancy_data['job_role']}
- Experience Level: {vacancy_data['experience_level']}
- Required Skills: {', '.join(vacancy_data['required_skills'])}
- Culture Traits: {', '.join(vacancy_data['culture_traits'])}
- Job Description: {vacancy_data.get('description', 'N/A')}

Candidate Resume (BACKGROUND ONLY — NOT PROOF):
{candidate_data.get('resume_text', '')}

Interview Transcript (PRIMARY EVIDENCE):
{transcript_text}

EVALUATION RULES (STRICT):
1. Base scores PRIMARILY on interview answers.
2. Resume may be used ONLY to:
   - check consistency
   - validate claims made during the interview
3. If a skill appears on the resume but is NOT demonstrated in interview → do NOT reward it.
4. Penalize:
   - vague responses
   - buzzwords without explanation
   - theoretical answers without practical examples
5. Reward:
   - clear reasoning
   - concrete examples
   - decision trade-offs
   - ownership and real-world thinking
6. Be strict, fair, and realistic — as if a real hiring decision depends on this.
7. Scores must be internally consistent.
8. Recommendation must naturally follow performance.
9. Do NOT reference numeric cutoffs or hiring rules.

SCORING CALIBRATION (INTERNAL — DO NOT MENTION):
- 90–100 → Exceptional, interview-ready hire
- 80–89 → Strong candidate with minor gaps
- 65–79 → Partial fit, needs improvement
- <65 → Not suitable for this role

RETURN STRICT JSON ONLY:
{
  "skill_score": <0–100>,
  "communication_score": <0–100>,
  "problem_solving_score": <0–100>,
  "culture_fit_score": <0–100>,
  "overall_score": <0–100>,
  "recommendation": "Strong Fit | Moderate Fit | Not Recommended",
  "evaluation_notes": "Short, specific justification referencing interview answers and job relevance"
}
"""

    raw = ai_service.generate_completion(eval_prompt)

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
    if evaluation["overall_score"] >= 80:
        try:
            email_service.send_final_interview_schedule(
                payload.candidate_id,
                candidate["email"],
                candidate["name"],
                "Final Interview",
                "Online",
                config.CALENDLY_LINK
            )
        except Exception as e:
            print("⚠️ Calendly email failed:", e)

        supabase.table("candidates").update({
            "status": "recommended"
        }).eq("id", payload.candidate_id).execute()

    else:
   
        try:
            email_service.send_rejection_email(
                payload.candidate_id,
                candidate["email"],
                candidate["name"]
            )
        except Exception as e:
            print("⚠️ Rejection email failed:", e)

        supabase.table("candidates").update({
            "status": "rejected",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", payload.candidate_id).execute()


    return {"success": True, "evaluation": evaluation}
