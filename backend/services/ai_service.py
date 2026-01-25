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

    # =====================================================
    # GPT-5-mini SAFE GENERATION (RENDER-PROOF)
    # =====================================================
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1500
    ) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": messages[-1]["content"]
                            }
                        ]
                    }
                ],
                max_output_tokens=max_tokens
            )

            output_text = ""
            for item in response.output:
                if item["type"] == "message":
                    for content in item["content"]:
                        if content["type"] == "output_text":
                            output_text += content["text"]

            if not output_text.strip():
                raise RuntimeError("GPT returned empty output")

            return output_text.strip()

        except Exception as e:
            print("❌ AI COMPLETION FAILED:", e)
            raise RuntimeError(f"AI generation failed: {e}")

    # =====================================================
    # RESUME SCREENING
    # =====================================================
    def screen_resume(self, candidate_id: str, vacancy_id: str) -> Dict[str, Any]:
        print("🔥 SCREENING STARTED:", candidate_id)

        candidate = supabase.table("candidates").select("*").eq("id", candidate_id).single().execute()
        vacancy = supabase.table("vacancies").select("*").eq("id", vacancy_id).single().execute()
        candidate_data = candidate.data
        vacancy_data = vacancy.data
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

        response_text = self.generate_completion(
            [{"role": "user", "content": prompt}]
        )

        try:
            data = json.loads(response_text)
        except Exception:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start == -1 or end == -1:
                raise RuntimeError("Invalid JSON returned by AI")
            data = json.loads(response_text[start:end])

        supabase.table("candidates").update({
            "screening_score": data["screening_score"],
            "skills": data["extracted_skills"],
            "experience_years": data["experience_years"],
            "screening_notes": data["screening_notes"],
            "status": "screened",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", candidate_id).execute()

        if data["screening_score"] >= 90:
            email_service.send_form_invitation(
                candidate_id,
                candidate.data["email"],
                candidate.data["name"]
            )

            supabase.table("candidates").update({
                "status": "form_sent"
            }).eq("id", candidate_id).execute()

        print("✅ SCREENING COMPLETED:", candidate_id)
        return data


ai_service = AIService()

