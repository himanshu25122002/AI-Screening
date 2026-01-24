import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL")
    SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "Futuready HR")

    GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    GOOGLE_FORM_SHEET_ID = os.getenv("GOOGLE_FORM_SHEET_ID")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
    AI_MODEL = os.getenv("AI_MODEL", "gpt-4-turbo-preview")

    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")
    GOOGLE_FORM_URL = os.getenv("GOOGLE_FORM_URL")
    CALENDLY_LINK = os.getenv("CALENDLY_LINK")


config = Config()

