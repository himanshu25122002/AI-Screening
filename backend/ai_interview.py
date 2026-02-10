from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
import json

from openai import OpenAI

from backend.database import supabase
from backend.services.email_service import email_service
from backend.config import config
from backend.services.ai_service import ai_service

router = APIRouter()

client = OpenAI(api_key=config.OPENAI_API_KEY)

MAX_QUESTIONS = 5


class InterviewPayload(BaseModel):
    candidate_id: str
    answer: str | None = None
class TokenPayload(BaseModel):
    token: str


@router.post("/ai-interview/validate")
def validate_interview(payload: TokenPayload):
    token = payload.token

    res = (
        supabase
        .table("ai_interview_sessions")
        .select("*")
        .eq("interview_token", token)
        .eq("is_active", True)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=403, detail="Invalid interview link")

    session = res.data[0]
    now = datetime.now(timezone.utc)

    scheduled_at = session.get("scheduled_at")
    expires_at = session.get("expires_at")

    if not scheduled_at or not expires_at:
        raise HTTPException(status_code=403, detail="Interview not scheduled properly")

    def to_utc(dt):
        if isinstance(dt, str):
            return datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(timezone.utc)
        return dt.astimezone(timezone.utc)

    scheduled_at_dt = to_utc(scheduled_at)
    expires_at_dt = to_utc(expires_at)

    if now < scheduled_at_dt:
        raise HTTPException(status_code=403, detail="Interview has not started yet")

    if now > expires_at_dt:
        supabase.table("ai_interview_sessions").update({
            "is_active": False
        }).eq("id", session["id"]).execute()

        raise HTTPException(status_code=403, detail="Interview link expired")

    # ✅ CRITICAL FIX
    supabase.table("ai_interview_sessions").update({
        "started_at": session.get("started_at") or now.isoformat()
    }).eq("id", session["id"]).execute()

    return {
        "success": True,
        "candidate_id": session["candidate_id"]
    }




# =====================================================
# NEXT QUESTION
# =====================================================
@router.post("/ai-interview/next")
def next_question(payload: InterviewPayload):
    

    # 1️⃣ Load or create session
    session_res = (
        supabase
        .table("ai_interview_sessions")
        .select("*")
        .eq("candidate_id", payload.candidate_id)
        .eq("is_active", True)
        .execute()
    )

    if not session_res.data:
        raise HTTPException(status_code=403, detail="Interview session inactive")

    session = session_res.data[0]



    if session:
        question_count = session["question_count"]
        transcript = session.get("transcript", [])
    

    # 2️⃣ Stop if interview completed
    # Stop if interview finished
    if question_count >= MAX_QUESTIONS:
        return {"completed": True}



    
    if payload.answer and transcript:
        transcript[-1]["answer"] = payload.answer


    last_answer = (
        transcript[-1]["answer"]
        if transcript and transcript[-1].get("answer")
        else "No previous answer yet."
    )

    
    candidate_res = (
        supabase.table("candidates")
        .select("*")
        .eq("id", payload.candidate_id)
        .single()
        .execute()
    )

    candidate_data = candidate_res.data

    vacancy_id = candidate_data.get("vacancy_id")

    if not vacancy_id:
        return {
            "completed": True,
            "error": "Candidate is not linked to any vacancy"
        }



    vacancy_res = (
        supabase.table("vacancies")
        .select("*")
        .eq("id", vacancy_id)
        .single()
        .execute()
    )

    vacancy_data = vacancy_res.data


    # 4️⃣ Generate next question (GPT-5-mini SAFE)
    prompt = f"""

You are a senior human interviewer conducting a REAL hiring interview.

━━━━━━━━━━━━━━━━━━━━━━
INTERVIEW CONTEXT
━━━━━━━━━━━━━━━━━━━━━━
Job Role: {vacancy_data['job_role']}
Experience Level Target: {vacancy_data['experience_level']}
Required Skills: {', '.join(vacancy_data['required_skills'])}
Job Description:
{vacancy_data.get('description', 'N/A')}

Candidate Resume:
{candidate_data.get('resume_text', '')}

━━━━━━━━━━━━━━━━━━━━━━
INTERVIEW STATE
━━━━━━━━━━━━━━━━━━━━━━
Current Question Number: {question_count + 1}
IMPORTANT:
You MUST include the question number in the final question text.
Format STRICTLY like this:
"Question {question_count + 1}: <question text>"
Previous Answer (if any):
{last_answer}

Previously Asked Questions:
{[t['question'] for t in transcript]}

━━━━━━━━━━━━━━━━━━━━━━
CRITICAL INTERVIEW RULES (NON-NEGOTIABLE)
━━━━━━━━━━━━━━━━━━━━━━

1️⃣ ASK EXACTLY ONE QUESTION.
   - No explanations
   - No commentary
   - No formatting

2️⃣ NEVER repeat:
   - A previously asked question
   - The same project, example, or scenario twice
   - The same skill focus twice in a row

3️⃣ TOPIC ROTATION (MANDATORY)
   You MUST rotate topics across questions.
   Choose ONE topic per question from the list below, ensuring diversity:

   • Resume project deep-dive
   • Core skill verification
   • Real-world problem solving
   • Decision making & trade-offs
   • Debugging / failure handling
   • System or design thinking (role-appropriate)
   • Ownership & responsibility
   • Communication & clarity
   • Culture & teamwork (lightweight)

   ❗ If the last question was about a project, the next question MUST NOT be about the same project.

4️⃣ ADAPT BASED ON LAST ANSWER (MANDATORY)
   - If last answer was strong:
     → Increase difficulty, add constraints, edge cases, or scale
   - If last answer was weak or vague:
     → Narrow scope, probe fundamentals, or ask for clarification
   - If last answer avoided the question:
     → Ask a more concrete, scenario-based follow-up

5️⃣ QUESTION QUALITY RULES
   - Prefer “How did you…”, “Why did you choose…”, “What would you do if…”
   - Prefer scenario-based and experience-driven questions
   - Avoid theory-only or textbook questions
   - Avoid generic HR questions

6️⃣ INTERVIEW FLOW (HUMAN-LIKE)
   - Early questions → verify resume claims & fundamentals
   - Middle questions → real work, problem solving, decisions
   - Later questions → ownership, failure, judgment, impact

7️⃣ INTERVIEW LENGTH
   - The interview has NO fixed number of questions.
   - Continue naturally until stopped externally.

━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (STRICT)
━━━━━━━━━━━━━━━━━━━━━━
Return ONLY the interview question.
No markdown.


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
    
    candidate_res = (
        supabase.table("candidates")
        .select("*")
        .eq("id", payload.candidate_id)
        .single()
        .execute()
    )

    candidate_data = candidate_res.data


    vacancy_id = candidate_data.get("vacancy_id")

    if not vacancy_id:
        raise HTTPException(
            status_code=400,
            detail="Candidate is not linked to any vacancy"
        )


    vacancy_res = (
        supabase.table("vacancies")
        .select("*")
        .eq("id", vacancy_id)
        .single()
        .execute()
    )

    vacancy_data = vacancy_res.data

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
        "started_at": session.get("started_at") or session["scheduled_at"],

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

    supabase.table("ai_interview_sessions").update({
        "is_active": False
    }).eq("candidate_id", payload.candidate_id).execute()

    # 5️⃣ Auto-Calendly
    if evaluation["overall_score"] >= 80:
        try:
            email_service.send_final_interview_schedule(
                payload.candidate_id,
                candidate["email"],
                candidate["name"]
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
