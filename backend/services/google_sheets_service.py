import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from config import config
from database import supabase
from datetime import datetime
from services.email_service import email_service


class GoogleSheetsService:
    def __init__(self):
        if config.GOOGLE_SHEETS_CREDENTIALS:
            creds_dict = json.loads(config.GOOGLE_SHEETS_CREDENTIALS)
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
        else:
            self.service = None

    def sync_form_responses(self, sheet_id: str = None):
        if not self.service:
            return {"success": False, "error": "Google Sheets not configured"}

        if not sheet_id:
            sheet_id = config.GOOGLE_FORM_SHEET_ID

        if not sheet_id:
            return {"success": False, "error": "Sheet ID not provided"}

        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=sheet_id,
                range='A:Z'
            ).execute()

            values = result.get('values', [])
            if not values:
                return {"success": False, "error": "No data found in sheet"}

            headers = values[0]
            rows = values[1:]

            synced_count = 0
            errors = []

            for row in rows:
                try:
                    row_dict = dict(zip(headers, row))

                    email = row_dict.get('Email Address', '').strip()
                    if not email:
                        continue

                    candidate_result = supabase.table("candidates") \
                        .select("id, status, name") \
                        .eq("email", email) \
                        .maybeSingle() \
                        .execute()

                    if not candidate_result.data:
                        continue

                    candidate_id = candidate_result.data["id"]
                    candidate_status = candidate_result.data["status"]
                    candidate_name = candidate_result.data.get("name", "Candidate")

                    # ---------- Build form data ----------
                    portfolio_links = []
                    if row_dict.get('Portfolio URL'):
                        portfolio_links.append(row_dict['Portfolio URL'])
                    if row_dict.get('GitHub URL'):
                        portfolio_links.append(row_dict['GitHub URL'])
                    if row_dict.get('LinkedIn URL'):
                        portfolio_links.append(row_dict['LinkedIn URL'])

                    skill_assessment = {}
                    for key, value in row_dict.items():
                        if 'skill' in key.lower() and 'rate' in key.lower():
                            skill_name = key.replace('Rate your skill in', '').strip()
                            skill_assessment[skill_name] = value

                    form_data = {
                        "candidate_id": candidate_id,
                        "portfolio_links": portfolio_links,
                        "skill_self_assessment": skill_assessment,
                        "availability": row_dict.get('When can you start?', ''),
                        "salary_expectations": row_dict.get('Expected Salary', ''),
                        "additional_info": {
                            k: v for k, v in row_dict.items()
                            if k not in [
                                'Email Address',
                                'Timestamp',
                                'Portfolio URL',
                                'GitHub URL',
                                'LinkedIn URL'
                            ]
                        },
                        "form_submitted_at": row_dict.get(
                            'Timestamp', datetime.utcnow().isoformat()
                        )
                    }

                    existing_form = supabase.table("candidate_forms") \
                        .select("id") \
                        .eq("candidate_id", candidate_id) \
                        .maybeSingle() \
                        .execute()

                    if existing_form.data:
                        supabase.table("candidate_forms") \
                            .update(form_data) \
                            .eq("candidate_id", candidate_id) \
                            .execute()
                    else:
                        supabase.table("candidate_forms") \
                            .insert(form_data) \
                            .execute()

                    # ---------- 🔥 AUTO SEND AI INTERVIEW (RULE 2) ----------
                    if candidate_status == "form_sent":
                        supabase.table("candidates").update({
                            "status": "form_completed",
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", candidate_id).execute()

                        interview_link = f"{config.FRONTEND_URL}?candidate_id={candidate_id}"

                        email_service.send_interview_invitation(
                            candidate_id,
                            email,
                            candidate_name,
                            interview_link
                        )

                    synced_count += 1

                except Exception as e:
                    errors.append(f"Error processing row: {str(e)}")

            return {
                "success": True,
                "synced_count": synced_count,
                "errors": errors if errors else None
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_form_response_by_email(self, email: str, sheet_id: str = None):
        if not self.service:
            return None

        if not sheet_id:
            sheet_id = config.GOOGLE_FORM_SHEET_ID

        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=sheet_id,
                range='A:Z'
            ).execute()

            values = result.get('values', [])
            if not values:
                return None

            headers = values[0]
            rows = values[1:]

            for row in rows:
                row_dict = dict(zip(headers, row))
                if row_dict.get('Email Address', '').strip().lower() == email.lower():
                    return row_dict

            return None

        except Exception as e:
            print(f"Error fetching form response: {e}")
            return None


google_sheets_service = GoogleSheetsService()
