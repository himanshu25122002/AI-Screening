import io
import re
import uuid
from typing import Dict

import PyPDF2
from pdf2image import convert_from_bytes
import pytesseract


class ResumeParser:
    @staticmethod
    def parse_pdf(file_content: bytes) -> str:
        """
        Hybrid PDF parser:
        1) Try PyPDF2 (text-based PDFs)
        2) Fallback to OCR (Canva / scanned PDFs)
        """

        text = ""

        # =========================
        # 1️⃣ PyPDF2 (FAST PATH)
        # =========================
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            for page in pdf_reader.pages:
                extracted = page.extract_text() or ""
                text += extracted + "\n"

        except Exception as e:
            print(f"⚠️ PyPDF2 parsing failed: {e}")

        # =========================
        # 2️⃣ OCR FALLBACK
        # =========================
        if not text or len(text.strip()) < 50:
            print("⚠️ OCR fallback triggered (image-based PDF detected)")

            try:
                images = convert_from_bytes(file_content, dpi=300)
                ocr_text = []

                for img in images:
                    ocr_text.append(
                        pytesseract.image_to_string(
                            img,
                            config="--psm 6"
                        )
                    )

                text = "\n".join(ocr_text)

            except Exception as e:
                print(f"❌ OCR failed: {e}")

        return text.strip()

    @staticmethod
    def parse_text(file_content: bytes) -> str:
        try:
            return file_content.decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"❌ Error parsing text file: {e}")
            return ""


    @staticmethod
    def _normalize_email_context(text: str) -> str:
        if not text:
            return ""

   
        text = re.sub(r"\s+@\s+", "@", text)
        text = re.sub(r"\s+@", "@", text)
        text = re.sub(r"@\s+", "@", text)
        text = re.sub(r"\s+\.\s+", ".", text)
        text = re.sub(
            r'([a-zA-Z0-9._%+-]+)\s*\n\s*(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'\1\2',
            text
        )
        return text


    @staticmethod
    def extract_basic_info(resume_text: str) -> Dict[str, str]:
        """
        VERY conservative extraction.
        Name extraction is intentionally strict.
        AI will refine later in screening stage.
        """

        info = {
            "name": "",
            "email": "",
            "phone": ""
        }


        
        if not resume_text or len(resume_text.strip()) < 30:
            # 🔥 Absolute fallback
            info["email"] = ResumeParser._generate_fallback_email()
            info["name"] = ""
            return info
            
        normalized_text = ResumeParser._normalize_email_context(resume_text)

        emails = re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            normalized_text
        )

        def _is_sane_email(email: str) -> bool:
            local = email.split("@")[0]
            return any(c.isalpha() for c in local)


        if emails:
            sane_emails = [e for e in emails if _is_sane_email(e)]
            info["email"] = sane_emails[0] if sane_emails else emails[0]


            
        lines = resume_text.split("\n")


        # =========================
        # 📞 PHONE
        # =========================
        phone_match = re.search(
            r'(\+?\d{1,3}[\s\-]?)?\(?\d{3,4}\)?[\s\-]?\d{3}[\s\-]?\d{3,4}',
            resume_text
        )
        if phone_match:
            info["phone"] = phone_match.group(0)

        # =========================
        # 👤 NAME (STRICT TOP LINES)
        # =========================
        for line in lines[:5]:
            clean = line.strip()

            if not clean:
                continue

            if any(x in clean.lower() for x in [
                "resume", "curriculum", "vitae", "profile",
                "summary", "engineer", "developer", "intern",
                "student", "b.tech", "m.tech", "linkedin", "github"
            ]):
                continue

            if "@" in clean or any(char.isdigit() for char in clean):
                continue

            if re.match(r"^[A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2}$", clean):
                info["name"] = clean
                break

        # =========================
        # 🚨 GUARANTEES
        # =========================
       

        if not info["name"]:
            info["name"] = ""

        return info

    @staticmethod
    def _generate_fallback_email() -> str:
        return f"auto_{uuid.uuid4().hex[:10]}@resume.local"


resume_parser = ResumeParser()










