# Deployment Guide

This guide provides step-by-step instructions for deploying the AI-Driven Candidate Screening System.

## Prerequisites Checklist

Before deploying, ensure you have:

- [ ] Supabase account and project created
- [ ] SendGrid account with verified sender email
- [ ] Google Cloud Platform project with Sheets API enabled
- [ ] OpenAI or Anthropic API key
- [ ] GitHub repository with your code
- [ ] Render account
- [ ] Streamlit Cloud account

## Step 1: Supabase Setup

### 1.1 Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Click "New Project"
3. Enter project details and create
4. Wait for project to be provisioned

### 1.2 Run Database Migration

The database schema was already created when you set up the project. If you need to verify:

1. Go to Supabase dashboard
2. Navigate to SQL Editor
3. You should see tables: vacancies, candidates, candidate_forms, ai_interviews, final_interviews, email_logs

### 1.3 Get API Credentials

1. Go to Project Settings > API
2. Copy these values:
   - Project URL (`SUPABASE_URL`)
   - Anon/Public key (`SUPABASE_ANON_KEY`)
   - Service Role key (`SUPABASE_SERVICE_KEY`)

## Step 2: SendGrid Setup

### 2.1 Create SendGrid Account

1. Go to [sendgrid.com](https://sendgrid.com)
2. Sign up for a free account
3. Verify your email address

### 2.2 Create API Key

1. Go to Settings > API Keys
2. Click "Create API Key"
3. Name it "Futuready Hiring System"
4. Select "Full Access"
5. Copy the API key (`SENDGRID_API_KEY`)

### 2.3 Verify Sender Email

1. Go to Settings > Sender Authentication
2. Click "Verify a Single Sender"
3. Fill in your details
4. Verify the email you receive
5. Use this email as `SENDGRID_FROM_EMAIL`

## Step 3: Google Sheets API Setup

### 3.1 Create Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click "New Project"
3. Name it "Futuready Hiring"
4. Click "Create"

### 3.2 Enable Google Sheets API

1. Go to "APIs & Services" > "Library"
2. Search for "Google Sheets API"
3. Click on it and click "Enable"

### 3.3 Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Name it "hiring-system-sa"
4. Click "Create and Continue"
5. Grant role: "Editor"
6. Click "Done"

### 3.4 Generate Service Account Key

1. Click on the service account you just created
2. Go to "Keys" tab
3. Click "Add Key" > "Create New Key"
4. Choose "JSON"
5. Download the file
6. The entire JSON content will be your `GOOGLE_SHEETS_CREDENTIALS`

### 3.5 Create Google Form and Share Sheet

1. Create a Google Form for candidate data collection
2. Include fields:
   - Email Address
   - Portfolio URL
   - GitHub URL
   - LinkedIn URL
   - Skill ratings
   - When can you start?
   - Expected Salary
3. Link form to Google Sheets
4. Open the connected Google Sheet
5. Copy the Sheet ID from the URL (the long string after `/d/`)
6. Share the sheet with the service account email (found in the JSON file)
7. Give "Editor" access

## Step 4: AI Provider Setup

### Option A: OpenAI

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up/Login
3. Go to API Keys
4. Create new secret key
5. Copy as `OPENAI_API_KEY`
6. Set `AI_PROVIDER=openai`
7. Set `AI_MODEL=gpt-4-turbo-preview`

### Option B: Anthropic

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up/Login
3. Go to API Keys
4. Create new key
5. Copy as `ANTHROPIC_API_KEY`
6. Set `AI_PROVIDER=anthropic`
7. Set `AI_MODEL=claude-3-sonnet-20240229`

## Step 5: Deploy Backend on Render

### 5.1 Create Web Service

1. Go to [render.com](https://render.com)
2. Sign up/Login with GitHub
3. Click "New +" > "Web Service"
4. Connect your GitHub repository
5. Configure:
   - **Name**: futuready-hiring-backend
   - **Environment**: Python 3
   - **Region**: Choose nearest to you
   - **Branch**: main
   - **Root Directory**: backend
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 5.2 Add Environment Variables

Click "Advanced" and add these environment variables:

```
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=your_verified_email@domain.com
SENDGRID_FROM_NAME=Futuready HR
GOOGLE_SHEETS_CREDENTIALS={"type":"service_account",...full json...}
GOOGLE_FORM_SHEET_ID=your_sheet_id
OPENAI_API_KEY=your_openai_key (or ANTHROPIC_API_KEY)
AI_PROVIDER=openai (or anthropic)
AI_MODEL=gpt-4-turbo-preview (or claude-3-sonnet-20240229)
FRONTEND_URL=https://your-app-will-be-here.streamlit.app
GOOGLE_FORM_URL=https://forms.google.com/your-form-id
```

### 5.3 Deploy

1. Click "Create Web Service"
2. Wait for deployment (5-10 minutes)
3. Once deployed, copy your backend URL (e.g., `https://futuready-hiring-backend.onrender.com`)

### 5.4 Test Backend

Visit `https://your-backend-url.onrender.com` and you should see:
```json
{
  "message": "AI Candidate Screening API",
  "version": "1.0.0",
  "status": "running"
}
```

## Step 6: Deploy Frontend on Streamlit Cloud

### 6.1 Prepare Repository

Ensure your repository has:
- `frontend/streamlit_app.py`
- `streamlit_requirements.txt` in root directory

### 6.2 Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Configure:
   - **Repository**: your-username/your-repo
   - **Branch**: main
   - **Main file path**: frontend/streamlit_app.py
   - **App URL**: choose a custom URL

### 6.3 Configure Secrets

1. Click "Advanced settings"
2. In the "Secrets" section, add:
```toml
API_URL = "https://your-backend-url.onrender.com"
```

### 6.4 Deploy

1. Click "Deploy!"
2. Wait for deployment (3-5 minutes)
3. Your app will be live at `https://your-app.streamlit.app`

### 6.5 Update Backend Environment Variable

1. Go back to Render
2. Update `FRONTEND_URL` to your Streamlit URL
3. Backend will automatically redeploy

## Step 7: Verify Deployment

### 7.1 Test Backend Endpoints

```bash
curl https://your-backend-url.onrender.com/health
```

Should return:
```json
{"status": "healthy", "timestamp": "..."}
```

### 7.2 Test Frontend

1. Open your Streamlit app
2. Navigate to "Vacancies"
3. Try creating a test vacancy
4. Check if it appears in the list

### 7.3 Test Email Functionality

1. Add a test candidate
2. Try sending a form invitation email
3. Check if email is received

### 7.4 Test Google Sheets Integration

1. Submit a test response to your Google Form
2. In Streamlit, go to "Google Forms Sync"
3. Click "Sync Form Responses"
4. Verify the response is imported

## Step 8: Production Checklist

- [ ] All environment variables are set correctly
- [ ] Database tables are created
- [ ] SendGrid sender email is verified
- [ ] Google Form is shared with service account
- [ ] Test vacancy can be created
- [ ] Test candidate can be added
- [ ] Emails are being sent successfully
- [ ] Google Forms sync is working
- [ ] AI screening is functional
- [ ] AI interviews are working
- [ ] Final interview scheduling works

## Troubleshooting

### Backend Won't Start

- Check Render logs for errors
- Verify all environment variables are set
- Ensure SUPABASE_SERVICE_KEY (not ANON_KEY) is used

### Emails Not Sending

- Verify SendGrid API key is correct
- Check sender email is verified in SendGrid
- Look for email logs in Supabase `email_logs` table

### Google Sheets Sync Failing

- Verify service account has access to the sheet
- Check GOOGLE_SHEETS_CREDENTIALS is valid JSON
- Ensure Sheet ID is correct

### AI Not Working

- Verify API key for your chosen provider
- Check AI_PROVIDER matches the key you're using
- Ensure you have credits/quota remaining

### Database Errors

- Verify all three Supabase keys are correct
- Check RLS policies are enabled
- Ensure tables were created successfully

## Maintenance

### Monitoring

- Check Render logs regularly
- Monitor SendGrid email delivery rates
- Review Supabase database usage
- Track API usage for AI provider

### Updates

To update the application:

1. Push changes to GitHub
2. Render will automatically redeploy backend
3. Streamlit will automatically redeploy frontend

### Scaling

- Render: Upgrade to paid plan for better performance
- Supabase: Monitor database usage and upgrade if needed
- SendGrid: Upgrade plan if sending more emails
- AI Provider: Upgrade tier for higher rate limits

## Support

If you encounter issues not covered in this guide:

1. Check application logs in Render
2. Review Supabase database for errors
3. Verify all API keys are valid
4. Contact the development team

## Security Notes

- Never commit API keys to GitHub
- Rotate API keys regularly
- Use strong passwords for all accounts
- Enable 2FA where available
- Monitor access logs regularly
- Keep dependencies updated
