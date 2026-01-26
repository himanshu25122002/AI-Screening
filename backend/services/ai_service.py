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
    def generate_completion(self, prompt: str, max_tokens: int = 1500) -> str:
        if not self.client:
            raise RuntimeError("AI client not configured")

        try:
        # GPT-5 / GPT-5-mini compatible
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            text = response.choices[0].message.content

            if not text or not text.strip():
                raise RuntimeError("Empty response from AI")

            return text.strip()

        except Exception as e:
            print("❌ OPENAI ERROR:", e)
            raise

    import re
   

    def extract_email_regex(self, text: str) -> str | None:
        if not text:
            return None

        matches = re.findall(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            text
        )

        return matches[0] if matches else None


    def extract_email_ai(self, resume_text: str) -> str | None:
        """
        Uses AI ONLY if regex-style email is missing.
        Returns verified email or None.
        """

        if not resume_text or len(resume_text.strip()) < 30:
             return None

        prompt = f"""
    Extract the candidate's EMAIL ADDRESS from the resume text below.

    Rules:
    - Return ONLY the email address
    - If email is written like (name at gmail dot com), convert it to real email
    - If no clear email is present, return NONE
    - Do NOT guess
    - Do NOT invent

    Resume:
    {resume_text}
    """

        try:
            response = self.generate_completion(prompt).strip()

            if response.lower() == "none":
                return None

        # 🔐 Final regex validation (critical)
            match = re.search(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", response)
            return match.group(0) if match else None

        except Exception as e:
            print("❌ AI email extraction failed:", e)
            return None

    def extract_email(self, resume_text: str) -> str | None:
       email = self.extract_email_regex(resume_text)
       if email:
           return email
       return self.extract_email_ai(resume_text)


    
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
        


        resume_text = candidate_data.get("resume_text", "")
        current_email = candidate_data.get("email", "")

        extracted_email = self.extract_email(resume_text)

        if extracted_email and current_email.endswith("@resume.local"):
            print("✅ Updating candidate email:", extracted_email)

            supabase.table("candidates").update({
                "email": extracted_email,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", candidate_id).execute()

   
            candidate_data["email"] = extracted_email





        prompt = f"""
    Analyze this resume as an expert HR and return STRICT JSON ONLY.

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
        response_text = self.generate_completion(prompt)
           

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


    # == =======================
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
        return data

ai_service = AIService()










