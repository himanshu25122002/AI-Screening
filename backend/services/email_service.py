from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from config import config
from database import supabase
from datetime import datetime

class EmailService:
    def __init__(self):
        self.sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        self.from_email = Email(config.SENDGRID_FROM_EMAIL, config.SENDGRID_FROM_NAME)

    def send_form_invitation(self, candidate_id: str, candidate_email: str, candidate_name: str):
        subject = "Complete Your Application - Next Steps"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Hello {candidate_name},</h2>
            <p>Thank you for your interest in the position at Futuready!</p>
            <p>We've reviewed your resume and would like to learn more about you.
            Please complete the following form to proceed to the next stage:</p>
            <p style="margin: 30px 0;">
                <a href="{config.GOOGLE_FORM_URL}"
                   style="background-color: #4CAF50; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    Complete Application Form
                </a>
            </p>
            <p>This form will help us understand your skills, experience, and availability better.</p>
            <p>Best regards,<br>Futuready HR Team</p>
        </body>
        </html>
        """

        return self._send_email(candidate_id, candidate_email, subject, html_content, "form_invite")

    def send_interview_invitation(self, candidate_id: str, candidate_email: str, candidate_name: str, interview_link: str):
        subject = "AI Interview Invitation - Futuready"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Hello {candidate_name},</h2>
            <p>Congratulations! You've been selected for an AI-powered interview.</p>
            <p>This is a 20-minute conversational interview where you'll discuss your experience,
            skills, and fit for the role.</p>
            <p style="margin: 30px 0;">
                <a href="{interview_link}"
                   style="background-color: #2196F3; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    Start AI Interview
                </a>
            </p>
            <p><strong>Tips for the interview:</strong></p>
            <ul>
                <li>Find a quiet place with good internet connection</li>
                <li>Be prepared to discuss your experience and projects</li>
                <li>Answer thoughtfully and honestly</li>
                <li>Take your time - there's no rush</li>
            </ul>
            <p>Best regards,<br>Futuready HR Team</p>
        </body>
        </html>
        """

        return self._send_email(candidate_id, candidate_email, subject, html_content, "interview_invite")

    def send_final_interview_schedule(self, candidate_id: str, candidate_email: str,
                                     candidate_name: str, scheduled_date: str,
                                     location: str, meeting_link: str = None):
        subject = "Final Interview Scheduled - Futuready"

        meeting_info = ""
        if meeting_link:
            meeting_info = f'<p><a href="{meeting_link}">Join Virtual Meeting</a></p>'

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Hello {candidate_name},</h2>
            <p>Great news! We'd like to invite you for a final face-to-face interview.</p>
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Interview Details:</h3>
                <p><strong>Date & Time:</strong> {scheduled_date}</p>
                <p><strong>Location:</strong> {location}</p>
                {meeting_info}
            </div>
            <p>Please confirm your attendance by replying to this email.</p>
            <p>If you need to reschedule, please let us know as soon as possible.</p>
            <p>We look forward to meeting you!</p>
            <p>Best regards,<br>Futuready HR Team</p>
        </body>
        </html>
        """

        return self._send_email(candidate_id, candidate_email, subject, html_content, "schedule_confirmation")

    def send_rejection_email(self, candidate_id: str, candidate_email: str, candidate_name: str):
        subject = "Application Update - Futuready"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Hello {candidate_name},</h2>
            <p>Thank you for your interest in the position at Futuready and for taking
            the time to go through our interview process.</p>
            <p>After careful consideration, we've decided to move forward with other candidates
            whose experience more closely matches our current needs.</p>
            <p>We were impressed by your background and encourage you to apply for future
            opportunities that match your skills and experience.</p>
            <p>We wish you the best in your job search.</p>
            <p>Best regards,<br>Futuready HR Team</p>
        </body>
        </html>
        """

        return self._send_email(candidate_id, candidate_email, subject, html_content, "rejection")

    def _send_email(self, candidate_id: str, recipient_email: str, subject: str,
                   html_content: str, email_type: str):
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

            return {
                "success": True,
                "message": "Email sent successfully",
                "message_id": response.headers.get("X-Message-Id")
            }

        except Exception as e:
            supabase.table("email_logs").insert({
                "candidate_id": candidate_id,
                "email_type": email_type,
                "recipient_email": recipient_email,
                "subject": subject,
                "status": "failed",
                "sent_at": datetime.utcnow().isoformat()
            }).execute()

            return {
                "success": False,
                "error": str(e)
            }

email_service = EmailService()
