from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import uuid

from backend.database import supabase
from backend.services.email_service import email_service
from backend.config import config

router = APIRouter()


class InterviewSchedulePayload(BaseModel):
    candidate_id: str
    scheduled_at: str


@router.post("/interviews/schedule")
def schedule_interview(payload: InterviewSchedulePayload):

    # Parse datetime
    try:
        scheduled_dt = datetime.fromisoformat(
            payload.scheduled_at
        ).astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    if scheduled_dt < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Cannot schedule in the past")

    expires_at = scheduled_dt + timedelta(hours=1)
    token = str(uuid.uuid4())

    # Ensure candidate exists
    candidate = (
        supabase
        .table("candidates")
        .select("email, name")
        .eq("id", payload.candidate_id)
        .single()
        .execute()
        .data
    )

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Insert interview session
    supabase.table("ai_interview_sessions").insert({
        "candidate_id": payload.candidate_id,
        "interview_token": token,
        "scheduled_at": scheduled_dt.isoformat(),
        "expires_at": expires_at.isoformat(),
        "is_active": True
    }).execute()

    interview_link = f"{config.INTERVIEW_UI_URL}?token={token}"

    # Send interview link email
    email_service.send_interview_invitation(
        candidate["email"],
        candidate["name"],
        interview_link
    )

    # Update candidate status
    supabase.table("candidates").update({
        "status": "interview_sent",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", payload.candidate_id).execute()

    return {"success": True}
