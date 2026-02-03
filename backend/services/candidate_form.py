from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import supabase
from backend.services.email_service import email_service
from backend.config import config

router = APIRouter()


# ================================
# Payload Schema
# ================================
class CandidateFormPayload(BaseModel):
    candidate_id: str
    availability: Optional[str] = None
    salary_expectations: Optional[str] = None
    portfolio_links: List[str] = []
    skill_self_assessment: Optional[str] = None
    additional_info: Optional[str] = None
    form_submitted_at: Optional[str] = None


# ================================
# Submit Candidate Form
# ================================
@router.post("/candidate-form/submit")
def submit_candidate_form(payload: CandidateFormPayload):
    # --------------------------------
    # 1️⃣ Always save form first (NO FAIL)
    # --------------------------------
    supabase.table("candidate_forms").insert({
        "candidate_id": payload.candidate_id,
        "availability": payload.availability,
        "salary_expectations": payload.salary_expectations,
        "portfolio_links": payload.portfolio_links,
        "skill_self_assessment": payload.skill_self_assessment,
        "additional_info": payload.additional_info,
        "form_submitted_at": payload.form_submitted_at or datetime.utcnow().isoformat()
    }).execute()

    # --------------------------------
    # 2️⃣ Update candidate status safely
    # --------------------------------
    supabase.table("candidates").update({
        "status": "form_completed",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", payload.candidate_id).execute()

    # --------------------------------
    # 3️⃣ Try sending AI interview email (NON-BLOCKING)
    # --------------------------------
    try:
        candidate = (
            supabase.table("candidates")
            .select("email, name")
            .eq("id", payload.candidate_id)
            .single()
            .execute()
            .data
        )



        email_service.send_interview_invitation(
            payload.candidate_id,
            candidate["email"],
            candidate["name"]
        )

        # update status only if mail sent
        supabase.table("candidates").update({
            "status": "interview_sent",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", payload.candidate_id).execute()

    except Exception as e:
        # 🔥 DO NOT FAIL FORM SUBMISSION
        print("⚠️ Interview email failed:", e)

    # --------------------------------
    # 4️⃣ Always return success
    # --------------------------------
    return {"success": True}

# ================================
# Check Candidate Form Status
# ================================
@router.get("/candidate-form/status")
def candidate_form_status(candidate_id: str):
    candidate = (
        supabase.table("candidates")
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

@router.get("/candidate-form/all")
def list_all_candidate_forms():
    result = (
        supabase
        .table("candidate_forms")
        .select("*")
        .order("form_submitted_at", desc=True)
        .execute()
    )
    return {"success": True, "data": result.data}
