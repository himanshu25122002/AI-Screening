# API Documentation

Complete reference for the AI-Driven Candidate Screening API.

Base URL: `http://localhost:8000` (development) or `https://your-backend.onrender.com` (production)

## Authentication

Currently, the API doesn't require authentication tokens. In production, you should implement API key authentication or OAuth2.

## Endpoints

### Health Check

#### `GET /`

Returns API information.

**Response:**
```json
{
  "message": "AI Candidate Screening API",
  "version": "1.0.0",
  "status": "running"
}
```

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

### Vacancies

#### `POST /vacancies`

Create a new job vacancy.

**Request Body:**
```json
{
  "job_role": "Senior Software Engineer",
  "required_skills": ["Python", "React", "PostgreSQL"],
  "experience_level": "Senior Level",
  "culture_traits": ["Collaborative", "Innovative", "Growth-minded"],
  "description": "We are looking for a senior engineer...",
  "created_by": "hr@futuready.com"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "job_role": "Senior Software Engineer",
    "required_skills": ["Python", "React", "PostgreSQL"],
    "experience_level": "Senior Level",
    "culture_traits": ["Collaborative", "Innovative", "Growth-minded"],
    "description": "We are looking for a senior engineer...",
    "status": "active",
    "created_by": "hr@futuready.com",
    "created_at": "2024-01-15T10:30:00.000Z",
    "updated_at": "2024-01-15T10:30:00.000Z"
  }
}
```

#### `GET /vacancies`

List all vacancies.

**Query Parameters:**
- `status` (optional): Filter by status (`active`, `closed`, `on_hold`)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "job_role": "Senior Software Engineer",
      "status": "active",
      ...
    }
  ]
}
```

#### `GET /vacancies/{vacancy_id}`

Get details of a specific vacancy.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "job_role": "Senior Software Engineer",
    ...
  }
}
```

#### `GET /stats/vacancy/{vacancy_id}`

Get statistics for a vacancy.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_candidates": 25,
    "status_breakdown": {
      "new": 5,
      "screened": 10,
      "form_sent": 8,
      "form_completed": 6,
      "interviewed": 4,
      "recommended": 2
    },
    "recommendation_breakdown": {
      "Strong Fit": 2,
      "Moderate Fit": 1,
      "Not Recommended": 1
    }
  }
}
```

---

### Candidates

#### `POST /candidates`

Add a new candidate with resume.

**Form Data:**
- `vacancy_id`: string (required)
- `name`: string (required)
- `email`: string (required)
- `phone`: string (optional)
- `resume`: file (required, PDF or TXT)

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "vacancy_id": "uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "resume_text": "Extracted resume text...",
    "resume_url": "uploads/john@example.com_resume.pdf",
    "skills": [],
    "experience_years": null,
    "screening_score": null,
    "screening_notes": null,
    "status": "new",
    "created_at": "2024-01-15T10:30:00.000Z",
    "updated_at": "2024-01-15T10:30:00.000Z"
  }
}
```

#### `GET /candidates`

List all candidates.

**Query Parameters:**
- `vacancy_id` (optional): Filter by vacancy
- `status` (optional): Filter by status

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "John Doe",
      "email": "john@example.com",
      "status": "new",
      ...
    }
  ]
}
```

#### `GET /candidates/{candidate_id}`

Get detailed candidate information including form data and interview results.

**Response:**
```json
{
  "success": true,
  "data": {
    "candidate": {
      "id": "uuid",
      "name": "John Doe",
      ...
    },
    "form_data": {
      "portfolio_links": ["https://github.com/johndoe"],
      "skill_self_assessment": {"Python": "Expert", "React": "Intermediate"},
      ...
    },
    "interview_data": {
      "overall_score": 85,
      "recommendation": "Strong Fit",
      ...
    }
  }
}
```

---

### Resume Screening

#### `POST /screening/resume`

Screen a single candidate's resume.

**Request Body:**
```json
{
  "candidate_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "candidate_id": "uuid",
    "screening_score": 85,
    "screening_notes": "Strong technical background...",
    "extracted_skills": ["Python", "React", "SQL"],
    "experience_years": 5
  }
}
```

#### `POST /screening/batch?vacancy_id={vacancy_id}`

Screen all new candidates for a vacancy.

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "candidate_id": "uuid",
      "success": true,
      "data": {
        "screening_score": 85,
        ...
      }
    }
  ]
}
```

---

### AI Interviews

#### `POST /interviews/start`

Generate interview questions for a candidate.

**Request Body:**
```json
{
  "candidate_id": "uuid",
  "vacancy_id": "uuid"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "questions": [
      "Tell me about your experience with Python...",
      "Describe a challenging project...",
      ...
    ],
    "interview_started": true
  }
}
```

#### `POST /interviews/submit`

Submit interview responses and get evaluation.

**Query Parameters:**
- `candidate_id`: uuid
- `vacancy_id`: uuid

**Request Body:**
```json
{
  "responses": [
    {
      "question": "Tell me about your experience...",
      "answer": "I have 5 years of experience..."
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "interview_id": "uuid",
    "candidate_id": "uuid",
    "overall_score": 85,
    "skill_score": 88,
    "communication_score": 90,
    "problem_solving_score": 82,
    "culture_fit_score": 85,
    "recommendation": "Strong Fit",
    "evaluation_notes": "The candidate demonstrated..."
  }
}
```

#### `GET /interviews/{candidate_id}`

Get interview results for a candidate.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "candidate_id": "uuid",
    "vacancy_id": "uuid",
    "interview_transcript": [...],
    "overall_score": 85,
    "recommendation": "Strong Fit",
    ...
  }
}
```

---

### Final Interviews

#### `POST /final-interviews/schedule`

Schedule a final face-to-face interview.

**Request Body:**
```json
{
  "candidate_id": "uuid",
  "vacancy_id": "uuid",
  "scheduled_date": "2024-01-20T14:00:00Z",
  "location": "Futuready Office, Building A",
  "interviewer_names": ["Jane Smith", "Bob Johnson"],
  "meeting_link": "https://meet.google.com/xxx",
  "notes": "Please bring portfolio"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "candidate_id": "uuid",
    "vacancy_id": "uuid",
    "scheduled_date": "2024-01-20T14:00:00Z",
    "location": "Futuready Office, Building A",
    "interviewer_names": ["Jane Smith", "Bob Johnson"],
    "meeting_link": "https://meet.google.com/xxx",
    "status": "scheduled",
    "notes": "Please bring portfolio",
    "created_at": "2024-01-15T10:30:00.000Z",
    "updated_at": "2024-01-15T10:30:00.000Z"
  }
}
```

#### `GET /final-interviews`

List all final interviews.

**Query Parameters:**
- `vacancy_id` (optional): Filter by vacancy

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "candidate_id": "uuid",
      "vacancy_id": "uuid",
      "scheduled_date": "2024-01-20T14:00:00Z",
      "status": "scheduled",
      "candidates": {
        "name": "John Doe",
        "email": "john@example.com"
      },
      "vacancies": {
        "job_role": "Senior Software Engineer"
      },
      ...
    }
  ]
}
```

---

### Email Management

#### `POST /emails/send`

Send email to a candidate.

**Request Body:**
```json
{
  "candidate_id": "uuid",
  "email_type": "form_invite"
}
```

**Email Types:**
- `form_invite`: Send Google Form invitation
- `interview_invite`: Send AI interview invitation
- `rejection`: Send rejection email
- `schedule_confirmation`: Sent automatically when scheduling final interview

**Response:**
```json
{
  "success": true,
  "data": {
    "success": true,
    "message": "Email sent successfully",
    "message_id": "sendgrid-message-id"
  }
}
```

---

### Google Forms Integration

#### `POST /google-forms/sync`

Sync responses from Google Sheets.

**Request Body (optional):**
```json
{
  "sheet_id": "google-sheet-id"
}
```

If `sheet_id` is not provided, uses the configured `GOOGLE_FORM_SHEET_ID`.

**Response:**
```json
{
  "success": true,
  "synced_count": 5,
  "errors": null
}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid input)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error

## Status Values

### Candidate Status
- `new`: Just added, not screened yet
- `screened`: Resume screened by AI
- `form_sent`: Google Form invitation sent
- `form_completed`: Candidate completed Google Form
- `interviewed`: AI interview completed
- `recommended`: Recommended for final interview
- `rejected`: Not moving forward

### Vacancy Status
- `active`: Accepting candidates
- `closed`: No longer accepting candidates
- `on_hold`: Temporarily paused

### Final Interview Status
- `scheduled`: Interview scheduled
- `completed`: Interview completed
- `cancelled`: Interview cancelled
- `rescheduled`: Interview rescheduled

### Recommendation Values
- `Strong Fit`: Highly recommended (score >= 85)
- `Moderate Fit`: Recommended with reservations (score 70-84)
- `Not Recommended`: Not recommended (score < 70)

## Rate Limiting

Currently, no rate limiting is implemented. For production, consider implementing:
- Rate limiting per IP/API key
- Request throttling
- Queue management for batch operations

## Interactive Documentation

When the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

These provide interactive API documentation where you can test endpoints directly.

## Examples

### Complete Workflow Example

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Create vacancy
vacancy = requests.post(f"{BASE_URL}/vacancies", json={
    "job_role": "Software Engineer",
    "required_skills": ["Python", "React"],
    "experience_level": "Mid Level",
    "culture_traits": ["Collaborative"],
    "created_by": "hr@company.com"
}).json()

vacancy_id = vacancy["data"]["id"]

# 2. Add candidate with resume
with open("resume.pdf", "rb") as f:
    candidate = requests.post(
        f"{BASE_URL}/candidates",
        data={
            "vacancy_id": vacancy_id,
            "name": "John Doe",
            "email": "john@example.com"
        },
        files={"resume": f}
    ).json()

candidate_id = candidate["data"]["id"]

# 3. Screen resume
screening = requests.post(
    f"{BASE_URL}/screening/resume",
    json={"candidate_id": candidate_id}
).json()

print(f"Screening Score: {screening['data']['screening_score']}")

# 4. Send form invitation
email = requests.post(
    f"{BASE_URL}/emails/send",
    json={"candidate_id": candidate_id, "email_type": "form_invite"}
).json()

# 5. After form is completed, start interview
interview = requests.post(
    f"{BASE_URL}/interviews/start",
    json={"candidate_id": candidate_id, "vacancy_id": vacancy_id}
).json()

# 6. Submit interview responses
responses = [
    {"question": q, "answer": "Sample answer..."}
    for q in interview["data"]["questions"]
]

evaluation = requests.post(
    f"{BASE_URL}/interviews/submit",
    params={"candidate_id": candidate_id, "vacancy_id": vacancy_id},
    json={"responses": responses}
).json()

print(f"Recommendation: {evaluation['data']['recommendation']}")

# 7. Schedule final interview if recommended
if evaluation["data"]["recommendation"] == "Strong Fit":
    final = requests.post(
        f"{BASE_URL}/final-interviews/schedule",
        json={
            "candidate_id": candidate_id,
            "vacancy_id": vacancy_id,
            "scheduled_date": "2024-01-20T14:00:00Z",
            "location": "Office",
            "interviewer_names": ["HR Manager"]
        }
    ).json()
```

## Support

For API issues or questions, check the backend logs or contact the development team.
