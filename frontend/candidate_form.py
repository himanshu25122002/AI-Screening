import streamlit as st
import requests
from datetime import datetime
import re

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")


def is_valid_url(url: str) -> bool:
    return bool(re.match(r"^https?://", url))


def render(candidate_id: str):
    st.title("📝 Candidate Information Form")
    st.info("Please fill the details carefully before proceeding.")

    with st.form("candidate_form"):
        availability = st.text_input("📅 Availability (e.g. Immediate, 2 weeks)")

        salary_expectations = st.text_input(
            "💰 Salary Expectations (numbers only)",
            placeholder="e.g. 800000 or 12,00,000"
        )

        portfolio_links_raw = st.text_area(
            "🔗 Portfolio / GitHub / LinkedIn (comma separated links only)",
            placeholder="https://github.com/username, https://linkedin.com/in/username"
        )

        skill_self_assessment = st.text_area(
            "🧠 Skill Self Assessment",
            placeholder="Python: 8/10, ML: 7/10"
        )

        additional_info = st.text_area("🗒 Additional Information")

        submitted = st.form_submit_button("✅ Submit Form")

    if submitted:
        errors = []

        # =========================
        # 💰 SALARY VALIDATION
        # =========================
        cleaned_salary = salary_expectations.replace(",", "").strip()

        if cleaned_salary and not cleaned_salary.isdigit():
            errors.append("💰 Salary must contain numbers only.")

        # =========================
        # 🔗 PORTFOLIO LINKS VALIDATION
        # =========================
        portfolio_links = [
            link.strip() for link in portfolio_links_raw.split(",") if link.strip()
        ]

        for link in portfolio_links:
            if not is_valid_url(link):
                errors.append(
                    f"🔗 Invalid link detected: `{link}` (must start with http:// or https://)"
                )

        # =========================
        # ❌ SHOW ERRORS
        # =========================
        if errors:
            for err in errors:
                st.error(err)
            st.stop()

        # =========================
        # ✅ SUBMIT PAYLOAD
        # =========================
        payload = {
            "candidate_id": candidate_id,
            "availability": availability,
            "salary_expectations": cleaned_salary,
            "portfolio_links": portfolio_links,
            "skill_self_assessment": skill_self_assessment,
            "additional_info": additional_info,
            "form_submitted_at": datetime.utcnow().isoformat()
        }

        with st.spinner("Submitting form..."):
            r = requests.post(
                f"{BACKEND_URL}/candidate-form/submit",
                json=payload
            )

        if r.status_code == 200:
            st.success("✅ Form submitted successfully!")
            st.stop()
        else:
            st.error("❌ Failed to submit form")
