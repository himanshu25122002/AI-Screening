import streamlit as st
import requests
from datetime import datetime
import re

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

# ================================
# Helpers
# ================================

def is_valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"[0-9]{10,15}", phone))


def is_valid_https_url(url: str) -> bool:
    return url.startswith("https://")


# ================================
# Main Render Function
# ================================

def render(candidate_id: str):
    st.title("📝 Candidate Information Form")
    st.info("Please fill all details carefully. This form can be submitted only once.")

    with st.form("candidate_form"):

        st.subheader("👤 Personal Details")

        first_name = st.text_input("First Name *")
        last_name = st.text_input("Last Name *")

        gender = st.selectbox("Gender *", ["Male", "Female", "Other"])
        age = st.selectbox("Age *", list(range(18, 61)))

        email = st.text_input("Email *")
        phone = st.text_input("Phone Number *", placeholder="10–15 digits")

        address = st.text_area("Address *")
        city = st.text_input("Town / City *")
        state = st.text_input("State *")

        st.divider()

        st.subheader("💼 Professional Details")

        years_of_experience = st.number_input(
            "Years of Experience *",
            min_value=0,
            step=1
        )

        current_ctc = st.number_input(
            "Current CTC *",
            min_value=0,
            step=1000
        )

        expected_ctc = st.number_input(
            "Expected CTC *",
            min_value=0,
            step=1000
        )

        notice_period = st.number_input(
            "Notice Period (days) *",
            min_value=0,
            step=1
        )

        portfolio_link = st.text_input(
            "Portfolio / GitHub / LinkedIn (https:// only)",
            placeholder="https://github.com/username"
        )

        submitted = st.form_submit_button("✅ Submit Form")

    # ================================
    # Validation + Submit
    # ================================

    if submitted:
        errors = []

        # Required text fields
        if not first_name.strip():
            errors.append("First name is required")
        if not last_name.strip():
            errors.append("Last name is required")
        if not email.strip():
            errors.append("Email is required")
        if not address.strip():
            errors.append("Address is required")
        if not city.strip():
            errors.append("City is required")
        if not state.strip():
            errors.append("State is required")

        # Phone
        if not is_valid_phone(phone):
            errors.append("Phone number must contain 10–15 digits only")

        # Portfolio link
        if portfolio_link and not is_valid_https_url(portfolio_link):
            errors.append("Portfolio link must start with https://")

        # Email format (basic safety)
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("Invalid email format")

        # Show errors
        if errors:
            for err in errors:
                st.error(f"❌ {err}")
            st.stop()

        # ================================
        # Payload (MATCHES BACKEND EXACTLY)
        # ================================

        payload = {
            "candidate_id": candidate_id,

            "first_name": first_name.strip(),
            "last_name": last_name.strip(),

            "gender": gender,
            "age": age,

            "email": email.strip().lower(),
            "phone": phone.strip(),

            "address": address.strip(),
            "city": city.strip(),
            "state": state.strip(),

            "years_of_experience": years_of_experience,
            "current_ctc": current_ctc,
            "expected_ctc": expected_ctc,
            "notice_period": notice_period,

            "portfolio_link": portfolio_link.strip() if portfolio_link else None
        }

        # ================================
        # Submit
        # ================================

        with st.spinner("Submitting form..."):
            r = requests.post(
                f"{BACKEND_URL}/candidate-form/submit",
                json=payload
            )

        if r.status_code == 200:
            st.success("✅ Form submitted successfully!")
            st.info("You may now close this page.")
            st.stop()
        else:
            st.error("❌ Failed to submit form. This form may already be submitted.")
