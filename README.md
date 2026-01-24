# AI-Driven Candidate Screening & Interview Workflow

An AI-powered end-to-end hiring workflow system for Futuready that automates candidate screening, conducts AI interviews, and manages the complete hiring pipeline from resume submission to final interview scheduling.

## Features

- **Vacancy Management**: Create and manage job openings with detailed requirements
- **AI Resume Screening**: Automatically parse and score resumes against job requirements
- **Google Forms Integration**: Collect structured candidate data through Google Forms
- **AI-Powered Interviews**: 20-minute adaptive interviews conducted by AI
- **Candidate Evaluation**: Comprehensive scoring on skills, communication, problem-solving, and culture fit
- **Email Automation**: Automated emails via SendGrid for all stages of the hiring process
- **Final Interview Scheduling**: Coordinate face-to-face interviews with recommended candidates
- **Analytics Dashboard**: Track hiring metrics and candidate pipeline

## Architecture

### Backend (FastAPI)
- RESTful API deployed on Render
- Supabase for database management
- SendGrid for email delivery
- Google Sheets API for form data collection
- OpenAI/Anthropic for AI functionality

### Frontend (Streamlit)
- Interactive dashboard for HR team
- Candidate management interface
- Interview scheduling and tracking
- Real-time analytics

## Deployment

### Backend Deployment on Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Use the following settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory**: `backend`

4. Add environment variables in Render dashboard:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_KEY=your_supabase_service_key
   SENDGRID_API_KEY=your_sendgrid_api_key
   SENDGRID_FROM_EMAIL=noreply@yourdomain.com
   SENDGRID_FROM_NAME=Futuready HR
   GOOGLE_SHEETS_CREDENTIALS={"type": "service_account", ...}
   GOOGLE_FORM_SHEET_ID=your_google_sheet_id
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   AI_PROVIDER=openai
   AI_MODEL=gpt-4-turbo-preview
   FRONTEND_URL=your_streamlit_url
   GOOGLE_FORM_URL=your_google_form_url
   ```

5. Deploy and note your backend URL

### Frontend Deployment on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Configure:
   - **Repository**: your-repo
   - **Branch**: main
   - **Main file path**: frontend/streamlit_app.py

5. Click "Advanced settings" and add secrets:
   ```toml
   API_URL = "https://your-backend-url.onrender.com"
   ```

6. Click "Deploy"

## Setup Instructions

### Prerequisites

- Python 3.9+
- Supabase account
- SendGrid account
- Google Cloud Platform account (for Sheets API)
- OpenAI or Anthropic API key

### Local Development

#### Backend

1. Navigate to backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Fill in your environment variables in `.env`

5. Run the backend:
   ```bash
   uvicorn main:app --reload
   ```

Backend will be available at `http://localhost:8000`

#### Frontend

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   pip install -r ../streamlit_requirements.txt
   ```

3. Create `.streamlit/secrets.toml`:
   ```bash
   mkdir -p .streamlit
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

4. Update `API_URL` in `secrets.toml`:
   ```toml
   API_URL = "http://localhost:8000"
   ```

5. Run Streamlit:
   ```bash
   streamlit run streamlit_app.py
   ```

Frontend will be available at `http://localhost:8501`

## API Configuration

### Supabase Setup

1. Create a new Supabase project
2. The database schema is automatically created via migration
3. Copy your project URL and API keys
4. Add them to environment variables

### SendGrid Setup

1. Create a SendGrid account
2. Create an API key with full access to Mail Send
3. Verify your sender email address
4. Add API key and sender email to environment variables

### Google Sheets API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable Google Sheets API
4. Create a service account
5. Download the credentials JSON
6. Share your Google Form response sheet with the service account email
7. Add the credentials JSON to `GOOGLE_SHEETS_CREDENTIALS` environment variable
8. Add the Sheet ID to `GOOGLE_FORM_SHEET_ID` environment variable

### OpenAI/Anthropic Setup

1. Create an account with OpenAI or Anthropic
2. Generate an API key
3. Add to environment variables
4. Set `AI_PROVIDER` to either "openai" or "anthropic"

## Workflow

1. **Create Vacancy**: HR creates a job posting with requirements
2. **Add Candidates**: Upload resumes for candidates
3. **AI Screening**: System automatically screens resumes and scores candidates
4. **Send Form**: Shortlisted candidates receive Google Form link
5. **Sync Responses**: System syncs form responses from Google Sheets
6. **AI Interview**: Candidates complete 20-minute AI interview
7. **Evaluation**: AI generates comprehensive candidate scorecard
8. **Schedule Final Interview**: Recommended candidates are invited for face-to-face interview
9. **Email Notifications**: Automated emails at each stage

## API Endpoints

### Vacancies
- `POST /vacancies` - Create new vacancy
- `GET /vacancies` - List all vacancies
- `GET /vacancies/{id}` - Get vacancy details
- `GET /stats/vacancy/{id}` - Get vacancy statistics

### Candidates
- `POST /candidates` - Add new candidate with resume
- `GET /candidates` - List candidates (filterable)
- `GET /candidates/{id}` - Get candidate details

### Screening
- `POST /screening/resume` - Screen single candidate
- `POST /screening/batch` - Screen all candidates for a vacancy

### Interviews
- `POST /interviews/start` - Generate interview questions
- `POST /interviews/submit` - Submit interview responses and get evaluation
- `GET /interviews/{candidate_id}` - Get interview results

### Final Interviews
- `POST /final-interviews/schedule` - Schedule final interview
- `GET /final-interviews` - List scheduled interviews

### Emails
- `POST /emails/send` - Send email to candidate

### Google Forms
- `POST /google-forms/sync` - Sync form responses from Google Sheets

## Database Schema

### Tables

- **vacancies**: Job postings and requirements
- **candidates**: Candidate information and resume data
- **candidate_forms**: Google Form responses
- **ai_interviews**: Interview transcripts and evaluations
- **final_interviews**: Face-to-face interview schedules
- **email_logs**: Email delivery tracking

## Tech Stack

### Backend
- FastAPI - Web framework
- Supabase - Database and authentication
- SendGrid - Email delivery
- Google Sheets API - Form data collection
- OpenAI/Anthropic - AI functionality
- PyPDF2 - Resume parsing

### Frontend
- Streamlit - Web interface
- Pandas - Data manipulation
- Plotly - Visualizations

## Security

- All database tables have Row Level Security (RLS) enabled
- API keys and credentials stored as environment variables
- CORS configured for frontend-backend communication
- Email logs track all communications

## Future Enhancements

- Video interview capability
- Advanced analytics and reporting
- Integration with ATS systems
- Candidate portal for self-service
- Multi-language support
- Custom evaluation criteria per role
- Interview scheduling automation with calendar integration

## Support

For issues or questions, please contact the development team.

## License

Proprietary - Futuready Internal Use Only
