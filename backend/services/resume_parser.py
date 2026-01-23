import PyPDF2
import io
from typing import Dict

class ResumeParser:
    @staticmethod
    def parse_pdf(file_content: bytes) -> str:
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            return text.strip()

        except Exception as e:
            print(f"Error parsing PDF: {e}")
            return ""

    @staticmethod
    def parse_text(file_content: bytes) -> str:
        try:
            return file_content.decode('utf-8')
        except Exception as e:
            print(f"Error parsing text: {e}")
            return ""

    @staticmethod
    def extract_basic_info(resume_text: str) -> Dict[str, str]:
        lines = resume_text.split('\n')
        info = {
            "name": "",
            "email": "",
            "phone": ""
        }

        import re

        for line in lines[:10]:
            if not info["email"] and '@' in line:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
                if email_match:
                    info["email"] = email_match.group(0)

            if not info["phone"]:
                phone_match = re.search(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', line)
                if phone_match:
                    info["phone"] = phone_match.group(0)

        if not info["name"] and lines:
            info["name"] = lines[0].strip()

        return info

resume_parser = ResumeParser()
