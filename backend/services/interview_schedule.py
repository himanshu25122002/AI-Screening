from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import uuid

from backend.database import supabase
from backend.services.email_service import email_service
from backend.config import config

router = APIRouter()

IST = ZoneInfo("Asia/Kolkata")


class InterviewSchedulePayload(BaseModel):
    candidate_id: str
    scheduled_at: str   # ISO string WITH timezone (+05:30)


from zoneinfo import ZoneInfo

@router.post("/interviews/schedule")
def schedule_interview(payload: InterviewSchedulePayload):

    IST = ZoneInfo("Asia/Kolkata")

    try:
        # 👇 treat input as IST
        scheduled_ist = datetime.fromisoformat(payload.scheduled_at).replace(tzinfo=IST)
        scheduled_utc = scheduled_ist.astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    if scheduled_utc < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Cannot schedule in the past")

    expires_at = scheduled_utc + timedelta(hours=1)
    token = str(uuid.uuid4())

    supabase.table("ai_interview_sessions").upsert({
        "candidate_id": payload.candidate_id,
        "interview_token": token,
        "scheduled_at": scheduled_utc.isoformat(),
        "expires_at": expires_at.isoformat(),
        "is_active": True,
        "updated_at": datetime.utcnow().isoformat()
    }, on_conflict="candidate_id").execute()

    interview_link = f"{config.INTERVIEW_UI_URL}?token={token}"

    email_service.send_interview_invitation(
        candidate["email"],
        candidate["name"],
        interview_link
    )

    return {"success": True}
