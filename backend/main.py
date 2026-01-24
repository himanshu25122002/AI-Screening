from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime

from models import (
    VacancyCreate, VacancyResponse, CandidateCreate, CandidateResponse,
    ResumeScreeningRequest, ResumeScreeningResponse, AIInterviewRequest,
    AIInterviewResponse, FinalInterviewSchedule, EmailRequest, GoogleFormSyncRequest
)
from database import supabase
from services.ai_service import ai_service
from services.email_service import email_service
from services.google_sheets_service import google_sheets_service
from services.resume_parser import resume_parser
from config import config
from ai_interview import router as interview_router
app.include_router(interview_router)

app = FastAPI(title="AI Candidate Screening API", version="1.0.0")
app.include_router(interview_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "message": "AI Candidate Screening API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/vacancies", response_model=dict)
def create_vacancy(vacancy: VacancyCreate):
    try:
        result = supabase.table("vacancies").insert({
            "job_role": vacancy.job_role,
            "required_skills": vacancy.required_skills,
            "experience_level": vacancy.experience_level,
            "culture_traits": vacancy.culture_traits,
            "description": vacancy.description,
            "created_by": vacancy.created_by,
            "status": "active"
        }).execute()

        return {"success": True, "data": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vacancies")
def list_vacancies(status: Optional[str] = None):
    try:
        query = supabase.table("vacancies").select("*").order("created_at", desc=True)

        if status:
            query = query.eq("status", status)

        result = query.execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vacancies/{vacancy_id}")
def get_vacancy(vacancy_id: str):
    try:
        result = supabase.table("vacancies").select("*").eq("id", vacancy_id).single().execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Vacancy not found")

@app.post("/candidates")
async def create_candidate(
    vacancy_id: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    resume: UploadFile = File(...)
):
    try:
        resume_content = await resume.read()

        if resume.filename.endswith('.pdf'):
            resume_text = resume_parser.parse_pdf(resume_content)
        else:
            resume_text = resume_parser.parse_text(resume_content)

        basic_info = resume_parser.extract_basic_info(resume_text)

        if not name:
            name = basic_info.get("name", "Unknown")
        if not email:
            email = basic_info.get("email", "")

        candidate_data = {
            "vacancy_id": vacancy_id,
            "name": name,
            "email": email,
            "phone": phone or basic_info.get("phone"),
            "resume_text": resume_text,
            "resume_url": f"uploads/{email}_{resume.filename}",
            "status": "new"
        }

        result = supabase.table("candidates").insert(candidate_data).execute()

        return {"success": True, "data": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/candidates")
def list_candidates(vacancy_id: Optional[str] = None, status: Optional[str] = None):
    try:
        query = supabase.table("candidates").select("*").order("created_at", desc=True)

        if vacancy_id:
            query = query.eq("vacancy_id", vacancy_id)
        if status:
            query = query.eq("status", status)

        result = query.execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str):
    try:
        candidate = supabase.table("candidates").select("*").eq("id", candidate_id).single().execute()

        form_data = supabase.table("candidate_forms")\
            .select("*")\
            .eq("candidate_id", candidate_id)\
            .maybeSingle()\
            .execute()

        interview_data = supabase.table("ai_interviews")\
            .select("*")\
            .eq("candidate_id", candidate_id)\
            .maybeSingle()\
            .execute()

        return {
            "success": True,
            "data": {
                "candidate": candidate.data,
                "form_data": form_data.data,
                "interview_data": interview_data.data
            }
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Candidate not found")

@app.post("/screening/resume")
def screen_resume(request: ResumeScreeningRequest):
    try:
        candidate = supabase.table("candidates")\
            .select("vacancy_id")\
            .eq("id", request.candidate_id)\
            .single()\
            .execute()

        result = ai_service.screen_resume(request.candidate_id, candidate.data["vacancy_id"])

        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/screening/batch")
def batch_screen_resumes(vacancy_id: str):
    try:
        candidates = supabase.table("candidates")\
            .select("id")\
            .eq("vacancy_id", vacancy_id)\
            .eq("status", "new")\
            .execute()

        results = []
        for candidate in candidates.data:
            try:
                result = ai_service.screen_resume(candidate["id"], vacancy_id)
                results.append({"candidate_id": candidate["id"], "success": True, "data": result})
            except Exception as e:
                results.append({"candidate_id": candidate["id"], "success": False, "error": str(e)})

        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interviews/start")
def start_interview(request: AIInterviewRequest):
    try:
        result = ai_service.conduct_interview(request.candidate_id, request.vacancy_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interviews/submit")
def submit_interview(candidate_id: str, vacancy_id: str, responses: List[dict]):
    try:
        result = ai_service.conduct_interview(candidate_id, vacancy_id, responses)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/interviews/{candidate_id}")
def get_interview(candidate_id: str):
    try:
        result = supabase.table("ai_interviews")\
            .select("*")\
            .eq("candidate_id", candidate_id)\
            .maybeSingle()\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Interview not found")

        return {"success": True, "data": result.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/final-interviews/schedule")
def schedule_final_interview(schedule: FinalInterviewSchedule):
    try:
        interview_data = {
            "candidate_id": schedule.candidate_id,
            "vacancy_id": schedule.vacancy_id,
            "scheduled_date": schedule.scheduled_date.isoformat(),
            "location": schedule.location,
            "interviewer_names": schedule.interviewer_names,
            "meeting_link": schedule.meeting_link,
            "notes": schedule.notes,
            "status": "scheduled"
        }

        result = supabase.table("final_interviews").insert(interview_data).execute()

        candidate = supabase.table("candidates")\
            .select("name, email")\
            .eq("id", schedule.candidate_id)\
            .single()\
            .execute()

        email_service.send_final_interview_schedule(
            schedule.candidate_id,
            candidate.data["email"],
            candidate.data["name"],
            schedule.scheduled_date.strftime("%B %d, %Y at %I:%M %p"),
            schedule.location,
            schedule.meeting_link
        )

        supabase.table("candidates").update({
            "status": "recommended",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", schedule.candidate_id).execute()

        return {"success": True, "data": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/final-interviews")
def list_final_interviews(vacancy_id: Optional[str] = None):
    try:
        query = supabase.table("final_interviews")\
            .select("*, candidates(*), vacancies(*)")\
            .order("scheduled_date", desc=False)

        if vacancy_id:
            query = query.eq("vacancy_id", vacancy_id)

        result = query.execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/emails/send")
def send_email(request: EmailRequest):
    try:
        candidate = supabase.table("candidates")\
            .select("name, email")\
            .eq("id", request.candidate_id)\
            .single()\
            .execute()

        candidate_data = candidate.data

        if request.email_type == "form_invite":
            result = email_service.send_form_invitation(
                request.candidate_id,
                candidate_data["email"],
                candidate_data["name"]
            )

            supabase.table("candidates").update({
                "status": "form_sent",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", request.candidate_id).execute()

        elif request.email_type == "interview_invite":
            interview_link = f"{config.FRONTEND_URL}/interview/{request.candidate_id}"
            result = email_service.send_interview_invitation(
                request.candidate_id,
                candidate_data["email"],
                candidate_data["name"],
                interview_link
            )

        elif request.email_type == "rejection":
            result = email_service.send_rejection_email(
                request.candidate_id,
                candidate_data["email"],
                candidate_data["name"]
            )

            supabase.table("candidates").update({
                "status": "rejected",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", request.candidate_id).execute()

        else:
            raise HTTPException(status_code=400, detail="Invalid email type")

        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/google-forms/sync")
def sync_google_forms(request: GoogleFormSyncRequest):
    try:
        result = google_sheets_service.sync_form_responses(request.sheet_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/vacancy/{vacancy_id}")
def get_vacancy_stats(vacancy_id: str):
    try:
        candidates = supabase.table("candidates")\
            .select("status")\
            .eq("vacancy_id", vacancy_id)\
            .execute()

        status_counts = {}
        for candidate in candidates.data:
            status = candidate["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        interviews = supabase.table("ai_interviews")\
            .select("recommendation")\
            .eq("vacancy_id", vacancy_id)\
            .execute()

        recommendation_counts = {}
        for interview in interviews.data:
            rec = interview["recommendation"]
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1

        return {
            "success": True,
            "data": {
                "total_candidates": len(candidates.data),
                "status_breakdown": status_counts,
                "recommendation_breakdown": recommendation_counts
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

