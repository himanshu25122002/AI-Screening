import streamlit as st
import requests
import pandas as pd

# =========================
# CONFIG
# =========================
BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

params = st.query_params
if "candidate_id" in params:
    import interview
    interview.render(params["candidate_id"])
    st.stop()

st.set_page_config(
    page_title="Futuready AI Hiring System",
    page_icon="💼",
    layout="wide"
)

# =========================
# HELPERS
# =========================
def api_post(endpoint, **kwargs):
    return requests.post(f"{BACKEND_URL}{endpoint}", **kwargs)

def api_get(endpoint):
    return requests.get(f"{BACKEND_URL}{endpoint}")

# =========================
# UI NAVIGATION
# =========================
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio(
    "Select Page",
    ["📥 HR Intake", "📊 Hiring Pipeline"]
)

# =========================
# PAGE 1 — HR INTAKE
# =========================
if page == "📥 HR Intake":
    st.title("📥 HR Intake – Start Hiring Pipeline")

    st.markdown("Fill job details **once** and upload all resumes together.")

    with st.form("hr_intake"):
        job_role = st.text_input("Job Role *")
        skills = st.text_area("Required Skills * (comma-separated)")
        experience = st.selectbox(
            "Experience Level *",
            ["Entry", "Mid", "Senior", "Lead"]
        )
        culture = st.text_area(
            "Culture Traits *",
            value="Collaborative, Growth-minded, Innovative"
        )

        resumes = st.file_uploader(
            "Upload Resumes (PDF)",
            type=["pdf"],
            accept_multiple_files=True
        )

        submitted = st.form_submit_button("🚀 Start AI Hiring Pipeline")

    if submitted:
        if not all([job_role, skills, culture, resumes]):
            st.error("Please fill all required fields and upload resumes.")
        else:
            with st.spinner("Processing resumes and starting AI pipeline..."):
                files = [("resumes", r) for r in resumes]
                data = {
                    "job_role": job_role,
                    "skills": skills,
                    "experience": experience,
                    "culture": culture
                }

                res = api_post("/process-job", data=data, files=files)

                if res.status_code == 200:
                    st.success(f"✅ {len(resumes)} resumes submitted successfully!")
                else:
                    st.error("❌ Failed to start pipeline")

# =========================
# PAGE 2 — PIPELINE DASHBOARD
# =========================
if page == "📊 Hiring Pipeline":
    st.title("📊 Hiring Pipeline Dashboard")

    with st.spinner("Fetching candidates..."):
        res = api_get("/candidates")

    if res.status_code != 200:
        st.error("Failed to load candidates")
    else:
        candidates = res.json().get("data", [])

        if not candidates:
            st.info("No candidates found yet.")
        else:
            df = pd.DataFrame(candidates)

            # Normalize stage display
            stage_map = {
                "resume": "📄 Resume Screening",
                "form_sent": "📝 Form Sent",
                "form_completed": "✅ Form Completed",
                "interview": "🎙 AI Interview",
                "final": "🏁 Final Review"
            }
            df["Stage"] = df["stage"].map(stage_map)

            display_df = df[[
                "name",
                "email",
                "job_role",
                "resume_score",
                "Stage",
                "recommendation"
            ]].rename(columns={
                "name": "Candidate",
                "email": "Email",
                "job_role": "Job Role",
                "resume_score": "Resume Score",
                "recommendation": "AI Recommendation"
            })

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
