# Quick Start Guide

Get the AI-Driven Candidate Screening System up and running in 15 minutes.

## Prerequisites

- Python 3.9 or higher
- Git
- Accounts: Supabase, SendGrid, Google Cloud, OpenAI/Anthropic

## 1. Clone Repository

```bash
git clone <your-repo-url>
cd project
```

## 2. Backend Setup (5 minutes)

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx...
SUPABASE_SERVICE_KEY=eyJxxx...

SENDGRID_API_KEY=SG.xxx
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

GOOGLE_SHEETS_CREDENTIALS={"type":"service_account",...}
GOOGLE_FORM_SHEET_ID=1abc...

OPENAI_API_KEY=sk-xxx
AI_PROVIDER=openai
AI_MODEL=gpt-4-turbo-preview

GOOGLE_FORM_URL=https://forms.google.com/xxx
FRONTEND_URL=http://localhost:8501
```

### Start Backend

```bash
uvicorn main:app --reload
```

Backend runs at: `http://localhost:8000`

## 3. Frontend Setup (3 minutes)

Open a new terminal:

```bash
cd frontend
pip install -r ../streamlit_requirements.txt
```

### Configure Secrets

```bash
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
API_URL = "http://localhost:8000"
EOF
```

### Start Frontend

```bash
streamlit run streamlit_app.py
```

Frontend runs at: `http://localhost:8501`

## 4. Quick Test (2 minutes)

1. Open browser to `http://localhost:8501`
2. Navigate to "Vacancies"
3. Create a test vacancy:
   - Job Role: Software Engineer
   - Skills: Python, React, SQL
   - Experience: Mid Level
   - Culture Traits: Collaborative, Innovative

4. Navigate to "Candidates"
5. Add a test candidate with a sample resume

6. Navigate to "AI Screening"
7. Click "Screen All New Candidates"

8. View results in "Candidates" section

## 5. Test Email (Optional)

1. Navigate to "Email Management"
2. Select a candidate
3. Choose "form_invite"
4. Click "Send Email"
5. Check the recipient's inbox

## Common Issues

### Port Already in Use

If port 8000 or 8501 is taken:

Backend:
```bash
uvicorn main:app --reload --port 8001
```

Frontend:
```bash
streamlit run streamlit_app.py --server.port 8502
```

### Missing Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Database Connection Error

- Verify Supabase credentials
- Check if using SERVICE_KEY (not ANON_KEY)
- Ensure database tables are created

### SendGrid Email Not Sending

- Verify sender email is verified in SendGrid
- Check API key has "Mail Send" permissions
- Look for errors in backend logs

## Next Steps

- Review [README.md](README.md) for full documentation
- See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for production deployment
- Check [WORKFLOW_DIAGRAM.md](WORKFLOW_DIAGRAM.md) to understand the flow

## API Documentation

Once backend is running, visit:
- API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Project Structure

```
project/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Supabase client
│   ├── models.py            # Pydantic models
│   └── services/
│       ├── ai_service.py           # AI screening & interviews
│       ├── email_service.py        # SendGrid integration
│       ├── google_sheets_service.py # Google Sheets sync
│       └── resume_parser.py        # Resume parsing
│
├── frontend/
│   └── streamlit_app.py     # Streamlit dashboard
│
├── requirements.txt         # Backend dependencies
├── streamlit_requirements.txt # Frontend dependencies
└── README.md               # Full documentation
```

## Support

If you encounter issues:

1. Check logs in terminal
2. Verify environment variables
3. Ensure all services are running
4. Review error messages
5. Consult full documentation

Happy hiring!
