import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json

API_URL = st.secrets.get("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Futuready AI Hiring System",
    page_icon="💼",
    layout="wide"
)

def api_request(method, endpoint, **kwargs):
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, **kwargs)
        elif method == "POST":
            response = requests.post(url, **kwargs)
        elif method == "PUT":
            response = requests.put(url, **kwargs)
        elif method == "DELETE":
            response = requests.delete(url, **kwargs)

        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

def main():
    st.title("💼 Futuready AI Hiring System")

    menu = st.sidebar.selectbox(
        "Navigation",
        ["Dashboard", "Vacancies", "Candidates", "AI Screening", "AI Interviews",
         "Final Interviews", "Email Management", "Google Forms Sync"]
    )

    if menu == "Dashboard":
        show_dashboard()
    elif menu == "Vacancies":
        show_vacancies()
    elif menu == "Candidates":
        show_candidates()
    elif menu == "AI Screening":
        show_screening()
    elif menu == "AI Interviews":
        show_interviews()
    elif menu == "Final Interviews":
        show_final_interviews()
    elif menu == "Email Management":
        show_email_management()
    elif menu == "Google Forms Sync":
        show_google_forms_sync()

def show_dashboard():
    st.header("Dashboard")

    vacancies_response = api_request("GET", "/vacancies?status=active")

    if vacancies_response and vacancies_response.get("success"):
        vacancies = vacancies_response["data"]

        st.subheader(f"Active Vacancies: {len(vacancies)}")

        for vacancy in vacancies:
            with st.expander(f"📋 {vacancy['job_role']}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Experience Level:** {vacancy['experience_level']}")
                    st.write(f"**Created by:** {vacancy['created_by']}")
                    st.write(f"**Created:** {vacancy['created_at'][:10]}")

                with col2:
                    st.write(f"**Skills:** {', '.join(vacancy['required_skills'])}")
                    st.write(f"**Culture Traits:** {', '.join(vacancy['culture_traits'])}")

                stats_response = api_request("GET", f"/stats/vacancy/{vacancy['id']}")
                if stats_response and stats_response.get("success"):
                    stats = stats_response["data"]

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Candidates", stats['total_candidates'])
                    with col2:
                        screened = stats['status_breakdown'].get('screened', 0)
                        st.metric("Screened", screened)
                    with col3:
                        interviewed = stats['status_breakdown'].get('interviewed', 0)
                        st.metric("Interviewed", interviewed)

                    if stats['recommendation_breakdown']:
                        st.write("**Recommendations:**")
                        rec_df = pd.DataFrame([
                            {"Recommendation": k, "Count": v}
                            for k, v in stats['recommendation_breakdown'].items()
                        ])
                        st.dataframe(rec_df, hide_index=True)

def show_vacancies():
    st.header("Manage Vacancies")

    tab1, tab2 = st.tabs(["View Vacancies", "Create New Vacancy"])

    with tab1:
        vacancies_response = api_request("GET", "/vacancies")

        if vacancies_response and vacancies_response.get("success"):
            vacancies = vacancies_response["data"]

            if vacancies:
                df = pd.DataFrame(vacancies)
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')

                st.dataframe(
                    df[['job_role', 'experience_level', 'status', 'created_by', 'created_at']],
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No vacancies found")

    with tab2:
        with st.form("create_vacancy"):
            job_role = st.text_input("Job Role*")
            experience_level = st.selectbox(
                "Experience Level*",
                ["Entry Level", "Mid Level", "Senior Level", "Lead/Principal"]
            )

            required_skills = st.text_area(
                "Required Skills* (comma-separated)",
                help="Enter skills separated by commas"
            )

            culture_traits = st.text_area(
                "Culture Traits* (comma-separated)",
                help="Enter desired culture traits separated by commas",
                value="Collaborative, Innovative, Growth-minded, Communicative"
            )

            description = st.text_area("Job Description")
            created_by = st.text_input("HR Email*")

            submitted = st.form_submit_button("Create Vacancy")

            if submitted:
                if not all([job_role, required_skills, culture_traits, created_by]):
                    st.error("Please fill all required fields")
                else:
                    vacancy_data = {
                        "job_role": job_role,
                        "required_skills": [s.strip() for s in required_skills.split(',')],
                        "experience_level": experience_level,
                        "culture_traits": [t.strip() for t in culture_traits.split(',')],
                        "description": description,
                        "created_by": created_by
                    }

                    response = api_request("POST", "/vacancies", json=vacancy_data)

                    if response and response.get("success"):
                        st.success("Vacancy created successfully!")
                        st.rerun()

def show_candidates():
    st.header("Manage Candidates")

    tab1, tab2 = st.tabs(["View Candidates", "Add New Candidate"])

    with tab1:
        vacancies_response = api_request("GET", "/vacancies?status=active")

        if vacancies_response and vacancies_response.get("success"):
            vacancies = vacancies_response["data"]

            vacancy_options = {v['job_role']: v['id'] for v in vacancies}
            vacancy_options = {"All Vacancies": None, **vacancy_options}

            selected_vacancy = st.selectbox("Filter by Vacancy", list(vacancy_options.keys()))

            vacancy_id = vacancy_options[selected_vacancy]

            endpoint = "/candidates"
            if vacancy_id:
                endpoint += f"?vacancy_id={vacancy_id}"

            candidates_response = api_request("GET", endpoint)

            if candidates_response and candidates_response.get("success"):
                candidates = candidates_response["data"]

                if candidates:
                    for candidate in candidates:
                        with st.expander(f"👤 {candidate['name']} - {candidate['email']}"):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.write(f"**Status:** {candidate['status']}")
                                st.write(f"**Phone:** {candidate.get('phone', 'N/A')}")

                            with col2:
                                st.write(f"**Screening Score:** {candidate.get('screening_score', 'N/A')}")
                                st.write(f"**Experience:** {candidate.get('experience_years', 'N/A')} years")

                            with col3:
                                st.write(f"**Skills:** {', '.join(candidate.get('skills', []))}")

                            if candidate.get('screening_notes'):
                                st.write("**Screening Notes:**")
                                st.info(candidate['screening_notes'])

                            if st.button(f"View Full Details", key=f"view_{candidate['id']}"):
                                show_candidate_details(candidate['id'])
                else:
                    st.info("No candidates found")

    with tab2:
        vacancies_response = api_request("GET", "/vacancies?status=active")

        if vacancies_response and vacancies_response.get("success"):
            vacancies = vacancies_response["data"]

            vacancy_options = {v['job_role']: v['id'] for v in vacancies}

            with st.form("add_candidate"):
                selected_job = st.selectbox("Select Vacancy*", list(vacancy_options.keys()))
                name = st.text_input("Candidate Name*")
                email = st.text_input("Email*")
                phone = st.text_input("Phone")
                resume = st.file_uploader("Upload Resume*", type=['pdf', 'txt'])

                submitted = st.form_submit_button("Add Candidate")

                if submitted:
                    if not all([selected_job, name, email, resume]):
                        st.error("Please fill all required fields")
                    else:
                        files = {"resume": resume}
                        data = {
                            "vacancy_id": vacancy_options[selected_job],
                            "name": name,
                            "email": email,
                            "phone": phone
                        }

                        response = api_request("POST", "/candidates", data=data, files=files)

                        if response and response.get("success"):
                            st.success("Candidate added successfully!")
                            st.rerun()

def show_candidate_details(candidate_id):
    response = api_request("GET", f"/candidates/{candidate_id}")

    if response and response.get("success"):
        data = response["data"]
        candidate = data["candidate"]
        form_data = data.get("form_data")
        interview_data = data.get("interview_data")

        st.subheader(f"Candidate: {candidate['name']}")

        st.write("**Basic Information:**")
        st.json(candidate)

        if form_data:
            st.write("**Google Form Response:**")
            st.json(form_data)

        if interview_data:
            st.write("**AI Interview Results:**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Skill Score", f"{interview_data['skill_score']:.0f}")
            with col2:
                st.metric("Communication", f"{interview_data['communication_score']:.0f}")
            with col3:
                st.metric("Problem Solving", f"{interview_data['problem_solving_score']:.0f}")
            with col4:
                st.metric("Culture Fit", f"{interview_data['culture_fit_score']:.0f}")

            st.write(f"**Overall Score:** {interview_data['overall_score']:.0f}")
            st.write(f"**Recommendation:** {interview_data['recommendation']}")
            st.write(f"**Evaluation Notes:** {interview_data['evaluation_notes']}")

def show_screening():
    st.header("AI Resume Screening")

    vacancies_response = api_request("GET", "/vacancies?status=active")

    if vacancies_response and vacancies_response.get("success"):
        vacancies = vacancies_response["data"]

        vacancy_options = {v['job_role']: v['id'] for v in vacancies}

        selected_job = st.selectbox("Select Vacancy", list(vacancy_options.keys()))
        vacancy_id = vacancy_options[selected_job]

        if st.button("Screen All New Candidates"):
            with st.spinner("Screening candidates..."):
                response = api_request("POST", f"/screening/batch?vacancy_id={vacancy_id}")

                if response and response.get("success"):
                    results = response["results"]
                    success_count = sum(1 for r in results if r.get("success"))

                    st.success(f"Screened {success_count} out of {len(results)} candidates")

                    for result in results:
                        if result.get("success"):
                            data = result["data"]
                            st.info(f"Candidate scored {data['screening_score']:.0f}/100")

        candidates_response = api_request("GET", f"/candidates?vacancy_id={vacancy_id}&status=new")

        if candidates_response and candidates_response.get("success"):
            candidates = candidates_response["data"]

            if candidates:
                st.subheader("New Candidates Awaiting Screening")

                for candidate in candidates:
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.write(f"**{candidate['name']}** - {candidate['email']}")

                    with col2:
                        if st.button("Screen", key=f"screen_{candidate['id']}"):
                            with st.spinner("Screening..."):
                                response = api_request(
                                    "POST",
                                    "/screening/resume",
                                    json={"candidate_id": candidate['id']}
                                )

                                if response and response.get("success"):
                                    st.success("Screening completed!")
                                    st.rerun()
            else:
                st.info("No new candidates awaiting screening")

def show_interviews():
    st.header("AI Interviews")

    candidates_response = api_request("GET", "/candidates?status=form_completed")

    if candidates_response and candidates_response.get("success"):
        candidates = candidates_response["data"]

        if candidates:
            st.subheader("Candidates Ready for Interview")

            for candidate in candidates:
                with st.expander(f"👤 {candidate['name']} - Score: {candidate.get('screening_score', 'N/A')}"):
                    st.write(f"**Email:** {candidate['email']}")
                    st.write(f"**Experience:** {candidate.get('experience_years', 'N/A')} years")
                    st.write(f"**Skills:** {', '.join(candidate.get('skills', []))}")

                    if st.button("Start AI Interview", key=f"interview_{candidate['id']}"):
                        with st.spinner("Generating interview questions..."):
                            response = api_request(
                                "POST",
                                "/interviews/start",
                                json={
                                    "candidate_id": candidate['id'],
                                    "vacancy_id": candidate['vacancy_id']
                                }
                            )

                            if response and response.get("success"):
                                st.success("Interview questions generated!")
                                st.json(response["data"])
        else:
            st.info("No candidates ready for interview")

    st.divider()

    st.subheader("Completed Interviews")

    interviewed_response = api_request("GET", "/candidates?status=interviewed")

    if interviewed_response and interviewed_response.get("success"):
        interviewed = interviewed_response["data"]

        if interviewed:
            for candidate in interviewed:
                interview_response = api_request("GET", f"/interviews/{candidate['id']}")

                if interview_response and interview_response.get("success"):
                    interview = interview_response["data"]

                    with st.expander(f"👤 {candidate['name']} - {interview['recommendation']}"):
                        col1, col2, col3, col4, col5 = st.columns(5)

                        with col1:
                            st.metric("Overall", f"{interview['overall_score']:.0f}")
                        with col2:
                            st.metric("Skill", f"{interview['skill_score']:.0f}")
                        with col3:
                            st.metric("Communication", f"{interview['communication_score']:.0f}")
                        with col4:
                            st.metric("Problem Solving", f"{interview['problem_solving_score']:.0f}")
                        with col5:
                            st.metric("Culture Fit", f"{interview['culture_fit_score']:.0f}")

                        st.write("**Evaluation Notes:**")
                        st.info(interview['evaluation_notes'])

def show_final_interviews():
    st.header("Final Interview Scheduling")

    tab1, tab2 = st.tabs(["Schedule Interview", "View Scheduled"])

    with tab1:
        candidates_response = api_request("GET", "/candidates?status=interviewed")

        if candidates_response and candidates_response.get("success"):
            candidates = candidates_response["data"]

            strong_fit_candidates = []
            for candidate in candidates:
                interview_response = api_request("GET", f"/interviews/{candidate['id']}")
                if interview_response and interview_response.get("success"):
                    interview = interview_response["data"]
                    if interview.get('recommendation') in ['Strong Fit', 'Moderate Fit']:
                        strong_fit_candidates.append(candidate)

            if strong_fit_candidates:
                candidate_options = {
                    f"{c['name']} ({c['email']})": c['id']
                    for c in strong_fit_candidates
                }

                with st.form("schedule_interview"):
                    selected_candidate = st.selectbox("Select Candidate", list(candidate_options.keys()))
                    scheduled_date = st.date_input("Interview Date", min_value=datetime.now().date())
                    scheduled_time = st.time_input("Interview Time")
                    location = st.text_input("Location", value="Futuready Office")
                    interviewer_names = st.text_input(
                        "Interviewers (comma-separated)",
                        value="HR Manager, Tech Lead"
                    )
                    meeting_link = st.text_input("Meeting Link (optional)")
                    notes = st.text_area("Additional Notes")

                    submitted = st.form_submit_button("Schedule Interview")

                    if submitted:
                        candidate_id = candidate_options[selected_candidate]
                        candidate = next(c for c in strong_fit_candidates if c['id'] == candidate_id)

                        scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)

                        schedule_data = {
                            "candidate_id": candidate_id,
                            "vacancy_id": candidate['vacancy_id'],
                            "scheduled_date": scheduled_datetime.isoformat(),
                            "location": location,
                            "interviewer_names": [name.strip() for name in interviewer_names.split(',')],
                            "meeting_link": meeting_link if meeting_link else None,
                            "notes": notes
                        }

                        response = api_request("POST", "/final-interviews/schedule", json=schedule_data)

                        if response and response.get("success"):
                            st.success("Interview scheduled and email sent!")
                            st.rerun()
            else:
                st.info("No candidates recommended for final interview")

    with tab2:
        interviews_response = api_request("GET", "/final-interviews")

        if interviews_response and interviews_response.get("success"):
            interviews = interviews_response["data"]

            if interviews:
                for interview in interviews:
                    candidate = interview.get('candidates', {})
                    vacancy = interview.get('vacancies', {})

                    status_color = {
                        "scheduled": "🟢",
                        "completed": "🔵",
                        "cancelled": "🔴",
                        "rescheduled": "🟡"
                    }

                    with st.expander(
                        f"{status_color.get(interview['status'], '⚪')} "
                        f"{candidate.get('name', 'Unknown')} - "
                        f"{interview['scheduled_date'][:16]}"
                    ):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Candidate:** {candidate.get('name', 'Unknown')}")
                            st.write(f"**Email:** {candidate.get('email', 'N/A')}")
                            st.write(f"**Position:** {vacancy.get('job_role', 'N/A')}")

                        with col2:
                            st.write(f"**Date & Time:** {interview['scheduled_date'][:16]}")
                            st.write(f"**Location:** {interview['location']}")
                            st.write(f"**Interviewers:** {', '.join(interview['interviewer_names'])}")

                        if interview.get('meeting_link'):
                            st.write(f"**Meeting Link:** {interview['meeting_link']}")

                        if interview.get('notes'):
                            st.write(f"**Notes:** {interview['notes']}")
            else:
                st.info("No interviews scheduled")

def show_email_management():
    st.header("Email Management")

    candidates_response = api_request("GET", "/candidates")

    if candidates_response and candidates_response.get("success"):
        candidates = candidates_response["data"]

        candidate_options = {
            f"{c['name']} ({c['email']}) - {c['status']}": c['id']
            for c in candidates
        }

        selected_candidate = st.selectbox("Select Candidate", list(candidate_options.keys()))
        candidate_id = candidate_options[selected_candidate]

        email_type = st.selectbox(
            "Email Type",
            ["form_invite", "interview_invite", "rejection"]
        )

        if st.button("Send Email"):
            with st.spinner("Sending email..."):
                response = api_request(
                    "POST",
                    "/emails/send",
                    json={"candidate_id": candidate_id, "email_type": email_type}
                )

                if response and response.get("success"):
                    st.success("Email sent successfully!")
                    st.json(response["data"])

def show_google_forms_sync():
    st.header("Google Forms Sync")

    st.write("Sync responses from Google Forms to update candidate records.")

    sheet_id = st.text_input(
        "Google Sheet ID (optional)",
        help="Leave blank to use the configured sheet ID"
    )

    if st.button("Sync Form Responses"):
        with st.spinner("Syncing..."):
            request_data = {}
            if sheet_id:
                request_data["sheet_id"] = sheet_id

            response = api_request("POST", "/google-forms/sync", json=request_data)

            if response:
                if response.get("success"):
                    st.success(f"Synced {response['synced_count']} responses")

                    if response.get("errors"):
                        st.warning("Some errors occurred:")
                        for error in response["errors"]:
                            st.error(error)
                else:
                    st.error(f"Sync failed: {response.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
