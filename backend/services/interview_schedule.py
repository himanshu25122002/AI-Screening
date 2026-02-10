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
    scheduled_at: str


@router.post("/interviews/schedule")
def schedule_interview(payload: InterviewSchedulePayload):

    # 1️⃣ Parse IST time → convert to UTC
    try:
        scheduled_ist = datetime.fromisoformat(payload.scheduled_at).replace(tzinfo=IST)
        scheduled_utc = scheduled_ist.astimezone(timezone.utc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    if scheduled_utc < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Cannot schedule in the past")

    expires_at = scheduled_utc + timedelta(hours=1)
    token = str(uuid.uuid4())

    # 2️⃣ FETCH CANDIDATE (🔥 THIS WAS MISSING)
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

    # 3️⃣ UPSERT INTERVIEW SESSION
    supabase.table("ai_interview_sessions").upsert(
        {
            "candidate_id": payload.candidate_id,
            "interview_token": token,
            "scheduled_at": scheduled_utc.isoformat(),  # UTC stored
            "expires_at": expires_at.isoformat(),       # UTC stored
            "is_active": True,
            "updated_at": datetime.utcnow().isoformat()
        },
        on_conflict="candidate_id"
    ).execute()

    # 4️⃣ SEND EMAIL
    interview_link = f"{config.INTERVIEW_UI_URL}?token={token}"

    email_service.send_interview_invitation(
        candidate["email"],
        candidate["name"],
        interview_link
    )

    # 5️⃣ UPDATE CANDIDATE STATUS
    supabase.table("candidates").update({
        "status": "interview_sent",
        "updated_at": datetime.utcnow().isoformat()
    }).eq("id", payload.candidate_id).execute()

    return {"success": True}
