from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

class VacancyCreate(BaseModel):
    job_role: str
    required_skills: List[str]
    experience_level: str
    culture_traits: List[str]
    description: Optional[str] = None
    created_by: str

class VacancyResponse(BaseModel):
    id: str
    job_role: str
    required_skills: List[str]
    experience_level: str
    culture_traits: List[str]
    description: Optional[str]
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime

class CandidateCreate(BaseModel):
    vacancy_id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_text: Optional[str] = None
    resume_url: Optional[str] = None

class CandidateResponse(BaseModel):
    id: str
    vacancy_id: str
    name: str
    email: str
    phone: Optional[str]
    skills: List[str]
    experience_years: Optional[float]
    screening_score: Optional[float]
    screening_notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

class ResumeScreeningRequest(BaseModel):
    candidate_id: str

class ResumeScreeningResponse(BaseModel):
    candidate_id: str
    screening_score: float
    screening_notes: str
    extracted_skills: List[str]
    experience_years: float

class AIInterviewRequest(BaseModel):
    candidate_id: str
    vacancy_id: str

class AIInterviewResponse(BaseModel):
    interview_id: str
    candidate_id: str
    overall_score: float
    recommendation: str
    skill_score: float
    communication_score: float
    problem_solving_score: float
    culture_fit_score: float
    evaluation_notes: str

class FinalInterviewSchedule(BaseModel):
    candidate_id: str
    vacancy_id: str
    scheduled_date: datetime
    location: str
    interviewer_names: List[str]
    meeting_link: Optional[str] = None
    notes: Optional[str] = None

class EmailRequest(BaseModel):
    candidate_id: str
    email_type: str

class GoogleFormSyncRequest(BaseModel):
    sheet_id: Optional[str] = None
