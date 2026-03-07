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
    ["📥 HR Intake", "📊 Hiring Pipeline", "📝 Candidate Forms", "🎤 AI Interviews"],
    index=["📥 HR Intake", "📊 Hiring Pipeline", "📝 Candidate Forms", "🎤 AI Interviews"].index(st.session_state.page)
    if st.session_state.page in ["📥 HR Intake", "📊 Hiring Pipeline", "📝 Candidate Forms", "🎤 AI Interviews"]
    else 0
)

st.session_state.page = page

# =========================
# PAGE 1 — HR INTAKE
# =========================
if page == "📥 HR Intake":

    st.title("📥 HR Intake — Create Website Job")

    st.markdown(
        "Create job exactly as it exists on website.\n\n"
        "Candidates will apply from website and resumes will automatically enter system."
    )

    # =========================
    # JOB CREATION FORM
    # =========================
    with st.form("hr_intake"):

        external_job_id = st.text_input(
            "External Job ID *",
            help="Must match job ID used on website (e.g. web-developer, ai-intern)"
        )

        job_role = st.text_input("Job Position *")

        experience_years = st.number_input(
            "Experience Required (Years) *",
            min_value=0,
            max_value=30,
            step=1
        )

        col1, col2 = st.columns(2)
        with col1:
            budget_min = st.number_input(
                "Minimum Budget (₹)",
                min_value=0,
                step=1000
            )

        with col2:
            budget_max = st.number_input(
                "Maximum Budget (₹)",
                min_value=0,
                step=1000
            )

        google_calendar_link = st.text_input(
            "Google Calendar Scheduling Link (Optional)",
            placeholder="https://calendar.google.com/..."
        )

        col1, col2 = st.columns(2)
        with col1:
            resume_cutoff_score = st.number_input(
                "Resume Screening Cutoff (Default 80)",
                min_value=0,
                max_value=100,
                value=80
            )

        with col2:
            interview_cutoff_score = st.number_input(
                "AI Interview Cutoff (Default 80)",
                min_value=0,
                max_value=100,
                value=80
            )
           

        interview_duration_minutes = st.number_input(
            "AI Interview Duration (minutes) *",
            min_value=5,
            max_value=60,
            value=15
        )

        interview_custom_prompt = st.text_area(
            "Custom AI Interview Prompt (Optional)",
            height=120,
            help="You can add mandatory questions, themes, or special instructions."
        )
        
        job_summary = st.text_area(
            "Job Summary *",
            height=120
        )

        key_responsibilities = st.text_area(
            "Key Responsibilities *",
            height=160
        )

        skills = st.text_area(
            "Required Skills (comma-separated)",
            placeholder="HTML, CSS, JavaScript, React..."
        )

        culture = st.text_area(
            "Culture Traits (comma-separated)",
            placeholder="Collaborative, Innovative..."
        )

        if "resume_criteria" not in st.session_state:
            st.session_state.resume_criteria = []
        col1, col2, col3 = st.columns([4,2,1])
        with col1:
            crit_name = st.text_input("Interview Criterion", key="resume_crit_name")
        with col2:
            crit_weight = st.number_input("Weight %",min_value=0, max_value=100, key="resume_crit_weight")
        with col3:
            if st.form_submit_button("Add"):
                if crit_name:
                    st.session_state.resume_criteria.append((crit_name, crit_weight))
        resume_dict = {k: v for k, v in st.session_state.resume_criteria}
        st.write("Current Resume Criteria:", resume_dict)
        
        submitted = st.form_submit_button("🚀 Create Job")

    if submitted:

        if not all([external_job_id, job_role, job_summary, key_responsibilities]):
            st.error("❌ Please fill all required fields.")
            st.stop()

        with st.spinner("Creating job..."):

            vacancy_res = api_post(
                "/vacancies",
                json={
                    "external_job_id": external_job_id.strip().lower(),
                    "job_role": job_role,
                    "required_skills": [s.strip() for s in skills.split(",")] if skills else [],
                    "experience_level": f"{experience_years} years",
                    "culture_traits": [c.strip() for c in culture.split(",")] if culture else [],
                    "description": f"""
=== Job Summary: ===
{job_summary}

=== Key Responsibilities: ===
{key_responsibilities}
""",
                    "created_by": "hr@company.com",
                    "budget_min": budget_min,
                    "budget_max": budget_max,
                    "google_calendar_link": google_calendar_link,
                    "resume_cutoff_score": resume_cutoff_score if resume_cutoff_score > 0 else None,
                    "interview_cutoff_score": interview_cutoff_score if interview_cutoff_score > 0 else None,
                    "interview_evaluation_criteria": resume_dict if resume_dict else None,
                    "interview_duration_minutes": interview_duration_minutes,
                    "interview_custom_prompt": interview_custom_prompt if interview_custom_prompt else None
                }
            )

            if vacancy_res.status_code != 200:
                st.error("❌ Failed to create job vacancy")
                st.text(vacancy_res.text)
                st.stop()

            st.success("✅ Job created successfully!")

    # =========================
    # JOB LIST SECTION
    # =========================
    st.markdown("---")
    st.markdown("## 📋 Created Jobs")

    col1, col2 = st.columns([8, 1])
    with col2:
        if st.button("🔄 Refresh Jobs"):
            st.rerun()

    # Fetch jobs
    with st.spinner("Loading jobs..."):
        jobs_res = api_get("/vacancies")

    if jobs_res.status_code != 200:
        st.error("Failed to load jobs")
        st.stop()

    jobs = jobs_res.json().get("data", [])

    if not jobs:
        st.info("No jobs created yet.")
        st.stop()

    df_jobs = pd.DataFrame(jobs)

    # =========================
    # SEARCH
    # =========================
    search_query = st.text_input("🔎 Search Job (by name or external ID)")

    if search_query:
        df_jobs = df_jobs[
            df_jobs["job_role"].str.contains(search_query, case=False, na=False)
            |
            df_jobs["external_job_id"].str.contains(search_query, case=False, na=False)
        ]

    if df_jobs.empty:
        st.info("No matching jobs found.")
        st.stop()

    # =========================
    # DISPLAY TABLE
    # =========================
    display_jobs = df_jobs[
        ["job_role", "external_job_id", "experience_level","budget_min","budget_max","google_calendar_link", "created_at"]
    ].rename(columns={
        "job_role": "Job Name",
        "external_job_id": "External Job ID",
        "experience_level": "Experience",
        "budget_min": "Budget Min (₹)",
        "budget_max": "Budget Max (₹)",
        "google_calendar_link": "Calendar Link",
        "created_at": "Created At"
    })

    st.dataframe(display_jobs, use_container_width=True, hide_index=True)

    # =========================
    # SELECT JOB
    # =========================
    st.markdown("## 🎯 Select Job to Manage")

    selected_job_name = st.selectbox(
        "",
        df_jobs["job_role"].tolist()
    )


    selected_job = df_jobs[df_jobs["job_role"] == selected_job_name].iloc[0]

    st.markdown("### 📄 Job Details")

    st.write(f"**External ID:** {selected_job['external_job_id']}")
    st.write(f"**Experience:** {selected_job['experience_level']}")
    st.write(f"**Status:** {selected_job['status']}")

    # =========================
    # MANUAL CANDIDATE UPLOAD
    # =========================
    st.markdown("### ➕ Add Candidate Manually")

    manual_resume = st.file_uploader(
        "Upload Resume (PDF)",
        type=["pdf"],
        key="manual_resume_upload"
    )

    if st.button("📤 Add Candidate to This Job"):

        if not manual_resume:
            st.error("Please upload a resume first.")
            st.stop()

        with st.spinner("Uploading candidate..."):

            res = api_post(
                "/candidates",
                data={
                    "external_job_id": selected_job["external_job_id"]
                },
                files={"resume": manual_resume}
            )

            if res.status_code == 200 and res.json().get("success"):
                st.success("✅ Candidate added successfully!")
            else:
                st.error("❌ Failed to add candidate")
                st.text(res.text)


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
        "rejected": "❌ Rejected in Interview"
    }


    df["Status"] = df["status"].map(stage_map)
    df["Resume Score"] = df["screening_score"]
    df["Applied At"] = pd.to_datetime(df["created_at"], utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%d-%m-%Y %H:%M")
    display_df = df[
        ["name", "email", "resume_url", "Job Name", "Resume Score", "Status", "Applied At"]
    ].rename(columns={
        "name": "Candidate Name",
        "email": "Email",
        "resume_url": "Resume"
    })

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Resume": st.column_config.LinkColumn("Resume")
        }
    )

    st.markdown("### 📤 Bulk Google Form Sender")

    if st.session_state.selected_job != "All Jobs":

        selected_vacancy_id = None
        for v in vacancies:
            if v["job_role"] == st.session_state.selected_job:
                selected_vacancy_id = v["id"]
                break
        selected_vacancy = next(
            (v for v in vacancies if v["id"] == selected_vacancy_id),
            None
        )
        default_cutoff = selected_vacancy.get("resume_cutoff_score", 80) if selected_vacancy else 80
        cutoff = st.number_input(
            "Resume Passing Score",
            min_value=0,
            max_value=100,
            value=default_cutoff
        )
        if st.button("🚀 Send Google Form to Qualified Candidates"):

            res = requests.post(
                f"{BACKEND_URL}/vacancies/{selected_vacancy_id}/send-form-bulk",
                params={"cutoff": cutoff}
            )

            if res.status_code == 200:
                count = res.json().get("sent_count", 0)
                st.success(f"✅ Sent Google Form to {count} candidates")
                st.rerun()
            else:
                st.error("❌ Failed to send bulk forms")
                st.text(res.text)
            
    st.markdown("### HR Manual Actions")

    candidate_options = {}

    for _, row in df.iterrows():
        label = f"{row['name']} ({row['email']}) — Resume Score: {row.get('screening_score', 'N/A')}"
        candidate_options[label] = row["id"]

    selected_label = st.selectbox(
        "Select Candidate",
        list(candidate_options.keys())
    )

    candidate_id = candidate_options[selected_label]


    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Send Google Form"):
            res = requests.post(
                f"{BACKEND_URL}/candidates/{candidate_id}/send-form"
            )

            if res.status_code == 200:
                st.success("✅ Google Form sent successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to send form")
                st.text(res.text)

    with col2:
        if st.button("📅 Send Final Interview Link"):
            res = requests.post(
                f"{BACKEND_URL}/candidates/{candidate_id}/send-final-interview"
            )

            if res.status_code == 200:
                st.success("✅ Final interview link sent!")
                st.rerun()
            else:
                st.error("❌ Failed to send link")
                st.text(res.text)
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
    display_df = df.copy()
    
    
    display_df["Candidate Name"] = (
        display_df["first_name"].fillna("") + " " + display_df["last_name"].fillna("")
    )
    display_df["created_at_form"] = pd.to_datetime(display_df["created_at_form"], utc=True).dt.tz_convert("Asia/Kolkata").dt.strftime("%d-%m-%Y %H:%M")
    display_df = display_df[[
        "Candidate Name",
        "email_form",
        "phone_form",
        "Job Name",
        "gender",
        "age",
        "state",
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

    if "Portfolio" in display_df.columns:
        display_df["Portfolio"] = display_df["Portfolio"].apply(
            lambda x: f"{x}" if pd.notnull(x) and str(x).startswith("http") else x
        )
        
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Portfolio": st.column_config.LinkColumn("Portfolio")
        }
    ) 

# =========================
# PAGE 4 — AI INTERVIEW RESULTS (PRODUCTION)
# =========================
if page == "🎤 AI Interviews":

    st.title("🎤 AI Interview Dashboard")

    # ---------- Refresh ----------
    col1, col2 = st.columns([8, 1])
    with col2:
        if st.button("🔄 Refresh"):
            st.session_state.selected_candidate_id = None
            st.rerun()

    # ---------- Fetch Data ----------
    with st.spinner("Loading interview data..."):
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

    df_candidates = pd.DataFrame(candidates)

    # Only interviewed candidates
    df_candidates = df_candidates[
        df_candidates["status"].isin(["interviewed", "recommended", "rejected"])
    ]

    if df_candidates.empty:
        st.info("No AI interviews completed yet.")
        st.stop()

    # Map job names
    vacancy_map = {v["id"]: v["job_role"] for v in vacancies}
    df_candidates["Job Profile"] = df_candidates["vacancy_id"].map(vacancy_map)

    # =========================
    # 🔽 JOB FILTER
    # =========================
    st.markdown("### 🔍 Filter by Job")

    job_options = ["All Jobs"] + sorted(
        df_candidates["Job Profile"].dropna().unique().tolist()
    )

    selected_job = st.selectbox("Select Job", job_options)

    if selected_job != "All Jobs":
        df_candidates = df_candidates[
            df_candidates["Job Profile"] == selected_job
        ]

    # =========================
    # 🔎 SEARCH
    # =========================
    search_query = st.text_input("🔎 Search Candidate")

    if search_query:
        df_candidates = df_candidates[
            df_candidates["name"].str.contains(search_query, case=False, na=False)
        ]

    if df_candidates.empty:
        st.info("No candidates match filter.")
        st.stop()

    # =========================
    # FETCH INTERVIEW SCORES
    # =========================
    interview_rows = []

    for _, row in df_candidates.iterrows():
        interview_res = api_get(f"/interviews/{row['id']}")

        if interview_res.status_code != 200:
            continue

        interview_data = interview_res.json().get("data")

        if not interview_data:
            continue

        interview_rows.append({
            "Candidate ID": row["id"],
            "Name": row["name"],
            "Job Profile": row["Job Profile"],
            "Skill": interview_data.get("skill_score"),
            "Communication": interview_data.get("communication_score"),
            "Problem Solving": interview_data.get("problem_solving_score"),
            "Culture Fit": interview_data.get("culture_fit_score"),
            "Overall": interview_data.get("overall_score"),
            "Recommendation": interview_data.get("recommendation"),
        })

    if not interview_rows:
        st.info("No interview records found.")
        st.stop()

    df_interviews = pd.DataFrame(interview_rows)

    # =========================
    # 📊 TABLE VIEW
    # =========================
    st.markdown("### 📊 Interview Results")

    selected_row = st.dataframe(
        df_interviews.drop(columns=["Candidate ID"]),
        use_container_width=True,
        hide_index=True
    )

    # =========================
    # SELECT CANDIDATE
    # =========================
    selected_name = st.selectbox(
        "Select Candidate to View Details",
        df_interviews["Name"].tolist()
    )

    selected_candidate = df_interviews[
        df_interviews["Name"] == selected_name
    ].iloc[0]

    candidate_id = selected_candidate["Candidate ID"]

    # =========================
    # LOAD TRANSCRIPT
    # =========================
    detail_res = api_get(f"/interviews/{candidate_id}")

    if detail_res.status_code != 200:
        st.error("Failed to load interview details")
        st.stop()

    interview_detail = detail_res.json().get("data")

    st.markdown("---")
    st.subheader(f"📄 Interview Transcript — {selected_name}")

    transcript = interview_detail.get("interview_transcript", [])

    if not transcript:
        st.info("No transcript available.")
    else:
        for idx, qa in enumerate(transcript, start=1):
            st.markdown(f"**Q{idx}: {qa.get('question')}**")
            st.markdown(f"🗣 **Answer:** {qa.get('answer')}")
            st.markdown("---")









