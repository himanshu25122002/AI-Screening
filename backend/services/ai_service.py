import json
from typing import Dict, List, Any
from datetime import datetime
import re
from backend.config import config
from backend.database import supabase
from backend.services.email_service import email_service


from openai import OpenAI


class AIService:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.AI_MODEL  

   
    def generate_completion(self, prompt: str, max_tokens: int = 1500) -> str:
        if not self.client:
            raise RuntimeError("AI client not configured")

        try:
        
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



    def extract_email_regex(self, text: str) -> str | None:
        if not text:
            return None

        matches = re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            text
        )

        for email in matches:
            local = email.split("@")[0]
        
            if any(c.isalpha() for c in local):
                return email

        return None





    def extract_email_ai(self, resume_text: str) -> str | None:
        """
        Uses AI ONLY if regex-style email is missing.
        Returns verified email or None.
        """

        if not resume_text or len(resume_text.strip()) < 30:
             return None

        

        prompt = f"""
You are an automated resume parsing system used by enterprise ATS platforms.

Your task is to extract the candidate’s EMAIL ADDRESS from the resume text.

━━━━━━━━━━━━━━━━━━━━━━
STRICT EXTRACTION RULES
━━━━━━━━━━━━━━━━━━━━━━

1. Extract ONLY an email address that is explicitly present in the resume text.
2. If the email is obfuscated, normalize it:
   - Examples:
     - "name at gmail dot com" → name@gmail.com
     - "name [at] domain [dot] com" → name@domain.com
3. Do NOT infer, guess, modify, shorten, or reconstruct an email.
4. Do NOT generate an email from the candidate’s name.
5. If multiple emails are present, return the most complete and professional-looking one.
6. If no valid email is clearly found, return EXACTLY:
   NONE

━━━━━━━━━━━━━━━━━━━━━━
OUTPUT RULES (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━

- Return ONLY the email address or the word NONE
- No explanations
- No extra text
- No punctuation
- No formatting

━━━━━━━━━━━━━━━━━━━━━━
RESUME TEXT
━━━━━━━━━━━━━━━━━━━━━━

{resume_text}

        """

        try:
            response = self.generate_completion(prompt).strip()

            if response.lower() == "none":
                return None

        # 🔐 Final regex validation (critical)
            match = re.search(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", response)
            return match.group(0) if match else None

        except Exception as e:
            print("❌ AI email extraction failed:", e)
            return None



    def repair_email_ai(self, resume_text: str, extracted_email: str | None) -> str | None:

        prompt = f"""
You are a production-grade ATS email correction engine.

TASK:
You are given resume text and a possibly incorrect email.
Your job is to return the CORRECT candidate email IF AND ONLY IF it is
explicitly present in the resume text but broken due to spacing or OCR.

ALLOWED OPERATIONS:
- Join split username parts (letters + digits)
- Join numeric fragments with username
- Remove spaces between username fragments
- Fix line breaks inside an email

FORBIDDEN:
- Do NOT invent a new email
- Do NOT change domain
- Do NOT guess usernames
- Do NOT modify letters order
- Do NOT create email if not present

RULE:
If the correct email cannot be reconstructed with certainty,
return EXACTLY:
NONE

OUTPUT:
Return ONLY the email or NONE.

RESUME TEXT:
{resume_text}

CURRENT EMAIL:
{extracted_email or "NONE"}
        """

        try:
            response = self.generate_completion(prompt).strip()

            if response.lower() == "none":
                return None

        
            if re.match(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                response
            ):
                return response

            return None

        except Exception as e:
            print("❌ AI email repair failed:", e)
            return None

    def extract_email(self, resume_text: str) -> str | None:
        if not resume_text:
            return None

        regex_matches = re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            resume_text
        )

        regex_email = regex_matches[0] if regex_matches else None

        repaired_email = self.repair_email_ai(resume_text, regex_email)

        if repaired_email:
            return repaired_email

        if regex_email:
            local = regex_email.split("@")[0]
            if not local.isdigit():
                return regex_email

        return None






    def extract_name_regex(self, text: str) -> str | None:
        if not text:
            return None

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        top_lines = lines[:5]  # names almost always appear here

        for line in top_lines:
            if any(x in line.lower() for x in [
                "resume", "curriculum", "cv", "email", "@", "phone",
                "linkedin", "github", "profile"
            ]):
                continue

            if re.match(r"^[A-Za-z]+(?:\s[A-Za-z]+){1,3}$", line):
                return line

        return None


    def extract_name_ai(self, resume_text: str) -> str | None:

        if not resume_text or len(resume_text.strip()) < 30:
            return None

        prompt = f"""
You are an automated resume parsing system used by enterprise ATS platforms.

Your task is to extract the candidate’s FULL NAME from the resume text.

━━━━━━━━━━━━━━━━━━━━━━
STRICT EXTRACTION RULES
━━━━━━━━━━━━━━━━━━━━━━
1. Extract ONLY the candidate's name explicitly written in the resume.
2. The name is usually at the top of the resume.
3. Do NOT infer or guess a name.
4. Do NOT extract usernames, emails, or profile handles.
5. Do NOT include titles (Mr, Ms, Dr, Eng, etc).
6. Do NOT include extra words or formatting.
7. If multiple names exist, return the most prominent candidate name.
8. If no clear candidate name is found, return EXACTLY:
NONE

━━━━━━━━━━━━━━━━━━━━━━
OUTPUT RULES (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━
- Return ONLY the full name or NONE
- No explanations
- No punctuation
- No formatting

━━━━━━━━━━━━━━━━━━━━━━
RESUME TEXT
━━━━━━━━━━━━━━━━━━━━━━
{resume_text}
    """

        try:
            response = self.generate_completion(prompt).strip()

            if response.lower() == "none":
                return None
           
            clean = response.strip()
            if any(x in clean.lower() for x in [
                "engineer", "developer", "resume", "cv",
                "linkedin", "github", "@", "|"
            ]):
                return None

            if re.match(r"^[A-Za-z]+(?:\s[A-Za-z]+){1,3}$", clean):
                return clean.title()

            return None


        except Exception as e:
            print("❌ AI name extraction failed:", e)
            return None

    
    def extract_name(self, resume_text: str) -> str | None:
        name = self.extract_name_regex(resume_text)
        if name:
            return name
        return self.extract_name_ai(resume_text)




    def is_valid_email_context(self, text: str, email: str) -> bool:

        if not text or not email:
            return False

        for match in re.finditer(re.escape(email), text):
            start, end = match.start(), match.end()

            before = text[start - 1] if start > 0 else " "
            after = text[end] if end < len(text) else " "

            if before.isalnum() or after.isalnum():
                return False

            local = email.split("@")[0]
            if local.isdigit():
                return False

            return True

        return False


    def is_corrupted_email(self, resume_text: str, email: str) -> bool:
        return not self.is_valid_email_context(resume_text, email)

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


        if extracted_email and (
            not current_email
            or self.is_corrupted_email(resume_text, current_email)
        ):
            print("✅ Correcting candidate email:", extracted_email)

            supabase.table("candidates").update({
                "email": extracted_email,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", candidate_id).execute()

            candidate_data["email"] = extracted_email


        

        PLACEHOLDER_NAMES = {"candidate", "unknown", ""}

        current_name_raw = candidate_data.get("name") or ""
        current_name = current_name_raw.strip().lower()

        extracted_name = self.extract_name(resume_text)

        if extracted_name and current_name in PLACEHOLDER_NAMES:
            print("✅ Updating candidate name:", extracted_name)

            supabase.table("candidates").update({
                "name": extracted_name,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", candidate_id).execute()

            candidate_data["name"] = extracted_name


        prompt = f"""
  
You are a production-grade ATS scoring engine used by modern hiring platforms.
Your task is to evaluate resume-to-job fit realistically and FAIRLY.

━━━━━━━━━━━━━━━━━━━━━━
JOB CONTEXT
━━━━━━━━━━━━━━━━━━━━━━
Job Role: {vacancy_data['job_role']}
Experience Level Target: {vacancy_data['experience_level']}
Required Skills (primary): {', '.join(vacancy_data['required_skills'])}
Culture Traits (low weight): {', '.join(vacancy_data['culture_traits'])}
Job Description:
{vacancy_data.get('description', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━
RESUME TEXT
━━━━━━━━━━━━━━━━━━━━━━
{candidate_data.get('resume_text', '')}

━━━━━━━━━━━━━━━━━━━━━━
EXPERIENCE CALCULATION (STRICT BUT FAIR)
━━━━━━━━━━━━━━━━━━━━━━
- Count ONLY professional work experience:
  jobs, internships, freelancing, contracts
- DO NOT count:
  education duration, academic projects, courses, certifications
- Experience must be supported by role + company + dates
- If dates overlap → count once
- Round DOWN to nearest 0.5 year
- If no valid experience → experience_years = 0

━━━━━━━━━━━━━━━━━━━━━━
SKILL EXTRACTION RULES
━━━━━━━━━━━━━━━━━━━━━━
- Extract ONLY skills explicitly written in the resume
- Do NOT infer or hallucinate
- Do NOT penalize missing secondary or optional skills
- Required skill match is considered GOOD if ≥70%

━━━━━━━━━━━━━━━━━━━━━━
SCORING PHILOSOPHY (VERY IMPORTANT)
━━━━━━━━━━━━━━━━━━━━━━
This system is calibrated so that:

▶ A DECENT, RELEVANT resume SHOULD score **90+**
▶ 90 is NOT exceptional — it is the NORMAL shortlist score
▶ Scores below 90 should be used ONLY when there are clear gaps



DO NOT deduct for:
- Minor keyword differences
- Non-critical skill gaps
- Imperfect job title wording
- Resume formatting or writing style

━━━━━━━━━━━━━━━━━━━━━━
SCORE INTERPRETATION
━━━━━━━━━━━━━━━━━━━━━━
- 90–100 → Strong match, shortlist-ready
- 80–89 → Good profile, minor gaps
- 65–79 → Partial match
- <65 → Weak or unrelated

━━━━━━━━━━━━━━━━━━━━━━
FINAL VERIFICATION (SILENT)
━━━━━━━━━━━━━━━━━━━━━━
Before responding:
- Ensure experience_years excludes education
- Ensure extracted_skills appear verbatim in resume
- Ensure score reflects REAL hiring behavior

━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (STRICT JSON ONLY)
━━━━━━━━━━━━━━━━━━━━━━
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
        resume_cutoff = vacancy_data.get("resume_cutoff_score") or 80

        if screening_score >= resume_cutoff:
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













































