from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from services.email_service import email_service
from database import supabase

router = APIRouter()


class CandidateFormPayload(BaseModel):
    candidate_id: str
    availability: Optional[str]
    salary_expectations: Optional[str]
    portfolio_links: List[str] = []
    skill_self_assessment: Optional[str]
    additional_info: Optional[str]
    form_submitted_at: Optional[str]


@router.post("/candidate-form/submit")
def submit_candidate_form(payload: CandidateFormPayload):
    try:
        supabase.table("candidate_forms").insert({
            "candidate_id": payload.candidate_id,
            "availability": payload.availability,
            "salary_expectations": payload.salary_expectations,
            "portfolio_links": payload.portfolio_links,
            "skill_self_assessment": payload.skill_self_assessment,
            "additional_info": payload.additional_info,
            "form_submitted_at": payload.form_submitted_at or datetime.utcnow().isoformat()
        }).execute()

        # update candidate status
        supabase.table("candidates").update({
            "status": "form_completed",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", payload.candidate_id).execute()

        return {"success": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
