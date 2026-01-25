import json
from typing import Dict, List, Any
from datetime import datetime

from config import config
from database import supabase
from services.email_service import email_service

# =========================
# AI CLIENT IMPORTS
# =========================
try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    openai_available = False

try:
    from anthropic import Anthropic
    anthropic_available = True
except ImportError:
    anthropic_available = False


class AIService:
    def __init__(self):
        self.provider = config.AI_PROVIDER
        self.model = config.AI_MODEL

        if self.provider == "openai" and openai_available:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        elif self.provider == "anthropic" and anthropic_available:
            self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        else:
            self.client = None

    # =====================================================
    # 🔥 GPT-5 / GPT-5-mini SAFE COMPLETION METHOD
    # =====================================================
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1500
    ) -> str:
        if not self.client:
            raise RuntimeError("❌ AI client not configured")

        try:
            # =========================
            # OPENAI (GPT-5-mini)
            # =========================
            if self.provider == "openai":
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
                    if item.get("type") == "message":
                        for content in item.get("content", []):
                            if content.get("type") == "output_text":
                                output_text += content.get("text", "")

                # 🔥 EMPTY OUTPUT GUARD (CRITICAL FIX)
                if not output_text or not output_text.strip():
                    raise RuntimeError("❌ GPT returned EMPTY response")

                return output_text.strip()

            # =========================
            # ANTHROPIC (CLAUDE)
            # =========================
            elif self.provider == "anthropic":
                system_message = ""
                user_messages = []

                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        user_messages.append(msg)

                response = self.client.messages.create(
                    model=self.model if "claude" in self.model else "claude-3-sonnet-20240229",
                    max_tokens=max_tokens,
                    system=system_message,
                    messages=user_messages
                )

                content = response.content[0].text

                if not content or not content.strip():
                    raise RuntimeError("❌ Claude returned EMPTY response")

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
You are an expert HR recruiter. Analyze the following resume against the job requirements.

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
                raise RuntimeError("❌ Invalid JSON returned by AI")
            response_data = json.loads(response_text[start:end])

        # =========================
        # UPDATE CANDIDATE RECORD
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
        # 🔥 AUTO SEND GOOGLE FORM (RULE 1)
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
