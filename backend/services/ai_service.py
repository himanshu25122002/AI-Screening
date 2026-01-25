import json
from typing import Dict, List, Any
from datetime import datetime

from config import config
from database import supabase
from services.email_service import email_service

from openai import OpenAI


class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.AI_MODEL  # gpt-5-mini

    # ================================
    # 🔥 SAFE COMPLETION (RENDER SAFE)
    # ================================
    def generate_completion(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert HR recruiter."},
                    {"role": "user", "content": prompt}
                ],
                
            )

            content = response.choices[0].message.content

            if not content or not content.strip():
                raise RuntimeError("Empty AI response")

            return content.strip()

        except Exception as e:
            print("❌ OPENAI ERROR:", str(e))
            raise

    # ================================
    # 🧠 RESUME SCREENING (FIXED)
    # ================================
    def screen_resume(self, candidate_id: str, vacancy_id: str) -> Dict[str, Any]:
        print("🔥 SCREENING STARTED:", candidate_id)

        candidate = (
            supabase.table("candidates")
            .select("*")
            .eq("id", candidate_id)
            .single()
            .execute()
        )
        vacancy = (
            supabase.table("vacancies")
            .select("*")
            .eq("id", vacancy_id)
            .single()
            .execute()
        )

        candidate_data = candidate.data
        vacancy_data = vacancy.data

        prompt = f"""
    Analyze this resume and return STRICT JSON ONLY.

    Job Role: {vacancy_data['job_role']}
    Experience Level: {vacancy_data['experience_level']}
    Required Skills: {', '.join(vacancy_data['required_skills'])}
    Culture Traits: {', '.join(vacancy_data['culture_traits'])}
    Job Description: {vacancy_data.get('description', 'N/A')}

    Resume:
    {candidate_data.get('resume_text', '')}

    Return ONLY this JSON:
    {{
      "screening_score": 0,
      "extracted_skills": [],
      "experience_years": 0,
      "screening_notes": ""
    }}
    """

    # ✅ CORRECT generate_completion CALL
        response_text = self.generate_completion(
            messages=[
                {"role": "system", "content": "You are an expert HR recruiter."},
                {"role": "user", "content": prompt}
            ]
        )

    # =========================
    # SAFE JSON PARSING
    # =========================
        try:
            data = json.loads(response_text)
        except Exception:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            data = json.loads(response_text[start:end])

    # =========================
    # SAFE TYPE CASTING (CRITICAL)
    # =========================
        screening_score = int(float(data.get("screening_score", 0)))
        experience_years = int(float(data.get("experience_years", 0)))
        extracted_skills = data.get("extracted_skills", [])
        screening_notes = str(data.get("screening_notes", ""))

    # =========================
    # UPDATE CANDIDATE
    # =========================
        supabase.table("candidates").update({
            "screening_score": screening_score,
            "skills": extracted_skills,
            "experience_years": experience_years,
            "screening_notes": screening_notes,
            "status": "screened",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", candidate_id).execute()

    # =========================
    # AUTO SEND GOOGLE FORM
    # =========================
        if screening_score >= 90:
            email_service.send_form_invitation(
                candidate_id,
                candidate_data["email"],
                candidate_data["name"]
            )

            supabase.table("candidates").update({
                "status": "form_sent",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", candidate_id).execute()

        print("✅ SCREENING COMPLETED:", candidate_id)
        return {
            "screening_score": screening_score,
            "extracted_skills": extracted_skills,
            "experience_years": experience_years,
            "screening_notes": screening_notes
        }


ai_service = AIService()


