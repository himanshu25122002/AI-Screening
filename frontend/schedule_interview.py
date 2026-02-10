import streamlit as st
import requests
from datetime import datetime, time

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

def render():
    st.title("📅 Schedule Your AI Interview")

    params = st.query_params
    candidate_id = params.get("candidate_id")

    if not candidate_id:
        st.error("Invalid scheduling link")
        st.stop()

    st.info("Choose a date and time for your AI interview. The interview link will be valid for **1 hour** from the scheduled time.")

    date = st.date_input("Interview Date")
    time_val = st.time_input("Interview Time", time(10, 0))

    if st.button("✅ Schedule Interview"):
        scheduled_at = datetime.combine(date, time_val).isoformat()

        with st.spinner("Scheduling your interview..."):
            r = requests.post(
                f"{BACKEND_URL}/interviews/schedule",
                params={
                    "candidate_id": candidate_id,
                    "scheduled_at": scheduled_at
                }
            )

        if r.status_code == 200:
            st.success("🎉 Interview scheduled successfully!")
            st.success("📧 Check your email for the interview link.")
        else:
            st.error(r.json().get("detail", "Failed to schedule interview"))
