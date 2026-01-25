import PyPDF2
import io
import re
import uuid
from typing import Dict


class ResumeParser:
    @staticmethod
    def parse_pdf(file_content: bytes) -> str:
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text = ""
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

            return text.strip()

        except Exception as e:
            print(f"Error parsing PDF: {e}")
            return ""

    @staticmethod
    def parse_text(file_content: bytes) -> str:
        try:
            return file_content.decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"Error parsing text: {e}")
            return ""

    @staticmethod
    def extract_basic_info(resume_text: str) -> Dict[str, str]:
        info = {
            "name": "",
            "email": "",
            "phone": ""
        }

        if not resume_text:
            # 🔥 ABSOLUTE FALLBACK
            info["email"] = ResumeParser._generate_fallback_email()
            info["name"] = "Unknown"
            return info

        lines = resume_text.split("\n")

        # 🔍 EMAIL — scan FULL resume
        email_match = re.search(
            r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            resume_text
        )
        if email_match:
            info["email"] = email_match.group(0)

        # 📞 PHONE
        phone_match = re.search(
            r'(\+?\d{1,3}[\s\-]?)?\(?\d{3,4}\)?[\s\-]?\d{3}[\s\-]?\d{3,4}',
            resume_text
        )
        if phone_match:
            info["phone"] = phone_match.group(0)

        # 👤 NAME — first non-empty line
        for line in lines[:5]:
            clean = line.strip()
            if len(clean.split()) >= 2:
                info["name"] = clean
                break

        # 🚨 GUARANTEE EMAIL EXISTS
        if not info["email"]:
            info["email"] = ResumeParser._generate_fallback_email()

        if not info["name"]:
            info["name"] = "Unknown"

        return info

    @staticmethod
    def _generate_fallback_email() -> str:
        return f"auto_{uuid.uuid4().hex[:10]}@resume.local"


resume_parser = ResumeParser()

