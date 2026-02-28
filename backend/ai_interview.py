from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import json
from zoneinfo import ZoneInfo
from openai import OpenAI

from backend.database import supabase
from backend.services.email_service import email_service
from backend.config import config
from backend.services.ai_service import ai_service

router = APIRouter()

client = OpenAI(api_key=config.OPENAI_API_KEY)




class InterviewPayload(BaseModel):
    candidate_id: str
    answer: str | None = None


class TokenPayload(BaseModel):
    token: str





@router.post("/ai-interview/validate")
def validate_interview(payload: TokenPayload):
    token = payload.token

    # 1️⃣ Fetch ONLY active session
    res = (
        supabase
        .table("ai_interview_sessions")
        .select("*")
        .eq("interview_token", token)
        .eq("is_active", True)   # 🔥 CRITICAL
        .single()
        .execute()
    )

    if not res.data:
        raise HTTPException(
            status_code=403,
            detail="Interview link is invalid or expired"
        )

    session = res.data

    # 2️⃣ Current time (UTC)
    now_utc = datetime.now(timezone.utc)

    # 3️⃣ Parse DB times → UTC AWARE
    scheduled_at_utc = datetime.fromisoformat(
        session["scheduled_at"].replace("Z", "+00:00")
    ).astimezone(timezone.utc)

    expires_at_utc = datetime.fromisoformat(
        session["expires_at"].replace("Z", "+00:00")
    ).astimezone(timezone.utc)

    # 4️⃣ BEFORE TIME
    if now_utc < scheduled_at_utc:
        raise HTTPException(
            status_code=403,
            detail="Interview has not started yet"
        )

    # 5️⃣ AFTER EXPIRY
    if now_utc > expires_at_utc:
        supabase.table("ai_interview_sessions").update({
            "is_active": False
        }).eq("id", session["id"]).execute()

        raise HTTPException(
            status_code=403,
            detail="Interview link has expired"
        )

    
    if not session.get("started_at"):

        now_utc = datetime.now(timezone.utc)

        vacancy_res = (
            supabase.table("vacancies")
            .select("interview_duration_minutes")
            .eq("id", session["vacancy_id"])
            .single()
            .execute()
        )

        duration = vacancy_res.data.get("interview_duration_minutes", 15)

        ends_at = now_utc + timedelta(minutes=duration)

        supabase.table("ai_interview_sessions").update({
            "started_at": now_utc.isoformat(),
            "ends_at": ends_at.isoformat()
        }).eq("id", session["id"]).execute()

        final_ends_at = ends_at.isoformat()

    else:
        final_ends_at = session.get("ends_at")

    return {
        "success": True,
        "candidate_id": session["candidate_id"],
        "ends_at": final_ends_at
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

    now_utc = datetime.now(timezone.utc)

    ends_at_str = session.get("ends_at")

    if ends_at_str:
        ends_at = datetime.fromisoformat(
            ends_at_str.replace("Z", "+00:00")
        )

        if now_utc >= ends_at and payload.answer is not None:
            return {
                "completed": True,
                "message": "Interview duration completed."
            }

    if session:
        question_count = session["question_count"]
        transcript = session.get("transcript", [])
    



    
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
    custom_prompt_block = ""

    if vacancy_data.get("interview_custom_prompt"):
        custom_prompt_block = f"""

━━━━━━━━━━━━━━━━━━━━━━
HR CUSTOM INTERVIEW INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━
{vacancy_data["interview_custom_prompt"]}

If HR provided mandatory questions,
you MUST ask them at some point during the interview.
You may adapt wording but must cover the intent.
    """
    prompt = f"""

You are a senior human interviewer conducting a REAL hiring interview.
{custom_prompt_block}
━━━━━━━━━━━━━━━━━━━━━━
INTERVIEW CONTEXT
━━━━━━━━━━━━━━━━━━━━━━
Job Role: {vacancy_data['job_role']}
Experience Level Target: {vacancy_data.get('experience_level', 'Not specified')}
Required Skills: {', '.join(vacancy_data.get('required_skills', [])) if vacancy_data.get('required_skills') else 'Not specified'}
Job Description:
{vacancy_data.get('description', 'N/A')}
Culture Traits: {', '.join(vacancy_data.get('culture_traits', [])) if vacancy_data.get('culture_traits') else 'Not specified'}
Candidate Resume:
{candidate_data.get('resume_text', 'Resume not available')}

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


INTERVIEW STYLE RULES

1. Ask simple, clear, human-friendly questions.
3. Avoid very long scenario descriptions.
4. Avoid multi-part questions.
5. Ask practical but moderate difficulty questions.
6. Keep tone natural and conversational.
7. Do not overcomplicate.

 NEVER repeat:
   - A previously asked question
   - The same project, example, or scenario twice
   - The same skill focus twice in a row

 TOPIC ROTATION (MANDATORY)
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

 ADAPT BASED ON LAST ANSWER (MANDATORY)
   - If last answer was strong:
     → Increase difficulty, add constraints, edge cases, or scale
   - If last answer was weak or vague:
     → Narrow scope, probe fundamentals, or ask for clarification
   - If last answer avoided the question:
     → Ask a more concrete, scenario-based follow-up

 QUESTION QUALITY RULES
   - Prefer “How did you…”, “Why did you choose…”, “What would you do if…”

 INTERVIEW FLOW (HUMAN-LIKE)
   - Early questions → verify resume claims & fundamentals
   - Middle questions → real work, problem solving, decisions
   - Later questions → ownership, failure, judgment, impact

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
        "current": question_count + 1
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

━━━━━━━━━━━━━━━━━━━━━━
JOB CONTEXT
━━━━━━━━━━━━━━━━━━━━━━
Role: {vacancy_data['job_role']}
Experience Level Target: {vacancy_data.get('experience_level', 'Not specified')}
Required Skills: {', '.join(vacancy_data.get('required_skills', [])) if vacancy_data.get('required_skills') else 'Not specified'}
Culture Traits: {', '.join(vacancy_data.get('culture_traits', [])) if vacancy_data.get('culture_traits') else 'Not specified'}
Job Description:
{vacancy_data.get('description', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━
CANDIDATE DATA
━━━━━━━━━━━━━━━━━━━━━━
Resume (BACKGROUND ONLY — NOT PROOF):
{candidate_data.get('resume_text', '')}

Interview Transcript (PRIMARY EVIDENCE):
{transcript_text}

━━━━━━━━━━━━━━━━━━━━━━
EVALUATION RULES (STRICT)
━━━━━━━━━━━━━━━━━━━━━━
1. Base scores PRIMARILY on interview answers.
2. Resume may be used ONLY to:
   - check consistency
   - validate claims made during interview
3. If a skill appears on resume but is NOT demonstrated → do NOT reward it.
4. Be fair and balanced.
5. Reward effort and clarity.
6. Do not overly penalize minor gaps.
7. Consider candidate potential.
8. Be practical, not harsh.
9. Avoid extreme scoring unless performance is clearly poor.

━━━━━━━━━━━━━━━━━━━━━━
SCORING SYSTEM (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━

Each category MUST be scored out of 25.

Categories:
- Skill (0–25)
- Communication (0–25)
- Problem Solving (0–25)
- Culture Fit (0–25)

⚠️ Hard Constraints:
- No category can exceed 25.
- No decimals.
- No negative values.

━━━━━━━━━━━━━━━━━━━━━━
OVERALL SCORE
━━━━━━━━━━━━━━━━━━━━━━

Overall Score MUST equal:

Skill + Communication + Problem Solving + Culture Fit

Overall Score MUST be out of 100.
It MUST be the exact mathematical sum.

━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDATION LOGIC
━━━━━━━━━━━━━━━━━━━━━━

80–100 → Strong Fit  
70–79  → Moderate Fit  
Below 70 → Not Recommended  

Do NOT mention numeric cutoffs in output.

━━━━━━━━━━━━━━━━━━━━━━
RETURN STRICT JSON ONLY
━━━━━━━━━━━━━━━━━━━━━━
Return JSON in this format:
{{
  "skill_score": <0-25>,
  "communication_score": <0-25>,
  "problem_solving_score": <0-25>,
  "culture_fit_score": <0-25>,
  "overall_score": <0-100>,
  "recommendation": "<Strong Fit | Moderate Fit | Not Recommended>",
  "evaluation_notes": "<3-5 sentence professional explanation>"
}}

    """

    raw = ai_service.generate_completion(eval_prompt)

    try:
        evaluation = json.loads(raw)
    except Exception:
        evaluation = {
            "skill_score": 15,
            "communication_score": 15,
            "problem_solving_score": 15,
            "culture_fit_score": 15,
            "overall_score": 60,
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
    interview_cutoff = vacancy_data.get("interview_cutoff_score") or 80
    if evaluation["overall_score"] >= interview_cutoff:
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
