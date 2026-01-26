import streamlit as st
import requests
from datetime import datetime

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")


def render(candidate_id: str):
    st.title("📝 Candidate Information Form")

    st.info("Please fill the details carefully before proceeding.")

    with st.form("candidate_form"):
        availability = st.text_input("📅 Availability (e.g. Immediate, 2 weeks)")
        salary_expectations = st.text_input("💰 Salary Expectations")

        portfolio_links = st.text_area(
            "🔗 Portfolio / GitHub / LinkedIn (comma separated)"
        )

        skill_self_assessment = st.text_area(
            "🧠 Skill Self Assessment (JSON or plain text)",
            placeholder="Python: 8/10, ML: 7/10"
        )

        additional_info = st.text_area("🗒 Additional Information")

        submitted = st.form_submit_button("✅ Submit Form")

    if submitted:
        payload = {
            "candidate_id": candidate_id,
            "availability": availability,
            "salary_expectations": salary_expectations,
            "portfolio_links": [
                link.strip() for link in portfolio_links.split(",") if link.strip()
            ],
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
