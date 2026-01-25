import json
from typing import Dict, List, Any
from config import config
from database import supabase
from datetime import datetime
from services.email_service import email_service

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
    # ✅ GPT-5 / GPT-5-mini COMPATIBLE GENERATION METHOD
    # =====================================================
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1500
    ) -> str:
        if not self.client:
            raise Exception("AI service not configured")

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
                    if item["type"] == "message":
                        for content in item["content"]:
                            if content["type"] == "output_text":
                                output_text += content["text"]

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
                return response.content[0].text

        except Exception as e:
            print("❌ AI generation error:", e)
            raise

    # =====================================================
    # RESUME SCREENING
    # =====================================================
    def screen_resume(self, candidate_id: str, vacancy_id: str) -> Dict[str, Any]:
        candidate = supabase.table("candidates")\
            .select("*")\
            .eq("id", candidate_id)\
            .single()\
            .execute()

        vacancy = supabase.table("vacancies")\
            .select("*")\
            .eq("id", vacancy_id)\
            .single()\
            .execute()

        candidate_data = candidate.data
        vacancy_data = vacancy.data

        prompt = f"""
You are an expert HR recruiter. Analyze the following resume against the job requirements and provide a detailed evaluation.

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

Please provide:
1. A screening score from 0-100
2. Extracted skills from the resume
3. Years of experience (estimate if not explicitly stated)
4. Detailed screening notes explaining the score

Respond in STRICT JSON format ONLY:
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

        response_text = self.generate_completion(messages, max_tokens=1500)

        # =========================
        # SAFE JSON PARSING
        # =========================
        try:
            response_data = json.loads(response_text)
        except Exception:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
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
        # AUTO SEND GOOGLE FORM
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

        return response_data


ai_service = AIService()
