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

    def generate_completion(self, messages: List[Dict[str, str]], max_tokens: int = 2000) -> str:
        if not self.client:
            return "AI service not configured"

        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7
                )
                return response.choices[0].message.content

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
            print(f"AI generation error: {e}")
            return f"Error: {str(e)}"

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

Respond in STRICT JSON format:
{{
  "screening_score": <number>,
  "extracted_skills": [<list of skills>],
  "experience_years": <number>,
  "screening_notes": "<detailed analysis>"
}}
"""



        messages = [
            {"role": "system", "content": "You are an expert HR recruiter."},
            {"role": "user", "content": prompt}
        ]

        response_text = self.generate_completion(messages, max_tokens=1500)

        try:
            response_data = json.loads(response_text)
        except:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            response_data = json.loads(response_text[start:end])

        # ✅ Update candidate after screening
        supabase.table("candidates").update({
            "screening_score": response_data["screening_score"],
            "screening_notes": response_data["screening_notes"],
            "skills": response_data["extracted_skills"],
            "experience_years": response_data["experience_years"],
            "status": "screened",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", candidate_id).execute()

        # 🔥 AUTO SEND GOOGLE FORM (RULE 1)
        if (
            response_data["screening_score"] > 90
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

    # 🔽 REST OF FILE UNCHANGED 🔽
    # conduct_interview(), _generate_interview_questions(), _evaluate_interview()
    # remain exactly the same (we will automate them next)


ai_service = AIService()

