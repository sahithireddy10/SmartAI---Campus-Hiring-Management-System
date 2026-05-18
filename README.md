# SmartHire AI — Campus Recruitment Management System

An AI-powered campus hiring platform built with **Python Flask** and **SQLite**. It connects students, companies, and administrators through intelligent job matching, automated pipelines, and real-time analytics.

---

## Features

### Student Portal
- Dashboard with active drives, application status, AI recommendations
- Profile with photo upload, resume upload (PDF/DOC)
- My Applications — tabbed view: Applied / Upcoming Interviews / Offers / Available Drives
- Demo Tests — Resume Matching, Aptitude Test (15 Qs with timer), Coding Test, Mock Interview, Feedback
- AI Match Score for every drive based on CGPA, skills, degree, and year

### Company / Recruiter Portal
- Dashboard with real-time stats: Active Drives, Total Applicants, Shortlisted, Interviews, Offers Made
- Line chart (applications over time) and donut chart (applicants by status)
- Drives section — create, manage, open/close drives with search and filter
- Applicants view — AI-ranked applicants with inline status update and CSV export
- Post New Drive with eligibility criteria (CGPA, degree, skills, year)

### Admin Portal
- Dashboard with platform-wide stats and 4 charts (placements over time, by department, by company, by branch)
- Students section — assessment scores table with View Details modal (Profile / Assessment Scores / Applications tabs)
- Assessment Scores section — resume match, aptitude, technical scores per student
- Companies section — expandable cards showing Active Drives, Applicants, Selected students per company
- New Registrations — add students and companies (only admin can register new users)
- Placement Stats — detailed analytics with 4 charts

### AI Features
- AI Match Score (0–100) based on CGPA, skills, degree, year of passing
- Skill Extractor — detects skills from pasted text
- Interview Prep — role-specific technical, HR, and aptitude questions
- Resume Matching — compares resume skills against job description

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Database | SQLite (smarthire.db) |
| Frontend | HTML5, CSS3, JavaScript, Chart.js 4.4 |
| Fonts & Icons | Inter (Google Fonts), Font Awesome 6 |
| PDF Parsing | pdf.js (client-side, for resume matching) |

---

## Project Structure

```
SmartHire-AI/
├── app.py                  # Main Flask application
├── seed_data.py            # Database seeder (run once to populate demo data)
├── smarthire.db            # SQLite database
├── static/
│   ├── hero.png            # Landing page illustration
│   ├── student_dash.js     # Student dashboard JavaScript
│   └── uploads/            # Student photo and resume uploads
└── templates/
    ├── base.html           # Base layout (navbar, chatbot, global CSS)
    ├── index.html          # Landing page with login
    ├── login.html          # Login page
    ├── student_register.html
    ├── company_register.html
    ├── student_dash.html   # Student dashboard (all sections)
    ├── company_dash.html   # Company dashboard (all sections)
    ├── admin_dash.html     # Admin dashboard (all sections)
    ├── drive_applicants.html
    └── create_drive.html
```

---

## Setup & Run

### Prerequisites
- Python 3.8+
- pip

### Install dependencies
```bash
pip install flask werkzeug
```

### Seed demo data (first time only)
```bash
python seed_data.py
```

### Run the application
```bash
python app.py
```

Open **http://127.0.0.1:5001** in your browser.

---

## Demo Login Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@smarthire.ai | admin123 |
| Student | arjun.sharma@student.edu | pass@123 |
| Student | priya.nair@student.edu | pass@123 |
| Company | hr@tcs.com | tcs@123 |
| Company | campus@google.com | google@123 |
| Company | mscampus@microsoft.com | msft@123 |

> **Note:** Only the admin can register new students and companies. Registration links are not available on the public landing page.

---

## Database Schema

| Table | Key Columns |
|---|---|
| students | id, name, email, pwd, branch, degree, cgpa, skills, photo, resume |
| companies | id, name, email, pwd, industry, location |
| drives | id, company_id, title, role, salary, deadline, req_cgpa, req_skills, status |
| applications | id, student_id, drive_id, status, ai_score, applied_on |

Application status flow: `applied → eligible → test → interview → selected / rejected`

---

## AI Scoring Logic

The AI match score (0–100) is computed as:

| Criteria | Weight |
|---|---|
| CGPA meets requirement | 30 pts |
| Skills match (proportional) | 40 pts |
| Degree matches requirement | 20 pts |
| Year of passing meets requirement | 10 pts |

---

*Built with Flask · SQLite · Chart.js · Font Awesome*
