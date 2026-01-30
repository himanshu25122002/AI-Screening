from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from backend.config import config
from backend.database import supabase
from datetime import datetime

def is_real_email(email: str) -> bool:
    return email and not email.endswith("@placeholder.local")


class EmailService:
    def __init__(self):
        self.sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        self.from_email = Email(
            config.SENDGRID_FROM_EMAIL,
            config.SENDGRID_FROM_NAME
        )
    


    # ======================================================
    # 1️⃣ GOOGLE FORM INVITE
    # ======================================================
    def send_form_invitation(self, candidate_id: str, candidate_email: str, candidate_name: str):
        subject = "Complete Your Application – Next Steps"
        form_link = f"{config.FRONTEND_URL}?candidate_id={candidate_id}&step=form"
        html_content = f"""
        <html>
        <body>
            <h2>Hello {candidate_name},</h2>
            <p>Thank you for applying at <strong>Futuready</strong>.</p>

            <p>Please complete the short application form to proceed:</p>

            <a href="{form_link}"
               style="padding:12px 24px;background:#4CAF50;color:#fff;text-decoration:none;border-radius:4px;">
               Complete Application Form
            </a>

            <p style="margin-top:16px;">
                <b>Note:</b> This link is unique to you. Please do not share it.
            </p>


            <p>Best regards,<br>Futuready HR</p>
        </body>
        </html>
        """

        return self._send_email(
            candidate_id,
            candidate_email,
            subject,
            html_content,
            "form_invite"
        )

    # ======================================================
    # 2️⃣ AI INTERVIEW INVITE (AUTO LINK)
    # ======================================================
    def send_interview_invitation( self, candidate_id: str, candidate_email: str, candidate_name: str):
        subject = "AI Interview Invitation – Futuready"

        interview_link = (
            f"https://ai-screening-six.vercel.app/index.html"
            f"?candidate_id={candidate_id}"
        )

        html_content = f"""
        <html>
        <body>
            <h2>Hello {candidate_name},</h2>

            <p>You are invited to an <strong>AI-powered interview</strong>.</p>

            <a href="{interview_link}"
               style="padding:12px 24px;background:#2196F3;color:#fff;text-decoration:none;border-radius:4px;">
               Start AI Interview
            </a>

            <p><b>Important:</b> This link is unique. Do not share it.</p>

            <p>Best regards,<br>Futuready HR</p>
        </body>
        </html>
        """

        return self._send_email(
            candidate_id,
            candidate_email,
            subject,
            html_content,
            "interview_invite"
        )

    # ======================================================
    # 3️⃣ FINAL INTERVIEW (CALENDLY – AUTO)
    # ======================================================
    def send_final_interview_schedule(
        self,
        candidate_id: str,
        candidate_email: str,
        candidate_name: str
    ):
        subject = "Final Interview – Schedule Your Slot"

        calendly_link = config.CALENDLY_LINK

        html_content = f"""
        <html>
        <body>
            <h2>Congratulations {candidate_name} 🎉</h2>

            <p>You’ve cleared the AI interview!</p>

            <p>Please book your final interview using the link below:</p>

            <a href="{calendly_link}"
               style="padding:12px 24px;background:#673AB7;color:#fff;text-decoration:none;border-radius:4px;">
               Schedule Final Interview
            </a>

            <p>Best regards,<br>Futuready HR</p>
        </body>
        </html>
        """

        return self._send_email(
            candidate_id,
            candidate_email,
            subject,
            html_content,
            "schedule_confirmation"
        )

    # ======================================================
    # 4️⃣ REJECTION EMAIL
    # ======================================================
    def send_rejection_email(self, candidate_id: str, candidate_email: str, candidate_name: str):
        subject = "Application Update – Futuready"

        html_content = f"""
        <html>
        <body>
            <h2>Hello {candidate_name},</h2>

            <p>Thank you for taking the time to interview with us.</p>

            <p>At this stage, we will not be moving forward.</p>

            <p>We wish you all the best.</p>

            <p>Futuready HR</p>
        </body>
        </html>
        """

        return self._send_email(
            candidate_id,
            candidate_email,
            subject,
            html_content,
            "rejection"
        )

    # ======================================================
    # 🔒 INTERNAL EMAIL SENDER (LOGGED)
    # ======================================================
    def _send_email(
        self,
        candidate_id: str,
        recipient_email: str,
        subject: str,
        html_content: str,
        email_type: str
    ):

        if not is_real_email(recipient_email):
            print(f"⚠️ Skipping email send — invalid email: {recipient_email}")

        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=To(recipient_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            response = self.sg.send(message)


            supabase.table("email_logs").insert({
                "candidate_id": candidate_id,
                "email_type": email_type,
                "recipient_email": recipient_email,
                "subject": subject,
                "status": "sent",
                "sendgrid_message_id": response.headers.get("X-Message-Id"),
                "sent_at": datetime.utcnow().isoformat()
            }).execute()

            return {"success": True}

        except Exception as e:
            supabase.table("email_logs").insert({
                "candidate_id": candidate_id,
                "email_type": email_type,
                "recipient_email": recipient_email,
                "subject": subject,
                "status": "failed",
                "sent_at": datetime.utcnow().isoformat()
            }).execute()

            return {"success": False, "error": str(e)}


email_service = EmailService()








