# AI-Driven Candidate Screening Workflow

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FUTUREADY HIRING WORKFLOW                        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: VACANCY DEFINITION                                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  HR Team → Streamlit Dashboard                                      │
│    ├─ Job Role                                                      │
│    ├─ Required Skills                                               │
│    ├─ Experience Level                                              │
│    ├─ Culture Traits                                                │
│    └─ Job Description                                               │
│                                                                      │
│  Status: VACANCY CREATED                                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: CANDIDATE DISCOVERY & RESUME UPLOAD                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  HR Team → Upload Candidate Resumes                                 │
│    ├─ Name                                                          │
│    ├─ Email                                                         │
│    ├─ Phone                                                         │
│    └─ Resume (PDF/TXT)                                              │
│                                                                      │
│  Backend → Parse Resume                                             │
│    ├─ Extract text from PDF                                         │
│    ├─ Parse contact information                                     │
│    └─ Store in database                                             │
│                                                                      │
│  Status: NEW CANDIDATE                                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: AI RESUME SCREENING                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  AI Service (OpenAI/Anthropic)                                      │
│    ├─ Analyze resume against job requirements                       │
│    ├─ Extract skills from resume                                    │
│    ├─ Estimate years of experience                                  │
│    └─ Generate screening score (0-100)                              │
│                                                                      │
│  Screening Output:                                                  │
│    ├─ Screening Score: 85/100                                       │
│    ├─ Extracted Skills: [Python, React, SQL, ...]                   │
│    ├─ Experience: 5 years                                           │
│    └─ Notes: "Strong match for senior developer role..."            │
│                                                                      │
│  Decision: Score >= 70 → SHORTLISTED                                │
│           Score < 70 → REJECTED                                     │
│                                                                      │
│  Status: SCREENED                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: SEND GOOGLE FORM INVITATION                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  HR Team → Select shortlisted candidates                            │
│                                                                      │
│  SendGrid Email Service                                             │
│    ├─ Send personalized email                                       │
│    ├─ Include Google Form link                                      │
│    └─ Log email delivery                                            │
│                                                                      │
│  Email Content:                                                     │
│    - Congratulations message                                        │
│    - Google Form link                                               │
│    - Instructions                                                   │
│                                                                      │
│  Status: FORM_SENT                                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 5: STRUCTURED DATA COLLECTION                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Candidate → Completes Google Form                                  │
│    ├─ Portfolio links (GitHub, LinkedIn, etc.)                      │
│    ├─ Skill self-assessment                                         │
│    ├─ Availability                                                  │
│    ├─ Salary expectations                                           │
│    └─ Additional information                                        │
│                                                                      │
│  Google Form → Saves to Google Sheets                               │
│                                                                      │
│  Backend → Syncs from Google Sheets                                 │
│    ├─ Google Sheets API reads responses                             │
│    ├─ Matches responses to candidates by email                      │
│    └─ Updates database                                              │
│                                                                      │
│  Status: FORM_COMPLETED                                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 6: AI INTERVIEW (20 MINUTES)                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  HR Team → Initiate AI Interview                                    │
│                                                                      │
│  AI Interview Agent generates questions based on:                   │
│    ├─ Resume content                                                │
│    ├─ Google Form responses                                         │
│    ├─ Job requirements                                              │
│    └─ Culture fit criteria                                          │
│                                                                      │
│  Interview Questions (5-7 adaptive questions):                      │
│    1. Technical skills & experience                                 │
│    2. Past projects & problem-solving                               │
│    3. Communication & teamwork                                      │
│    4. Culture fit & values                                          │
│    5. Career goals & motivation                                     │
│                                                                      │
│  Candidate → Provides responses (text/recorded)                     │
│                                                                      │
│  Interview Transcript → Saved to database                           │
│                                                                      │
│  Status: INTERVIEWED                                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 7: AI EVALUATION & RECOMMENDATION                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  AI Evaluation Engine analyzes:                                     │
│    ├─ Interview responses                                           │
│    ├─ Resume data                                                   │
│    ├─ Form responses                                                │
│    └─ Job requirements                                              │
│                                                                      │
│  Scorecard Generation (0-100 for each):                             │
│                                                                      │
│    ┌─────────────────────────────────────────┐                      │
│    │ Skill Fit:              88/100          │                      │
│    │ Communication:          92/100          │                      │
│    │ Problem Solving:        85/100          │                      │
│    │ Culture Alignment:      90/100          │                      │
│    │                                         │                      │
│    │ Overall Score:          89/100          │                      │
│    │                                         │                      │
│    │ Recommendation: STRONG FIT              │                      │
│    └─────────────────────────────────────────┘                      │
│                                                                      │
│  Recommendation Categories:                                         │
│    ├─ Strong Fit (>= 85): Proceed to final interview                │
│    ├─ Moderate Fit (70-84): Consider for final interview            │
│    └─ Not Recommended (< 70): Send rejection email                  │
│                                                                      │
│  Evaluation Notes:                                                  │
│    - Detailed analysis of strengths                                 │
│    - Areas for improvement                                          │
│    - Specific examples from interview                               │
│    - Culture fit assessment                                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
                        ┌─────┴─────┐
                        │           │
           Strong Fit / Moderate Fit │ Not Recommended
                        │           │
                        ↓           ↓
┌─────────────────────────────┐   ┌─────────────────────────────┐
│ STEP 8A: FINAL INTERVIEW    │   │ STEP 8B: REJECTION          │
│ SCHEDULING                   │   │                             │
├─────────────────────────────┤   ├─────────────────────────────┤
│                             │   │                             │
│ HR Team → Schedule Meeting  │   │ Send rejection email        │
│   ├─ Select date/time       │   │   ├─ Polite message         │
│   ├─ Choose location        │   │   ├─ Encourage reapply      │
│   ├─ Assign interviewers    │   │   └─ Thank candidate        │
│   └─ Add meeting link       │   │                             │
│                             │   │ Update status: REJECTED     │
│ SendGrid → Send invitation  │   │                             │
│   ├─ Interview details      │   │ Log in database             │
│   ├─ Calendar invite        │   │                             │
│   ├─ Meeting link           │   └─────────────────────────────┘
│   └─ Preparation tips       │
│                             │
│ Status: RECOMMENDED         │
│                             │
│ Face-to-face interview at   │
│ Futuready office            │
│                             │
└─────────────────────────────┘

```

## Detailed Flow by Role

### HR Team Actions

1. Create job vacancies with detailed requirements
2. Upload candidate resumes
3. Trigger batch resume screening
4. Review screening results
5. Send Google Form invitations to shortlisted candidates
6. Sync Google Form responses
7. Initiate AI interviews
8. Review AI interview results and scorecards
9. Schedule final interviews for recommended candidates
10. Track candidate pipeline and analytics

### Automated System Actions

1. Parse uploaded resumes
2. Screen resumes using AI against job requirements
3. Send automated emails at each stage
4. Sync Google Form responses from Sheets
5. Generate adaptive interview questions
6. Evaluate interview responses
7. Generate candidate scorecards
8. Log all activities and communications
9. Update candidate status throughout pipeline
10. Track metrics and statistics

### Candidate Journey

1. Submit application/resume
2. Resume automatically screened
3. Receive email with Google Form link (if shortlisted)
4. Complete Google Form with detailed information
5. Receive AI interview invitation
6. Complete 20-minute AI interview
7. Receive final interview invitation (if recommended)
8. Attend face-to-face interview at Futuready

## Data Flow

```
Resume (PDF/TXT)
    ↓
Resume Parser
    ↓
Text Extraction
    ↓
Database Storage
    ↓
AI Screening Engine
    ↓
Screening Score + Notes
    ↓
Google Form Invitation
    ↓
Google Form Responses
    ↓
Google Sheets
    ↓
Google Sheets API
    ↓
Database Update
    ↓
AI Interview Questions
    ↓
Candidate Responses
    ↓
AI Evaluation Engine
    ↓
Scorecard + Recommendation
    ↓
Final Interview / Rejection
```

## Integration Points

### Supabase Database
- Stores all candidate and vacancy data
- Manages interview transcripts and evaluations
- Tracks email logs and system activities
- Provides real-time data access

### SendGrid Email Service
- Sends form invitations
- Sends interview invitations
- Sends final interview schedules
- Sends rejection emails
- Tracks delivery status

### Google Sheets API
- Reads form responses
- Syncs candidate data
- Updates candidate records
- Handles batch imports

### AI Provider (OpenAI/Anthropic)
- Screens resumes
- Generates interview questions
- Evaluates interview responses
- Creates scorecards and recommendations

## Status Progression

```
NEW → SCREENED → FORM_SENT → FORM_COMPLETED →
INTERVIEWED → RECOMMENDED → FINAL_INTERVIEW

Or at any stage:
→ REJECTED
```

## Key Metrics Tracked

- Total candidates per vacancy
- Screening pass rate
- Average screening score
- Form completion rate
- Interview completion rate
- Recommendation distribution
- Time to hire
- Email delivery rates
- Candidate pipeline by status

## Security & Privacy

- All data encrypted in transit and at rest
- Row Level Security on database
- Email logs for audit trail
- API key management via environment variables
- No PII exposed in logs
- Secure file upload handling
- CORS protection on API endpoints
