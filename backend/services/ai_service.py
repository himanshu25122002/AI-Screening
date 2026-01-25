import json
from typing import Dict, List, Any
from datetime import datetime

from config import config
from database import supabase
from services.email_service import email_service

# =========================
# AI CLIENT IMPORT
# =========================
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class AIService:
    def __init__(self):
        self.provider = config.AI_PROVIDER
        self.model = config.AI_MODEL

        if self.provider == "openai" and OpenAI:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        else:
            self.client = None

    # =====================================================
    # 🔥 RENDER-SAFE GPT-5 / GPT-5-MINI COMPLETION
    # =====================================================
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1500
    ) -> str:
        if not self.client:
            raise RuntimeError("❌ OpenAI client not configured")

        try:
            response = self.client.chat.completions.create(
                model=self.model,               # gpt-5-mini
                messages=messages,
                max_completion_tokens=max_tokens,
                temperature=0.3
            )

            content = response.choices[0].message.content

            # 🔥 EMPTY OUTPUT GUARD (CRITICAL)
            if not content or not content.strip():
                raise RuntimeError("❌ GPT returned EMPTY response")

            return content.strip()

        except Exception as e:
            print("❌ AI COMPLETION FAILED:", str(e))
            raise RuntimeError(f"AI generation failed: {e}")

    # =====================================================
    # 🧠 RESUME SCREENING
    # =====================================================
    def screen_resume(self, candidate_id: str, vacancy_id: str) -> Dict[str, Any]:
        # 🔍 Fetch candidate & vacancy
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

        print("🔥 SCREENING STARTED:", candidate_id)

        prompt = f"""
You are an expert HR recruiter.

Analyze the candidate resume against the job requirements.

Job Role: {vacancy_data['job_role']}
Experience Level: {vacancy_data['experience_level']}

Required Skills:
{', '.join(vacancy_data['required_skills'])}

Culture Traits:
{', '.join(vacancy_data['culture_traits'])}

Job Description:
{vacancy_data.get('description', 'Not provided')}

Candidate Resume:
{candidate_data.get('resume_text', 'No resume text available')}

Return STRICT JSON ONLY:
{{
  "screening_score": 0,
  "extracted_skills": [],
  "experience_years": 0,
  "screening_notes": ""
}}
"""

        messages = [
            {"role": "system", "content": "You are an expert HR recruiter."},
            {"role": "user", "content": prompt}
        ]

        response_text = self.generate_completion(messages)

        # =========================
        # SAFE JSON PARSING
        # =========================
        try:
            response_data = json.loads(response_text)
        except Exception:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start == -1 or end == -1:
                raise RuntimeError("❌ Invalid JSON returned by GPT")
            response_data = json.loads(response_text[start:end])

        # =========================
        # UPDATE CANDIDATE
        # =========================
        supabase.table("candidates").update({
            "screening_score": response_data["screening_score"],
            "screening_notes": response_data["screening_notes"],
            "skills": response_data["extracted_skills"],
            "experience_years": response_data["experience_years"],
            "status": "screened",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", candidate_id).execute()

        # =========================
        # 🔥 AUTO SEND GOOGLE FORM (SCORE ≥ 90)
        # =========================
        if (
            response_data["screening_score"] >= 90
            and candidate_data.get("status") != "form_sent"
        ):
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

        return response_data


ai_service = AIService()

