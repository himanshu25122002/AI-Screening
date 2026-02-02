import streamlit as st
import requests
import pandas as pd

# =========================
# CONFIG
# =========================
BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

# =========================
# Candidate interview routing (UNCHANGED)
# =========================
params = st.query_params
candidate_id = params.get("candidate_id")

if candidate_id:
    try:
        r = requests.get(
            f"{BACKEND_URL}/candidate-form/status",
            params={"candidate_id": candidate_id},
            timeout=60
        )
        form_completed = r.json().get("form_completed", False)
    except Exception:
        form_completed = False

    if not form_completed:
        import candidate_form
        candidate_form.render(candidate_id)
    else:
        st.success("✅ Form already submitted")

        interview_url = (
            "https://ai-screening-six.vercel.app/index.html"
            f"?candidate_id={candidate_id}"
        )

        st.markdown("### 🎤 AI Interview")
        st.markdown(
            f"""
            <a href="{interview_url}" target="_blank">
                <button style="
                    padding:14px 28px;
                    font-size:16px;
                    background:#4CAF50;
                    color:white;
                    border:none;
                    border-radius:8px;
                    cursor:pointer;
                ">
                Start AI Interview
                </button>
            </a>
            """,
            unsafe_allow_html=True
        )

    st.stop()

# =========================
# PAGE CONFIG
# =========================
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
# SESSION-SAFE NAVIGATION
# =========================
if "page" not in st.session_state:
    st.session_state.page = "📥 HR Intake"  # default only ONCE

st.sidebar.title("🧭 Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["📥 HR Intake", "📊 Hiring Pipeline"],
    index=0 if st.session_state.page == "📥 HR Intake" else 1
)

st.session_state.page = page

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

            success_count = 0
            failed_files = []

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

                    if res.status_code == 200 and res.json().get("success"):
                        success_count += 1
                    else:
                        failed_files.append(resume.name)

                except Exception:
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

    # ---------- Header + Refresh ----------
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("📊 Hiring Pipeline Dashboard")

    with col2:
        if st.button("🔄 Refresh"):
            st.session_state.force_refresh = True

    # ---------- Initialize state ----------
    if "selected_job" not in st.session_state:
        st.session_state.selected_job = "All Jobs"

    if "force_refresh" not in st.session_state:
        st.session_state.force_refresh = False

    # ---------- Fetch candidates ----------
    with st.spinner("Fetching candidates..."):
        res = api_get("/candidates")

    st.session_state.force_refresh = False

    if res.status_code != 200:
        st.error("Failed to load candidates")
        st.text(res.text)
        st.stop()

    candidates = res.json().get("data", [])
    if not candidates:
        st.info("No candidates found yet.")
        st.stop()

    df = pd.DataFrame(candidates)

    # ---------- Fetch vacancies ----------
    vacancy_res = api_get("/vacancies")
    if vacancy_res.status_code != 200:
        st.error("Failed to load jobs")
        st.stop()

    vacancies = vacancy_res.json().get("data", [])

    vacancy_map = {v["id"]: v["job_role"] for v in vacancies}
    df["Job Name"] = df["vacancy_id"].map(vacancy_map).fillna("Unknown Job")

    # =========================
    # 🔽 JOB FILTER DROPDOWN
    # =========================
    st.markdown("### 🔍 Filter by Job")

    job_options = ["All Jobs"] + sorted(df["Job Name"].unique().tolist())

    st.session_state.selected_job = st.selectbox(
        "Select Job",
        job_options,
        index=job_options.index(st.session_state.selected_job)
        if st.session_state.selected_job in job_options else 0
    )

    # ---------- Apply filter ----------
    if st.session_state.selected_job != "All Jobs":
        df = df[df["Job Name"] == st.session_state.selected_job]

    # =========================
    # DISPLAY TABLE
    # =========================
    stage_map = {
        "new": "📄 Resume Uploaded",
        "screened": "📊 Resume Screened",
        "form_sent": "📝 Google Form Sent",
        "form_completed": "✅ Form Completed",
        "interview_sent": "🎤 AI Interview Link Sent",
        "interview_started": "🎙 AI Interview Started",
        "interview_completed": "🎙 AI Interview Done",
        "recommended": "🏁 Final Interview",
        "rejected": "❌ Rejected"
    }


    df["Stage"] = df["status"].map(stage_map)
    df["Resume Score"] = df["screening_score"]

    display_df = df[
        ["name", "email", "Job Name", "Resume Score", "Stage"]
    ].rename(columns={
        "name": "Candidate Name",
        "email": "Email"
    })

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )






