# SmartHire AI — Campus Hiring Management System

An AI-powered, multi-college campus placement platform built with **Python Flask**, **MongoDB Atlas**, and **Gemini 2.5 Flash**. It connects colleges, students, and companies through intelligent job matching, automated pipelines, real-time analytics, and voice-enabled AI assistance.

---

## What's New (June 2026)

- ✅ **Multi-College Architecture** — Each college gets its own isolated portal. No data leaks between colleges.
- ✅ **Super Admin Portal** — Platform-wide management of all colleges.
- ✅ **MongoDB Atlas** — Migrated from SQLite to cloud MongoDB.
- ✅ **Gemini 2.5 Flash** — Powers chatbot, career advice, and mock interview feedback.
- ✅ **GitHub OAuth** — Students connect GitHub to showcase projects to recruiters.
- ✅ **Web Speech API** — Browser-native voice for interview questions and chatbot replies.
- ✅ **Sarvam AI** — Hindi translation for chatbot responses.

---

## Architecture

```
Super Admin
    └── Creates / manages Colleges
            └── Each College has:
                    ├── College Admin (staff)
                    ├── Students
                    ├── Companies / Recruiters
                    └── Placement Drives & Applications
```

All data (students, companies, drives, applications) is scoped to a `college_id`. One college cannot see another college's data.

---

## Features

### Super Admin Portal (`/superadmin`)
- Create and manage colleges on the platform
- Activate / deactivate college portals
- View platform-wide stats (total colleges, students, placements)
- Delete a college and all its associated data

### College Registration (`/college/register`)
- Any college can self-register
- Creates an isolated portal with a unique college code
- College admin logs in with their registered email + password

### College Admin Portal
- Dashboard with placement stats, charts, and analytics scoped to their college
- Register students and companies (only admin can register new users)
- View all students with assessment scores and application details
- View all companies with their drives, applicants, and selected students
- Placement Stats — 4 charts (monthly trends, department-wise, company-wise, status breakdown)

### Student Portal
- Dashboard with active drives, AI recommendations, and application status chart
- Profile with photo upload, resume upload (PDF/DOC), and GitHub projects
- My Applications — tabbed view: Applied / Upcoming Interviews / Offers / Available Drives
- Demo Tests — Resume Matching, Aptitude Test (15 Qs with timer), Coding Test, Mock Interview, Feedback
- AI Match Score (0–100) for every drive based on CGPA, skills, degree, year
- **AI Career Advice** — Gemini-powered advice on skills, resume tips, salary negotiation
- **🔊 Voice** — Listen to chatbot replies and interview questions via browser speech synthesis

### Company / Recruiter Portal
- Dashboard with real-time stats scoped to their college
- Create and manage placement drives with eligibility criteria
- Applicant ranking by AI match score
- Inline status update (Applied → Eligible → Test → Interview → Selected / Rejected)
- CSV export of applicants
- View student GitHub projects directly from applicant list

### AI Features
- **Gemini 2.5 Flash Chatbot** — Context-aware campus hiring assistant with Hindi toggle
- **AI Match Score** — CGPA (30) + Skills (40) + Degree (20) + Year (10) = 100 pts
- **Career Advice Modal** — Personalized advice based on student profile
- **Mock Interview Feedback** — Gemini evaluates HR answers with strengths, improvements, score
- **Skill Extractor** — Auto-detects skills from pasted resume text
- **Interview Prep** — Role-specific Technical, HR, and Aptitude question banks

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Database | MongoDB Atlas (PyMongo) |
| AI | Gemini 2.5 Flash (Google AI Studio) |
| Voice | Browser Web Speech API + Sarvam AI (Hindi) |
| Auth | Session-based + GitHub OAuth |
| Frontend | HTML5, CSS3, JavaScript, Chart.js 4.4 |
| Fonts & Icons | Inter (Google Fonts), Font Awesome 6 |

---

## Project Structure

```
SmartHire-AI/
├── app.py                       # Main Flask application
├── seed_data.py                 # Database seeder (run once)
├── .env                         # API keys and config (not committed)
├── .gitignore
├── static/
│   ├── hero.png
│   ├── student_dash.js          # Student dashboard JavaScript
│   └── uploads/                 # Student photo and resume uploads
└── templates/
    ├── base.html                # Base layout (navbar, chatbot, global CSS)
    ├── index.html               # Landing page
    ├── login.html               # Login page (student / company / college admin)
    ├── college_register.html    # College self-registration
    ├── superadmin.html          # Super admin portal
    ├── student_register.html
    ├── company_register.html
    ├── student_dash.html        # Student dashboard
    ├── company_dash.html        # Company dashboard
    ├── admin_dash.html          # College admin dashboard
    ├── drive_applicants.html    # Applicant management
    └── create_drive.html
```

---

## Setup & Run

### Prerequisites
- Python 3.8+
- MongoDB Atlas account (free tier works)
- Google AI Studio API key (for Gemini)

### 1. Install dependencies
```bash
pip install flask werkzeug pymongo[srv] python-dotenv requests
```

### 2. Configure `.env`
```env
FLASK_SECRET_KEY=your_secret_key

# Super Admin
SUPER_ADMIN_EMAIL=superadmin@smarthire.ai
SUPER_ADMIN_PWD=super@123

# MongoDB Atlas
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=Cluster0

# Google Gemini
GEMINI_API_KEY=your_gemini_api_key

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# ElevenLabs (optional TTS upgrade)
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL

# Sarvam AI (Hindi translation)
SARVAM_API_KEY=your_sarvam_key
SARVAM_LANGUAGE=hi-IN
```

### 3. Seed demo data
```bash
python seed_data.py
```

### 4. Run
```bash
python app.py
```

Open **http://127.0.0.1:5001** in your browser.

---

## Login Credentials

### Super Admin
| Email | Password | URL |
|---|---|---|
| superadmin@smarthire.ai | super@123 | `/superadmin/login` |

### Demo College — Woxsen University
| Role | Email | Password |
|---|---|---|
| College Admin | admin@woxsen.edu.in | woxsen@123 |
| Student | arjun.sharma@student.edu | pass@123 |
| Student | priya.nair@student.edu | pass@123 |
| Company | hr@tcs.com | tcs@123 |
| Company | campus@google.com | google@123 |
| Company | mscampus@microsoft.com | msft@123 |

> **Note:** Only the College Admin can register new students and companies within their college portal.

---

## Database Design

### MongoDB Collections

| Collection | Key Fields |
|---|---|
| `colleges` | `_id`, `name`, `code`, `email`, `pwd`, `active`, `created` |
| `students` | `_id`, `college_id`, `name`, `email`, `cgpa`, `skills`, `github_repos[]` |
| `companies` | `_id`, `college_id`, `name`, `email`, `industry` |
| `drives` | `_id`, `college_id`, `company_id`, `title`, `role`, `req_cgpa`, `req_skills`, `status` |
| `applications` | `_id`, `student_id`, `drive_id`, `status`, `ai_score`, `applied_on` |

### Relationships
```
colleges._id  ←── students.college_id
colleges._id  ←── companies.college_id
colleges._id  ←── drives.college_id
companies._id ←── drives.company_id
students._id  ←── applications.student_id
drives._id    ←── applications.drive_id
```

### Application Status Flow
```
applied → eligible → test → interview → selected
                                      ↘ rejected
```

---

## AI Scoring Logic

| Criteria | Weight |
|---|---|
| CGPA meets requirement | 30 pts |
| Skills match (proportional) | 40 pts |
| Degree matches requirement | 20 pts |
| Year of passing meets requirement | 10 pts |
| **Total** | **100 pts** |

---

## GitHub OAuth Setup

1. Go to [github.com/settings/developers](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set callback URL to: `http://127.0.0.1:5001/auth/github/callback`
4. Copy Client ID and Secret to `.env`

---

*Built with Flask · MongoDB Atlas · Gemini 2.5 Flash · Chart.js · Font Awesome*
