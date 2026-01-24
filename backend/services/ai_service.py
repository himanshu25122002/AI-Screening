import json
from typing import Dict, List, Any
from config import config
from database import supabase
from datetime import datetime

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
Required Skills: {', '.join(vacancy_data['required_skills'])}
Experience Level: {vacancy_data['experience_level']}
Culture Traits: {', '.join(vacancy_data['culture_traits'])}

Resume:
{candidate_data.get('resume_text', 'No resume text available')}

Please provide:
1. A screening score from 0-100
2. Extracted skills from the resume
3. Years of experience (estimate if not explicitly stated)
4. Detailed screening notes explaining the score

Respond in JSON format:
{{
  "screening_score": <number>,
  "extracted_skills": [<list of skills>],
  "experience_years": <number>,
  "screening_notes": "<detailed analysis>"
}}
"""

        messages = [
            {"role": "system", "content": "You are an expert HR recruiter analyzing resumes."},
            {"role": "user", "content": prompt}
        ]

        response_text = self.generate_completion(messages, max_tokens=1500)

        try:
            response_data = json.loads(response_text)
        except:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                response_data = json.loads(response_text[start_idx:end_idx])
            else:
                response_data = {
                    "screening_score": 50,
                    "extracted_skills": [],
                    "experience_years": 0,
                    "screening_notes": "Unable to parse AI response"
                }

        supabase.table("candidates").update({
            "screening_score": response_data["screening_score"],
            "screening_notes": response_data["screening_notes"],
            "skills": response_data["extracted_skills"],
            "experience_years": response_data["experience_years"],
            "status": "screened",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", candidate_id).execute()

        return response_data

    def conduct_interview(self, candidate_id: str, vacancy_id: str,
                         candidate_responses: List[Dict[str, str]] = None) -> Dict[str, Any]:
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

        form_data = supabase.table("candidate_forms")\
            .select("*")\
            .eq("candidate_id", candidate_id)\
            .maybeSingle()\
            .execute()

        candidate_data = candidate.data
        vacancy_data = vacancy.data
        form_data_content = form_data.data if form_data.data else {}

        if not candidate_responses:
            interview_questions = self._generate_interview_questions(candidate_data, vacancy_data, form_data_content)
            return {"questions": interview_questions, "interview_started": True}

        evaluation = self._evaluate_interview(candidate_data, vacancy_data, form_data_content, candidate_responses)

        interview_record = {
            "candidate_id": candidate_id,
            "vacancy_id": vacancy_id,
            "interview_transcript": candidate_responses,
            "duration_minutes": 20,
            "skill_score": evaluation["skill_score"],
            "communication_score": evaluation["communication_score"],
            "problem_solving_score": evaluation["problem_solving_score"],
            "culture_fit_score": evaluation["culture_fit_score"],
            "overall_score": evaluation["overall_score"],
            "recommendation": evaluation["recommendation"],
            "evaluation_notes": evaluation["evaluation_notes"],
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("ai_interviews").insert(interview_record).execute()

        supabase.table("candidates").update({
            "status": "interviewed",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", candidate_id).execute()

        return {
            "interview_id": result.data[0]["id"],
            **evaluation
        }

    def _generate_interview_questions(self, candidate_data: Dict, vacancy_data: Dict,
                                     form_data: Dict) -> List[str]:
        prompt = f"""
Generate 5-7 tailored interview questions for a candidate applying for {vacancy_data['job_role']}.

Candidate Background:
- Skills: {', '.join(candidate_data.get('skills', []))}
- Experience: {candidate_data.get('experience_years', 'Not specified')} years
- Resume highlights: {candidate_data.get('screening_notes', 'N/A')[:200]}

Job Requirements:
- Required skills: {', '.join(vacancy_data['required_skills'])}
- Experience level: {vacancy_data['experience_level']}
- Culture traits: {', '.join(vacancy_data['culture_traits'])}

Generate questions that assess:
1. Technical skills and experience
2. Problem-solving abilities
3. Communication skills
4. Culture fit

Return only the questions as a JSON array: ["question1", "question2", ...]
"""

        messages = [
            {"role": "system", "content": "You are an expert interviewer."},
            {"role": "user", "content": prompt}
        ]

        response = self.generate_completion(messages, max_tokens=800)

        try:
            questions = json.loads(response)
            if isinstance(questions, list):
                return questions
        except:
            pass

        return [
            f"Tell me about your experience with {vacancy_data['required_skills'][0] if vacancy_data['required_skills'] else 'the required technologies'}.",
            "Describe a challenging project you worked on and how you overcame obstacles.",
            "How do you stay updated with industry trends and new technologies?",
            f"Why are you interested in the {vacancy_data['job_role']} position at Futuready?",
            "Describe your ideal work environment and team culture."
        ]

    def _evaluate_interview(self, candidate_data: Dict, vacancy_data: Dict,
                          form_data: Dict, responses: List[Dict[str, str]]) -> Dict[str, Any]:
        transcript = "\n\n".join([
            f"Q: {r.get('question', '')}\nA: {r.get('answer', '')}"
            for r in responses
        ])

        prompt = f"""
Evaluate this candidate interview for the position: {vacancy_data['job_role']}

Candidate Background:
- Skills: {', '.join(candidate_data.get('skills', []))}
- Experience: {candidate_data.get('experience_years', 0)} years
- Screening Score: {candidate_data.get('screening_score', 0)}/100

Job Requirements:
- Required skills: {', '.join(vacancy_data['required_skills'])}
- Experience level: {vacancy_data['experience_level']}
- Culture traits: {', '.join(vacancy_data['culture_traits'])}

Interview Transcript:
{transcript}

Provide a comprehensive evaluation with scores (0-100) for:
1. Skill Fit - Technical knowledge and experience alignment
2. Communication - Clarity, articulation, and professionalism
3. Problem Solving - Analytical thinking and approach to challenges
4. Culture Fit - Alignment with company values and work style

Also provide:
- Overall Score (weighted average)
- Recommendation: "Strong Fit", "Moderate Fit", or "Not Recommended"
- Detailed evaluation notes

Respond in JSON format:
{{
  "skill_score": <number>,
  "communication_score": <number>,
  "problem_solving_score": <number>,
  "culture_fit_score": <number>,
  "overall_score": <number>,
  "recommendation": "<Strong Fit|Moderate Fit|Not Recommended>",
  "evaluation_notes": "<detailed analysis>"
}}
"""

        messages = [
            {"role": "system", "content": "You are an expert HR evaluator."},
            {"role": "user", "content": prompt}
        ]

        response_text = self.generate_completion(messages, max_tokens=1500)

        try:
            evaluation = json.loads(response_text)
        except:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                evaluation = json.loads(response_text[start_idx:end_idx])
            else:
                evaluation = {
                    "skill_score": 70,
                    "communication_score": 70,
                    "problem_solving_score": 70,
                    "culture_fit_score": 70,
                    "overall_score": 70,
                    "recommendation": "Moderate Fit",
                    "evaluation_notes": "Unable to parse AI evaluation"
                }

        return evaluation

ai_service = AIService()
