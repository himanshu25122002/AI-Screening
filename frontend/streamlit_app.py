import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# =========================
# CONFIG
# =========================
BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

# =========================
# Candidate Flow (FORM → SCHEDULE)
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
        status_completed = r.json().get("form_completed", False)
    except Exception:
        status_completed = False

    # 1️⃣ Candidate fills form
    if not status_completed:
        import candidate_form
        candidate_form.render(candidate_id)
        st.stop()

    # 2️⃣ Candidate schedules interview
    st.success("✅ Application submitted successfully")

    st.markdown("## 📅 Schedule Your AI Interview")

    scheduled_at = st.date_input("Select Interview Date")
    scheduled_time = st.time_input("Select Interview Time")
    if "interview_scheduled" not in st.session_state:
        st.session_state.interview_scheduled = False

    if st.button("📩 Confirm & Send Interview Link", disabled=st.session_state.interview_scheduled):
        scheduled_datetime = datetime.combine(
            scheduled_at,
            scheduled_time
        )

        scheduled_datetime_utc = scheduled_datetime.astimezone()

        if scheduled_datetime_utc <= datetime.utcnow().astimezone():
            st.error("❌ Please select a future date and time")
            st.stop()


        res = requests.post(
            f"{BACKEND_URL}/interviews/schedule",
            json={
                "candidate_id": candidate_id,
                "scheduled_at": scheduled_datetime_utc.isoformat()
            },
            timeout=60
        )

        if res.status_code == 200:
            st.session_state.interview_scheduled = True
            st.success(
                "✅ Interview scheduled!\n\n"
                "📧 Check your email for the interview link.\n\n"
                "⏱ Link will be active for 1 hour from scheduled time."
            )
        else:
            st.error("❌ Failed to schedule interview")
            st.text(res.text)

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
    ["📥 HR Intake", "📊 Hiring Pipeline", "📝 Candidate Forms"],
    index=["📥 HR Intake", "📊 Hiring Pipeline", "📝 Candidate Forms"].index(st.session_state.page)
    if st.session_state.page in ["📥 HR Intake", "📊 Hiring Pipeline", "📝 Candidate Forms"]
    else 0
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
            placeholder="Python, FastAPI, SQL, AWS, etc..."
        )

        experience = st.selectbox(
            "Experience Level *",
            ["Entry", "Mid", "Senior", "Lead"]
        )

        culture = st.text_area(
            "Culture Traits *",
            placeholder="Collaborative, Growth-minded, Innovative, etc...."
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

# =========================
# PAGE 3 — CANDIDATE FORMS
# =========================
if page == "📝 Candidate Forms":

    # ---------- Header + Refresh ----------
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("📝 Candidate Forms Dashboard")
    with col2:
        if st.button("🔄 Refresh"):
            st.session_state.force_refresh = True

    # ---------- Init session state ----------
    if "selected_form_job" not in st.session_state:
        st.session_state.selected_form_job = "All Jobs"

    # ---------- Fetch data ----------
    with st.spinner("Fetching candidate forms..."):
        candidates_res = api_get("/candidates")
        vacancies_res = api_get("/vacancies")

    if candidates_res.status_code != 200 or vacancies_res.status_code != 200:
        st.error("Failed to load data")
        st.stop()

    candidates = candidates_res.json().get("data", [])
    vacancies = vacancies_res.json().get("data", [])

    if not candidates:
        st.info("No candidates found.")
        st.stop()

    # ---------- Build maps ----------
    vacancy_map = {v["id"]: v["job_role"] for v in vacancies}

    # ---------- Fetch candidate_forms directly ----------
    forms_res = requests.get(f"{BACKEND_URL}/candidate-form/all")
    if forms_res.status_code != 200:
        st.error("Failed to load candidate forms")
        st.stop()

    forms = forms_res.json().get("data", [])

    if not forms:
        st.info("No forms submitted yet.")
        st.stop()

    df_candidates = pd.DataFrame(candidates)
    df_forms = pd.DataFrame(forms)

    # ---------- Merge ----------
    df = df_forms.merge(
        df_candidates,
        left_on="candidate_id",
        right_on="id",
        how="left",
        suffixes=("_form", "_candidate")
    )
    # -------------------------------
    # Ensure required columns exist
    # -------------------------------
    required_columns = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "years_of_experience",
        "current_ctc",
        "expected_ctc",
        "notice_period",
        "portfolio_link",
        "created_at",
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    df["Job Name"] = df["vacancy_id"].map(vacancy_map).fillna("Unknown Job")

    # =========================
    # 🔽 JOB FILTER
    # =========================
    st.markdown("### 🔍 Filter by Job")

    job_options = ["All Jobs"] + sorted(df["Job Name"].unique().tolist())

    st.session_state.selected_form_job = st.selectbox(
        "Select Job",
        job_options,
        index=job_options.index(st.session_state.selected_form_job)
        if st.session_state.selected_form_job in job_options else 0
    )

    if st.session_state.selected_form_job != "All Jobs":
        df = df[df["Job Name"] == st.session_state.selected_form_job]

    # =========================
    # DISPLAY TABLE
    # =========================
    display_df = df[[
        "first_name",
        "last_name",
        "email_form",
        "phone_form",
        "Job Name",
        "years_of_experience",
        "current_ctc",
        "expected_ctc",
        "notice_period",
        "portfolio_link",
        "created_at_form"
    ]].copy()

    display_df["Candidate Name"] = (
        display_df["first_name"].fillna("") + " " + display_df["last_name"].fillna("")
    )

    display_df = display_df[[
        "Candidate Name",
        "email_form",
        "phone_form",
        "Job Name",
        "years_of_experience",
        "current_ctc",
        "expected_ctc",
        "notice_period",
        "portfolio_link",
        "created_at_form"
    ]].rename(columns={
        "email_form": "Email",
        "phone_form": "Phone",
        "years_of_experience": "Experience (Years)",
        "current_ctc": "Current CTC",
        "expected_ctc": "Expected CTC",
        "notice_period": "Notice Period (Days)",
        "portfolio_link": "Portfolio",
        "created_at_form": "Submitted At"
    })



    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )













