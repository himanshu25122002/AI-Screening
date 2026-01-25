import streamlit as st
import requests
import pandas as pd

# =========================
# CONFIG
# =========================
BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

# =========================
# Candidate interview routing
# =========================
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
# API HELPERS
# =========================
def api_post(endpoint, **kwargs):
    return requests.post(f"{BACKEND_URL}{endpoint}", **kwargs)

def api_get(endpoint):
    return requests.get(f"{BACKEND_URL}{endpoint}")

# =========================
# SIDEBAR
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
    st.title("📥 HR Intake — Start Hiring Pipeline")
    st.markdown(
        "Fill job details **once** and upload **all resumes together**. "
        "The system will process each resume automatically."
    )

    with st.form("hr_intake"):
        job_role = st.text_input("Job Role *")

        skills = st.text_area(
            "Required Skills * (comma-separated)",
            placeholder="Python, FastAPI, SQL, AWS"
        )

        experience = st.selectbox(
            "Experience Level *",
            ["Entry", "Mid", "Senior", "Lead"]
        )

        culture = st.text_area(
            "Culture Traits *",
            value="Collaborative, Growth-minded, Innovative"
        )

        # ✅ NEW — Job Description
        job_description = st.text_area(
            "Job Description / Responsibilities *",
            placeholder=(
                "Describe responsibilities, tech stack, expectations, KPIs,\n"
                "team structure, tools, etc."
            ),
            height=160
        )

        resumes = st.file_uploader(
            "Upload Resumes (PDF)",
            type=["pdf"],
            accept_multiple_files=True
        )

        submitted = st.form_submit_button("🚀 Start AI Hiring Pipeline")

    if submitted:
        if not all([job_role, skills, culture, job_description, resumes]):
            st.error("❌ Please fill all required fields and upload resumes.")
            st.stop()

        with st.spinner("Creating job and uploading resumes..."):
            # 1️⃣ Create Vacancy
            vacancy_res = api_post(
                "/vacancies",
                json={
                    "job_role": job_role,
                    "required_skills": [s.strip() for s in skills.split(",")],
                    "experience_level": experience,
                    "culture_traits": [c.strip() for c in culture.split(",")],
                    "description": job_description,
                    "created_by": "hr@company.com"
                }
            )

            if vacancy_res.status_code != 200:
                st.error("❌ Failed to create job vacancy")
                st.text(vacancy_res.text)
                st.stop()

            vacancy_id = vacancy_res.json()["data"]["id"]

            # 2️⃣ Upload resumes
            success_count = 0
            failed = []

            for resume in resumes:
                try:
                    res = api_post(
                        "/candidates",
                        data={
                            "vacancy_id": vacancy_id,
                            "name": "",
                            "email": "",
                            "phone": ""
                        },
                        files={"resume": resume}
                    )

                    if res.status_code == 200:
                        success_count += 1
                    else:
                        failed_files.append(resume.name)

                except Exception as e:
                    failed_files.append(resume.name)

            st.success(f"✅ {success_count} resumes uploaded successfully!")

            if failed_files:
                st.warning("⚠️ Some resumes failed to process:")
                for f in failed_files:
                    st.write(f"- {f}")

# =========================
# PAGE 2 — PIPELINE DASHBOARD
# =========================
if page == "📊 Hiring Pipeline":
    st.title("📊 Hiring Pipeline Dashboard")

    with st.spinner("Fetching candidates..."):
        res = api_get("/candidates")

    if res.status_code != 200:
        st.error("Failed to load candidates")
        st.text(res.text)
    else:
        candidates = res.json().get("data", [])

        if not candidates:
            st.info("No candidates found yet.")
        else:
            df = pd.DataFrame(candidates)

            stage_map = {
                "new": "📄 Resume Uploaded",
                "screened": "📊 Resume Screened",
                "form_sent": "📝 Google Form Sent",
                "form_completed": "✅ Form Completed",
                "interviewed": "🎙 AI Interview Done",
                "recommended": "🏁 Final Interview",
                "rejected": "❌ Rejected"
            }

            df["Stage"] = df["status"].map(stage_map)
            df["Resume Score"] = df["screening_score"]

            display_df = df[
                ["name", "email", "vacancy_id", "Resume Score", "Stage"]
            ].rename(columns={
                "name": "Candidate Name",
                "email": "Email",
                "vacancy_id": "Job ID"
            })

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

