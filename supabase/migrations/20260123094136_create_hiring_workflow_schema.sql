/*
  # AI-Driven Candidate Screening System Schema

  ## Overview
  This migration creates the complete database schema for the AI-driven candidate screening
  and interview workflow system for Futuready.

  ## New Tables

  ### 1. `vacancies`
  Stores job vacancy information created by HR
  - `id` (uuid, primary key)
  - `job_role` (text) - Job title/role
  - `required_skills` (jsonb) - Array of required skills
  - `experience_level` (text) - Required experience level
  - `culture_traits` (jsonb) - Array of desired culture traits
  - `description` (text) - Detailed job description
  - `status` (text) - active, closed, on_hold
  - `created_by` (text) - HR user email
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)

  ### 2. `candidates`
  Stores candidate information and resume data
  - `id` (uuid, primary key)
  - `vacancy_id` (uuid, foreign key)
  - `name` (text)
  - `email` (text, unique)
  - `phone` (text)
  - `resume_text` (text) - Parsed resume content
  - `resume_url` (text) - Cloud storage URL for resume file
  - `skills` (jsonb) - Extracted skills from resume
  - `experience_years` (numeric)
  - `screening_score` (numeric) - AI screening score (0-100)
  - `screening_notes` (text) - AI screening analysis
  - `status` (text) - new, screened, form_sent, form_completed, interviewed, recommended, rejected
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)

  ### 3. `candidate_forms`
  Stores structured data collected from Google Forms
  - `id` (uuid, primary key)
  - `candidate_id` (uuid, foreign key, unique)
  - `portfolio_links` (jsonb) - Array of portfolio URLs
  - `skill_self_assessment` (jsonb) - Skill ratings by candidate
  - `availability` (text) - When candidate can start
  - `salary_expectations` (text)
  - `additional_info` (jsonb) - Other form responses
  - `form_submitted_at` (timestamptz)
  - `created_at` (timestamptz)

  ### 4. `ai_interviews`
  Stores AI interview sessions and responses
  - `id` (uuid, primary key)
  - `candidate_id` (uuid, foreign key)
  - `vacancy_id` (uuid, foreign key)
  - `interview_transcript` (jsonb) - Q&A pairs from interview
  - `duration_minutes` (numeric)
  - `skill_score` (numeric) - Score out of 100
  - `communication_score` (numeric)
  - `problem_solving_score` (numeric)
  - `culture_fit_score` (numeric)
  - `overall_score` (numeric)
  - `recommendation` (text) - Strong Fit, Moderate Fit, Not Recommended
  - `evaluation_notes` (text) - Detailed AI evaluation
  - `started_at` (timestamptz)
  - `completed_at` (timestamptz)
  - `created_at` (timestamptz)

  ### 5. `final_interviews`
  Manages face-to-face interview scheduling
  - `id` (uuid, primary key)
  - `candidate_id` (uuid, foreign key)
  - `vacancy_id` (uuid, foreign key)
  - `scheduled_date` (timestamptz)
  - `location` (text)
  - `interviewer_names` (jsonb) - Array of interviewer names
  - `meeting_link` (text)
  - `status` (text) - scheduled, completed, cancelled, rescheduled
  - `notes` (text)
  - `created_at` (timestamptz)
  - `updated_at` (timestamptz)

  ### 6. `email_logs`
  Tracks all emails sent through the system
  - `id` (uuid, primary key)
  - `candidate_id` (uuid, foreign key)
  - `email_type` (text) - form_invite, interview_invite, schedule_confirmation, rejection
  - `recipient_email` (text)
  - `subject` (text)
  - `status` (text) - sent, failed, bounced
  - `sendgrid_message_id` (text)
  - `sent_at` (timestamptz)
  - `created_at` (timestamptz)

  ## Security
  - Row Level Security (RLS) enabled on all tables
  - Policies created for authenticated access
*/

-- Create vacancies table
CREATE TABLE IF NOT EXISTS vacancies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_role text NOT NULL,
  required_skills jsonb DEFAULT '[]'::jsonb,
  experience_level text NOT NULL,
  culture_traits jsonb DEFAULT '[]'::jsonb,
  description text,
  status text DEFAULT 'active' CHECK (status IN ('active', 'closed', 'on_hold')),
  created_by text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create candidates table
CREATE TABLE IF NOT EXISTS candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vacancy_id uuid REFERENCES vacancies(id) ON DELETE CASCADE,
  name text NOT NULL,
  email text UNIQUE NOT NULL,
  phone text,
  resume_text text,
  resume_url text,
  skills jsonb DEFAULT '[]'::jsonb,
  experience_years numeric,
  screening_score numeric,
  screening_notes text,
  status text DEFAULT 'new' CHECK (status IN ('new', 'screened', 'form_sent', 'form_completed', 'interviewed', 'recommended', 'rejected')),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create candidate_forms table
CREATE TABLE IF NOT EXISTS candidate_forms (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id uuid UNIQUE REFERENCES candidates(id) ON DELETE CASCADE,
  portfolio_links jsonb DEFAULT '[]'::jsonb,
  skill_self_assessment jsonb DEFAULT '{}'::jsonb,
  availability text,
  salary_expectations text,
  additional_info jsonb DEFAULT '{}'::jsonb,
  form_submitted_at timestamptz,
  created_at timestamptz DEFAULT now()
);

-- Create ai_interviews table
CREATE TABLE IF NOT EXISTS ai_interviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id uuid REFERENCES candidates(id) ON DELETE CASCADE,
  vacancy_id uuid REFERENCES vacancies(id) ON DELETE CASCADE,
  interview_transcript jsonb DEFAULT '[]'::jsonb,
  duration_minutes numeric,
  skill_score numeric,
  communication_score numeric,
  problem_solving_score numeric,
  culture_fit_score numeric,
  overall_score numeric,
  recommendation text CHECK (recommendation IN ('Strong Fit', 'Moderate Fit', 'Not Recommended')),
  evaluation_notes text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz DEFAULT now()
);

-- Create final_interviews table
CREATE TABLE IF NOT EXISTS final_interviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id uuid REFERENCES candidates(id) ON DELETE CASCADE,
  vacancy_id uuid REFERENCES vacancies(id) ON DELETE CASCADE,
  scheduled_date timestamptz,
  location text,
  interviewer_names jsonb DEFAULT '[]'::jsonb,
  meeting_link text,
  status text DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled')),
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create email_logs table
CREATE TABLE IF NOT EXISTS email_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id uuid REFERENCES candidates(id) ON DELETE SET NULL,
  email_type text NOT NULL CHECK (email_type IN ('form_invite', 'interview_invite', 'schedule_confirmation', 'rejection')),
  recipient_email text NOT NULL,
  subject text NOT NULL,
  status text DEFAULT 'sent' CHECK (status IN ('sent', 'failed', 'bounced')),
  sendgrid_message_id text,
  sent_at timestamptz DEFAULT now(),
  created_at timestamptz DEFAULT now()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_candidates_vacancy_id ON candidates(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
CREATE INDEX IF NOT EXISTS idx_ai_interviews_candidate_id ON ai_interviews(candidate_id);
CREATE INDEX IF NOT EXISTS idx_final_interviews_candidate_id ON final_interviews(candidate_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_candidate_id ON email_logs(candidate_id);

-- Enable Row Level Security
ALTER TABLE vacancies ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_forms ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE final_interviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for vacancies
CREATE POLICY "Allow all operations on vacancies for authenticated users"
  ON vacancies FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- RLS Policies for candidates
CREATE POLICY "Allow all operations on candidates for authenticated users"
  ON candidates FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- RLS Policies for candidate_forms
CREATE POLICY "Allow all operations on candidate_forms for authenticated users"
  ON candidate_forms FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- RLS Policies for ai_interviews
CREATE POLICY "Allow all operations on ai_interviews for authenticated users"
  ON ai_interviews FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- RLS Policies for final_interviews
CREATE POLICY "Allow all operations on final_interviews for authenticated users"
  ON final_interviews FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- RLS Policies for email_logs
CREATE POLICY "Allow all operations on email_logs for authenticated users"
  ON email_logs FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);
