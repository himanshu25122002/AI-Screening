from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field, validator

from backend.database import supabase
from backend.services.email_service import email_service

router = APIRouter()

# ================================
# Payload Schema (STRICT)
# ================================

class CandidateFormPayload(BaseModel):
    candidate_id: str

    # Personal Details
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)

    gender: str
    age: int = Field(..., ge=18, le=60)

    email: EmailStr
    phone: str = Field(..., pattern=r"^[0-9]{10,15}$")

    address: str
    city: str
    state: str

    # Professional Details
    years_of_experience: int = Field(..., ge=0)
    current_ctc: int = Field(..., ge=0)
    expected_ctc: int = Field(..., ge=0)
    notice_period: int = Field(..., ge=0)

    portfolio_link: Optional[str] = None

    @validator("gender")
    def validate_gender(cls, v):
        if v not in ["Male", "Female", "Other"]:
            raise ValueError("Invalid gender")
        return v

    @validator("portfolio_link")
    def validate_portfolio_link(cls, v):
        if v and not v.startswith("https://"):
            raise ValueError("Portfolio link must start with https://")
        return v


# ================================
# Submit Candidate Form
# ================================

@router.post("/candidate-form/submit")
def submit_candidate_form(payload: CandidateFormPayload):
    # --------------------------------
    # 1️⃣ Check candidate exists
    # --------------------------------
    candidate = (
        supabase
        .table("candidates")
        .select("id, email, name")
        .eq("id", payload.candidate_id)
        .single()
        .execute()
        .data
    )

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # --------------------------------
    # 2️⃣ Insert form (ONE per candidate)
    # --------------------------------
    try:
        supabase.table("candidate_forms").insert({
            "candidate_id": payload.candidate_id,

            "first_name": payload.first_name.strip(),
            "last_name": payload.last_name.strip(),

            "gender": payload.gender,
            "age": payload.age,

            "email": payload.email.lower(),
            "phone": payload.phone,

            "address": payload.address,
            "city": payload.city,
            "state": payload.state,

            "years_of_experience": payload.years_of_experience,
            "current_ctc": payload.current_ctc,
            "expected_ctc": payload.expected_ctc,
            "notice_period": payload.notice_period,

            "portfolio_link": payload.portfolio_link,
            "created_at": datetime.utcnow().isoformat(),
        }).execute()

    except Exception as e:
        # Most likely UNIQUE constraint violation
        raise HTTPException(
            status_code=400,
            detail="Candidate form already submitted"
        )

    
    email_service.send_schedule_interview_link(
        payload.candidate_id,
        candidate["email"],
        candidate["name"]
    )




    supabase.table("candidates").update({
        "status": "form_completed",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", payload.candidate_id).execute()


    # --------------------------------
    # 5️⃣ Always return success
    # --------------------------------
    return {"success": True}


# ================================
# Check Candidate Form Status
# ================================

@router.get("/candidate-form/status")
def candidate_form_status(candidate_id: str):
    candidate = (
        supabase
        .table("candidates")
        .select("status")
        .eq("id", candidate_id)
        .single()
        .execute()
        .data
    )

    if not candidate:
        return {"form_completed": False}

    return {
        "form_completed": candidate["status"] in [
            "form_completed",
            "interview_sent",
            "interview_started",
            "interview_completed"
        ]
    }


# ================================
# Admin: List All Candidate Forms
# ================================

@router.get("/candidate-form/all")
def list_all_candidate_forms():
    result = (
        supabase
        .table("candidate_forms")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return {"success": True, "data": result.data}
