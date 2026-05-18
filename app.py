from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "smarthire_ai_secret_2024"
DB = os.path.join(os.path.dirname(__file__), "smarthire.db")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_PHOTO  = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_RESUME = {"pdf", "doc", "docx"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── DB ───────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, pwd TEXT,
        phone TEXT, dob TEXT, branch TEXT, degree TEXT,
        year INTEGER, cgpa REAL DEFAULT 0,
        p12 REAL DEFAULT 0, p10 REAL DEFAULT 0,
        skills TEXT DEFAULT '', bio TEXT DEFAULT '',
        gender TEXT DEFAULT '', location TEXT DEFAULT '',
        photo TEXT DEFAULT '', resume TEXT DEFAULT '',
        resume_uploaded_on TEXT DEFAULT '',
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, pwd TEXT,
        phone TEXT, location TEXT, industry TEXT,
        website TEXT DEFAULT '', about TEXT DEFAULT '',
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS drives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER, title TEXT, role TEXT,
        location TEXT, salary REAL, deadline TEXT,
        description TEXT DEFAULT '',
        req_cgpa REAL DEFAULT 0, req_degree TEXT DEFAULT '',
        req_skills TEXT DEFAULT '', req_year INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        created TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER, drive_id INTEGER,
        status TEXT DEFAULT 'applied',
        ai_score REAL DEFAULT 0,
        applied_on TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, drive_id)
    );
    """)
    conn.commit(); conn.close()

# ─── Migrate existing DB (add new columns if missing) ─────────────────────────
def migrate_db():
    conn = get_db(); c = conn.cursor()
    existing = [row[1] for row in c.execute("PRAGMA table_info(students)").fetchall()]
    for col, defn in [
        ("gender",             "TEXT DEFAULT ''"),
        ("location",           "TEXT DEFAULT ''"),
        ("photo",              "TEXT DEFAULT ''"),
        ("resume",             "TEXT DEFAULT ''"),
        ("resume_uploaded_on", "TEXT DEFAULT ''"),
    ]:
        if col not in existing:
            c.execute(f"ALTER TABLE students ADD COLUMN {col} {defn}")
    conn.commit(); conn.close()

# ─── AI helpers ───────────────────────────────────────────────────────────────
def ai_match_score(student, drive):
    score = 0
    # CGPA (30 pts)
    if student['cgpa'] >= drive['req_cgpa']:
        score += 30
    elif student['cgpa'] >= drive['req_cgpa'] - 0.5:
        score += 15
    # Skills (40 pts)
    req = [s.strip().lower() for s in (drive['req_skills'] or '').split(',') if s.strip()]
    stu = [s.strip().lower() for s in (student['skills'] or '').split(',') if s.strip()]
    if req:
        matched = sum(1 for r in req if any(r in s or s in r for s in stu))
        score += int((matched / len(req)) * 40)
    else:
        score += 30
    # Degree (20 pts)
    if not drive['req_degree'] or student['degree'] == drive['req_degree']:
        score += 20
    else:
        score += 5
    # Year (10 pts)
    if not drive['req_year'] or student['year'] >= drive['req_year']:
        score += 10
    return round(score, 1)

def ai_extract_skills(text):
    known = ["Python","Java","JavaScript","C++","C","React","Node.js","Django","Flask",
             "SQL","MongoDB","PostgreSQL","MySQL","Machine Learning","Deep Learning",
             "TensorFlow","PyTorch","NLP","Data Science","AWS","Docker","Kubernetes",
             "Git","HTML","CSS","TypeScript","REST API","Pandas","NumPy","Scikit-learn",
             "R","Android","iOS","Swift","Kotlin","Spring Boot","FastAPI","Figma",
             "Power BI","Tableau","Excel","Linux","Redis","GraphQL"]
    return [k for k in known if k.lower() in text.lower()]

def ai_questions(role, rtype="Technical"):
    bank = {
        "Technical": {
            "ml":  ["Explain overfitting and how to prevent it.",
                    "What is the bias-variance tradeoff?",
                    "How does gradient descent work?",
                    "Explain supervised vs unsupervised learning.",
                    "What is cross-validation?"],
            "web": ["What is the JavaScript event loop?",
                    "Explain REST vs GraphQL.",
                    "What are React hooks?",
                    "How does HTTP caching work?",
                    "Explain CORS."],
            "default": ["Explain stack vs queue with examples.",
                        "What is Big O notation?",
                        "Describe a challenging project you built.",
                        "Explain SOLID principles.",
                        "What is the difference between process and thread?"]
        },
        "HR": ["Tell me about yourself.",
               "Where do you see yourself in 5 years?",
               "Describe a conflict you resolved in a team.",
               "What are your greatest strengths and weaknesses?",
               "Why do you want to join our company?"],
        "Aptitude": ["A train travels 60 km/h for 2 hours. Distance?",
                     "5 workers finish a job in 10 days. Time for 10 workers?",
                     "Next: 2, 6, 12, 20, 30, ?",
                     "20% profit on ₹500 cost price. Selling price?",
                     "Simplify: (25×4)÷(5×2)"]
    }
    if rtype == "HR":      return bank["HR"]
    if rtype == "Aptitude": return bank["Aptitude"]
    r = role.lower()
    if any(k in r for k in ["ml","ai","data","machine"]): return bank["Technical"]["ml"]
    if any(k in r for k in ["web","front","back","full"]): return bank["Technical"]["web"]
    return bank["Technical"]["default"]

# ─── Routes ───────────────────────────────────────────────────────────────────
# Run migrations on every startup (safe — only adds missing columns)
with app.app_context():
    init_db()
    migrate_db()

@app.route("/")
def index():
    db = get_db()
    stats = {
        "students":  db.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"],
        "companies": db.execute("SELECT COUNT(*) as c FROM companies").fetchone()["c"],
        "drives":    db.execute("SELECT COUNT(*) as c FROM drives WHERE status='active'").fetchone()["c"],
        "placed":    db.execute("SELECT COUNT(DISTINCT student_id) as c FROM applications WHERE status='selected'").fetchone()["c"],
    }
    db.close()
    return render_template("index.html", stats=stats)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        pwd   = request.form.get("pwd","").strip()
        role  = request.form.get("role","")
        if role == "admin":
            if email == "admin@smarthire.ai" and pwd == "admin123":
                session.update({"uid":0,"role":"admin","name":"Admin","email":email})
                return redirect(url_for("admin_dash"))
            return render_template("login.html", error="Invalid admin credentials.")
        table = "students" if role == "student" else "companies"
        db = get_db()
        row = db.execute(f"SELECT * FROM {table} WHERE email=?", (email,)).fetchone()
        db.close()
        if not row: return render_template("login.html", error="Account not found.")
        if row["pwd"] != pwd: return render_template("login.html", error="Wrong password.")
        session.update({"uid":row["id"],"role":role,"name":row["name"],"email":email})
        return redirect(url_for("student_dash" if role=="student" else "company_dash"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("index"))

@app.route("/register/student", methods=["GET","POST"])
def student_register():
    if request.method == "POST":
        f = request.form
        db = get_db()
        try:
            db.execute("""INSERT INTO students (name,email,pwd,phone,dob,branch,degree,year,cgpa,p12,p10,skills,bio)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f["name"],f["email"],f["pwd"],f["phone"],f["dob"],
                 f["branch"],f["degree"],int(f["year"]),
                 float(f["cgpa"]),float(f["p12"]),float(f["p10"]),
                 f.get("skills",""),f.get("bio","")))
            db.commit(); db.close()
            return render_template("student_register.html", success=True)
        except sqlite3.IntegrityError:
            db.close()
            return render_template("student_register.html", error="Email already registered.")
    return render_template("student_register.html")

@app.route("/register/company", methods=["GET","POST"])
def company_register():
    if request.method == "POST":
        f = request.form
        db = get_db()
        try:
            db.execute("""INSERT INTO companies (name,email,pwd,phone,location,industry,website,about)
                VALUES (?,?,?,?,?,?,?,?)""",
                (f["name"],f["email"],f["pwd"],f["phone"],
                 f["location"],f["industry"],f.get("website",""),f.get("about","")))
            db.commit(); db.close()
            return render_template("company_register.html", success=True)
        except sqlite3.IntegrityError:
            db.close()
            return render_template("company_register.html", error="Email already registered.")
    return render_template("company_register.html")

@app.route("/student")
def student_dash():
    if session.get("role") != "student": return redirect(url_for("login"))
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (session["uid"],)).fetchone()
    drives_raw = db.execute("""
        SELECT d.*, c.name as company_name, c.industry,
               a.id as app_id, a.status as app_status, a.ai_score
        FROM drives d JOIN companies c ON d.company_id=c.id
        LEFT JOIN applications a ON a.drive_id=d.id AND a.student_id=?
        WHERE d.status='active' ORDER BY d.created DESC
    """, (session["uid"],)).fetchall()

    # Compute AI score for every drive (use stored score if already applied)
    drives = []
    for d in drives_raw:
        row = dict(d)
        if row['app_id'] and row['ai_score']:
            row['computed_score'] = row['ai_score']
        else:
            row['computed_score'] = ai_match_score(student, d)
        drives.append(row)
    my_apps = db.execute("""
        SELECT a.*, d.title, d.role, d.salary, d.location as job_loc, c.name as company_name
        FROM applications a JOIN drives d ON a.drive_id=d.id
        JOIN companies c ON d.company_id=c.id
        WHERE a.student_id=? ORDER BY a.applied_on DESC
    """, (session["uid"],)).fetchall()

    # AI recommendations: score all unapplied drives and return top 3
    unapplied   = [d for d in drives if not d["app_id"]]
    recommendations = []
    for d in unapplied:
        score = d["computed_score"]
        recommendations.append({"drive": d, "score": score})
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    recommendations = recommendations[:3]
    recommendations = recommendations[:3]

    # Application status counts for pie chart
    status_counts = {"applied": 0, "eligible": 0, "test": 0, "interview": 0, "selected": 0, "rejected": 0}
    for a in my_apps:
        s = a["status"]
        if s in status_counts:
            status_counts[s] += 1

    db.close()
    skills_list = [s.strip() for s in (student["skills"] or "").split(",") if s.strip()]
    return render_template("student_dash.html", student=student,
                           drives=drives, my_apps=my_apps, skills_list=skills_list,
                           recommendations=recommendations, status_counts=status_counts)

@app.route("/apply/<int:drive_id>", methods=["POST"])
def apply(drive_id):
    if session.get("role") != "student": return redirect(url_for("login"))
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (session["uid"],)).fetchone()
    drive   = db.execute("SELECT * FROM drives WHERE id=?", (drive_id,)).fetchone()
    score   = ai_match_score(student, drive)
    try:
        db.execute("INSERT INTO applications (student_id,drive_id,ai_score) VALUES (?,?,?)",
                   (session["uid"], drive_id, score))
        db.commit()
    except sqlite3.IntegrityError:
        pass
    db.close()
    return redirect(url_for("student_dash"))

@app.route("/company")
def company_dash():
    if session.get("role") != "company": return redirect(url_for("login"))
    db = get_db()
    company = db.execute("SELECT * FROM companies WHERE id=?", (session["uid"],)).fetchone()
    drives  = db.execute("""
        SELECT d.*,
               COUNT(a.id) as app_count,
               COUNT(DISTINCT CASE WHEN a.status='selected'  THEN a.student_id END) as selected_count,
               COUNT(DISTINCT CASE WHEN a.status='interview' THEN a.student_id END) as interview_count,
               SUM(CASE WHEN a.status='eligible'  THEN 1 ELSE 0 END) as eligible_count,
               SUM(CASE WHEN a.status='test'      THEN 1 ELSE 0 END) as test_count,
               SUM(CASE WHEN a.status='rejected'  THEN 1 ELSE 0 END) as rejected_count
        FROM drives d LEFT JOIN applications a ON a.drive_id=d.id
        WHERE d.company_id=? GROUP BY d.id ORDER BY d.created DESC
    """, (session["uid"],)).fetchall()

    # Aggregate stats
    total_apps       = sum(d["app_count"]       or 0 for d in drives)
    total_selected   = sum(d["selected_count"]  or 0 for d in drives)
    total_interviews = sum(d["interview_count"] or 0 for d in drives)
    total_offers     = total_selected  # offers = selected

    stats = {
        "drives":     len(drives),
        "apps":       total_apps,
        "selected":   total_selected,
        "interviews": total_interviews,
        "offers":     total_offers,
    }

    # Status breakdown for donut chart (real data)
    status_rows = db.execute("""
        SELECT a.status, COUNT(*) as cnt
        FROM applications a JOIN drives d ON a.drive_id=d.id
        WHERE d.company_id=? GROUP BY a.status
    """, (session["uid"],)).fetchall()
    status_counts = {"applied":0,"eligible":0,"test":0,"interview":0,"selected":0,"rejected":0}
    for row in status_rows:
        if row["status"] in status_counts:
            status_counts[row["status"]] = row["cnt"]

    # Applications over time — group by applied_on date (last 30 days)
    timeline = db.execute("""
        SELECT DATE(a.applied_on) as day, COUNT(*) as cnt,
               SUM(CASE WHEN a.status IN ('eligible','test','interview','selected') THEN 1 ELSE 0 END) as shortlisted
        FROM applications a JOIN drives d ON a.drive_id=d.id
        WHERE d.company_id=?
        GROUP BY DATE(a.applied_on) ORDER BY day ASC LIMIT 30
    """, (session["uid"],)).fetchall()
    timeline_labels    = [r["day"] for r in timeline]
    timeline_apps      = [r["cnt"] for r in timeline]
    timeline_shortlist = [r["shortlisted"] for r in timeline]

    db.close()
    return render_template("company_dash.html",
        company=company, drives=drives, stats=stats,
        status_counts=status_counts,
        timeline_labels=timeline_labels,
        timeline_apps=timeline_apps,
        timeline_shortlist=timeline_shortlist
    )

@app.route("/drive/create", methods=["GET","POST"])
def create_drive():
    if session.get("role") != "company": return redirect(url_for("login"))
    if request.method == "POST":
        f = request.form
        db = get_db()
        db.execute("""INSERT INTO drives (company_id,title,role,location,salary,deadline,
                      description,req_cgpa,req_degree,req_skills,req_year) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (session["uid"],f["title"],f["role"],f["location"],float(f["salary"]),
             f["deadline"],f.get("description",""),float(f.get("req_cgpa",0)),
             f.get("req_degree",""),f.get("req_skills",""),int(f.get("req_year",0))))
        db.commit(); db.close()
        return redirect(url_for("company_dash") + "?section=drives")
    return render_template("create_drive.html")

@app.route("/drive/<int:drive_id>/toggle", methods=["POST"])
def toggle_drive(drive_id):
    if session.get("role") != "company": return redirect(url_for("login"))
    db = get_db()
    d = db.execute("SELECT status FROM drives WHERE id=? AND company_id=?", (drive_id, session["uid"])).fetchone()
    if d:
        new_status = "closed" if d["status"] == "active" else "active"
        db.execute("UPDATE drives SET status=? WHERE id=?", (new_status, drive_id))
        db.commit()
    db.close()
    return redirect(url_for("company_dash") + "?section=drives")

@app.route("/drive/<int:drive_id>/applicants")
def drive_applicants(drive_id):
    if session.get("role") != "company": return redirect(url_for("login"))
    db = get_db()
    drive = db.execute("SELECT * FROM drives WHERE id=? AND company_id=?",
                       (drive_id, session["uid"])).fetchone()
    if not drive: return redirect(url_for("company_dash"))
    apps = db.execute("""
        SELECT a.*, s.name as sname, s.email as semail, s.cgpa, s.branch,
               s.degree, s.skills, s.phone
        FROM applications a JOIN students s ON a.student_id=s.id
        WHERE a.drive_id=? ORDER BY a.ai_score DESC
    """, (drive_id,)).fetchall()
    db.close()
    return render_template("drive_applicants.html", drive=drive, apps=apps)

@app.route("/app/<int:app_id>/status", methods=["POST"])
def update_status(app_id):
    if session.get("role") != "company": return redirect(url_for("login"))
    status = request.form.get("status")
    db = get_db()
    db.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    db.commit()
    row = db.execute("SELECT drive_id FROM applications WHERE id=?", (app_id,)).fetchone()
    db.close()
    return redirect(url_for("drive_applicants", drive_id=row["drive_id"]))

@app.route("/admin")
def admin_dash():
    if session.get("role") != "admin": return redirect(url_for("login"))
    db = get_db()

    # Core stats
    stats = {
        "students":  db.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"],
        "companies": db.execute("SELECT COUNT(*) as c FROM companies").fetchone()["c"],
        "drives":    db.execute("SELECT COUNT(*) as c FROM drives").fetchone()["c"],
        "apps":      db.execute("SELECT COUNT(*) as c FROM applications").fetchone()["c"],
        "selected":  db.execute("SELECT COUNT(DISTINCT student_id) as c FROM applications WHERE status='selected'").fetchone()["c"],
    }
    placement_rate = min(round((stats["selected"] / stats["students"] * 100), 1), 100.0) if stats["students"] else 0

    # Recent drives with app count
    drives = db.execute("""SELECT d.*, c.name as company_name, COUNT(a.id) as app_count
        FROM drives d JOIN companies c ON d.company_id=c.id
        LEFT JOIN applications a ON a.drive_id=d.id
        GROUP BY d.id ORDER BY d.created DESC LIMIT 10""").fetchall()

    # All students with their application count and best AI score
    students = db.execute("""
        SELECT s.*, COUNT(a.id) as app_count,
               MAX(a.ai_score) as best_score
        FROM students s
        LEFT JOIN applications a ON a.student_id=s.id
        GROUP BY s.id ORDER BY s.created DESC
    """).fetchall()

    # Student applications detail (for modal)
    student_apps = {}
    for s in students:
        apps = db.execute("""
            SELECT a.status, a.ai_score, a.applied_on, d.title, d.role, c.name as company_name
            FROM applications a JOIN drives d ON a.drive_id=d.id
            JOIN companies c ON d.company_id=c.id
            WHERE a.student_id=? ORDER BY a.applied_on DESC
        """, (s["id"],)).fetchall()
        student_apps[s["id"]] = [dict(a) for a in apps]

    # Companies with their drive/applicant/selected counts + detail data
    companies = db.execute("""
        SELECT co.*,
               COUNT(DISTINCT d.id) as drive_count,
               COUNT(a.id) as app_count,
               COUNT(DISTINCT CASE WHEN a.status='selected' THEN a.student_id END) as selected_count
        FROM companies co
        LEFT JOIN drives d ON d.company_id=co.id
        LEFT JOIN applications a ON a.drive_id=d.id
        GROUP BY co.id ORDER BY co.created DESC
    """).fetchall()

    # Per-company detail data for expandable panels
    company_drives = {}
    company_applicants = {}
    company_selected = {}
    for co in companies:
        cid = co["id"]
        company_drives[cid] = db.execute("""
            SELECT d.*, COUNT(a.id) as app_count
            FROM drives d LEFT JOIN applications a ON a.drive_id=d.id
            WHERE d.company_id=? GROUP BY d.id ORDER BY d.created DESC
        """, (cid,)).fetchall()
        company_applicants[cid] = db.execute("""
            SELECT s.name, s.email, s.branch, s.cgpa, a.status, a.ai_score, a.applied_on, d.title as drive_title
            FROM applications a JOIN students s ON a.student_id=s.id
            JOIN drives d ON a.drive_id=d.id
            WHERE d.company_id=? ORDER BY a.applied_on DESC
        """, (cid,)).fetchall()
        company_selected[cid] = [r for r in company_applicants[cid] if r["status"] == "selected"]

    # Branch-wise placements
    branch_stats = db.execute("""SELECT s.branch, COUNT(a.id) as placed
        FROM applications a JOIN students s ON a.student_id=s.id
        WHERE a.status='selected' GROUP BY s.branch ORDER BY placed DESC""").fetchall()

    # Placements over time (monthly)
    monthly = db.execute("""
        SELECT strftime('%Y-%m', a.applied_on) as month, COUNT(*) as apps,
               SUM(CASE WHEN a.status='selected' THEN 1 ELSE 0 END) as placed
        FROM applications a GROUP BY month ORDER BY month ASC LIMIT 12
    """).fetchall()
    monthly_labels  = [r["month"] for r in monthly]
    monthly_apps    = [r["apps"]   for r in monthly]
    monthly_placed  = [r["placed"] for r in monthly]

    # Top recruiting companies
    top_companies = db.execute("""
        SELECT c.name, COUNT(a.id) as hired
        FROM applications a JOIN drives d ON a.drive_id=d.id
        JOIN companies c ON d.company_id=c.id
        WHERE a.status='selected' GROUP BY c.id ORDER BY hired DESC LIMIT 5
    """).fetchall()

    # Status breakdown
    status_rows = db.execute("SELECT status, COUNT(*) as cnt FROM applications GROUP BY status").fetchall()
    status_counts = {"applied":0,"eligible":0,"test":0,"interview":0,"selected":0,"rejected":0}
    for r in status_rows:
        if r["status"] in status_counts:
            status_counts[r["status"]] = r["cnt"]

    # Recent registrations (students + companies combined)
    recent_students  = db.execute("SELECT id, name, email, 'student' as type, created FROM students ORDER BY created DESC LIMIT 5").fetchall()
    recent_companies = db.execute("SELECT id, name, email, 'company' as type, created FROM companies ORDER BY created DESC LIMIT 5").fetchall()
    recent_regs = sorted(list(recent_students) + list(recent_companies), key=lambda x: x["created"], reverse=True)[:10]

    db.close()
    return render_template("admin_dash.html",
        stats=stats, placement_rate=placement_rate,
        drives=drives, students=students, companies=companies,
        student_apps=student_apps,
        company_drives=company_drives,
        company_applicants=company_applicants,
        company_selected=company_selected,
        branch_stats=branch_stats,
        monthly_labels=monthly_labels, monthly_apps=monthly_apps, monthly_placed=monthly_placed,
        top_companies=top_companies, status_counts=status_counts,
        recent_regs=recent_regs
    )

@app.route("/admin/register/student", methods=["GET","POST"])
def admin_register_student():
    if session.get("role") != "admin": return redirect(url_for("login"))
    if request.method == "POST":
        f = request.form
        db = get_db()
        try:
            db.execute("""INSERT INTO students (name,email,pwd,phone,dob,branch,degree,year,cgpa,p12,p10,skills,bio)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f["name"],f["email"],f["pwd"],f["phone"],f["dob"],
                 f["branch"],f["degree"],int(f["year"]),
                 float(f["cgpa"]),float(f["p12"]),float(f["p10"]),
                 f.get("skills",""),f.get("bio","")))
            db.commit(); db.close()
            return redirect(url_for("admin_dash") + "?section=registrations&msg=student_added")
        except Exception as e:
            db.close()
            return render_template("admin_dash.html", reg_error=str(e))
    return redirect(url_for("admin_dash") + "?section=registrations")

@app.route("/admin/register/company", methods=["GET","POST"])
def admin_register_company():
    if session.get("role") != "admin": return redirect(url_for("login"))
    if request.method == "POST":
        f = request.form
        db = get_db()
        try:
            db.execute("""INSERT INTO companies (name,email,pwd,phone,location,industry,website,about)
                VALUES (?,?,?,?,?,?,?,?)""",
                (f["name"],f["email"],f["pwd"],f["phone"],
                 f["location"],f["industry"],f.get("website",""),f.get("about","")))
            db.commit(); db.close()
            return redirect(url_for("admin_dash") + "?section=registrations&msg=company_added")
        except Exception as e:
            db.close()
            return redirect(url_for("admin_dash") + "?section=registrations&err="+str(e))
    return redirect(url_for("admin_dash") + "?section=registrations")

# ── AI API endpoints ──
@app.route("/ai/match/<int:drive_id>")
def ai_match(drive_id):
    if session.get("role") != "student": return jsonify({"error":"unauthorized"})
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (session["uid"],)).fetchone()
    drive   = db.execute("SELECT * FROM drives WHERE id=?", (drive_id,)).fetchone()
    db.close()
    if not drive: return jsonify({"error":"not found"})
    score = ai_match_score(student, drive)
    req = [s.strip() for s in (drive["req_skills"] or "").split(",") if s.strip()]
    stu = [s.strip().lower() for s in (student["skills"] or "").split(",") if s.strip()]
    matched = [r for r in req if any(r.lower() in s or s in r.lower() for s in stu)]
    missing = [r for r in req if r not in matched]
    return jsonify({"score":score,"matched":matched,"missing":missing,"cgpa_ok":student["cgpa"]>=drive["req_cgpa"]})

@app.route("/ai/questions")
def get_questions():
    role  = request.args.get("role","Software Engineer")
    rtype = request.args.get("round","Technical")
    return jsonify({"questions": ai_questions(role, rtype), "role":role, "round":rtype})

@app.route("/ai/extract", methods=["POST"])
def extract_skills():
    text   = request.json.get("text","")
    skills = ai_extract_skills(text)
    return jsonify({"skills": skills})

@app.route("/chatbot", methods=["POST"])
def chatbot():
    msg = request.json.get("message","").lower()
    if any(w in msg for w in ["interview","schedule","when"]):
        reply = "Your interviews are listed in 'My Applications'. Check the status column for scheduled rounds."
    elif any(w in msg for w in ["eligible","qualify"]):
        reply = "Eligibility is checked automatically when you apply. The AI match score shows how well you fit each role."
    elif any(w in msg for w in ["score","match","ai"]):
        reply = "Your AI match score is based on CGPA, skills, degree, and year of passing vs job requirements."
    elif any(w in msg for w in ["job","drive","opening"]):
        reply = "Browse all active drives in the 'Explore Drives' section. Filter by role, location, or salary."
    elif any(w in msg for w in ["skill","resume","extract"]):
        reply = "Use the AI Skill Extractor — paste your resume text and AI will auto-detect your skills!"
    elif any(w in msg for w in ["status","applied"]):
        reply = "Track applications in 'My Applications'. Flow: Applied → Eligible → Test → Interview → Selected."
    elif any(w in msg for w in ["hello","hi","hey"]):
        reply = f"Hi {session.get('name','there')}! 👋 I'm SmartHire AI. Ask me about jobs, eligibility, or your applications."
    else:
        reply = "I can help with: job eligibility, application status, AI match scores, interview prep, and skill tips!"
    return jsonify({"reply": reply})

# ── Upload: profile photo ──
@app.route("/student/upload/photo", methods=["POST"])
def upload_photo():
    if session.get("role") != "student": return redirect(url_for("login"))
    f = request.files.get("photo")
    if not f or f.filename == "": return redirect(url_for("student_dash") + "#profile")
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_PHOTO: return redirect(url_for("student_dash") + "#profile")
    filename = f"photo_{session['uid']}.{ext}"
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    db = get_db()
    db.execute("UPDATE students SET photo=? WHERE id=?", (filename, session["uid"]))
    db.commit(); db.close()
    return redirect(url_for("student_dash") + "?section=profile")

# ── Upload: resume ──
@app.route("/student/upload/resume", methods=["POST"])
def upload_resume():
    if session.get("role") != "student": return redirect(url_for("login"))
    f = request.files.get("resume")
    if not f or f.filename == "": return redirect(url_for("student_dash") + "?section=profile")
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_RESUME: return redirect(url_for("student_dash") + "?section=profile")
    orig_name = secure_filename(f.filename)
    filename  = f"resume_{session['uid']}_{orig_name}"
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    from datetime import datetime
    uploaded_on = datetime.now().strftime("%d %b %Y")
    db = get_db()
    db.execute("UPDATE students SET resume=?, resume_uploaded_on=? WHERE id=?",
               (filename, uploaded_on, session["uid"]))
    db.commit(); db.close()
    return redirect(url_for("student_dash") + "?section=profile")

# ── Download resume ──
@app.route("/student/resume/download")
def download_resume():
    if session.get("role") != "student": return redirect(url_for("login"))
    db = get_db()
    row = db.execute("SELECT resume FROM students WHERE id=?", (session["uid"],)).fetchone()
    db.close()
    if not row or not row["resume"]: return "No resume uploaded", 404
    return send_from_directory(UPLOAD_FOLDER, row["resume"], as_attachment=True)

if __name__ == "__main__":
    init_db()
    migrate_db()
    print("\n✅  SmartHire AI — Campus Hiring Management System")
    print("   Open: http://127.0.0.1:5001\n")
    app.run(debug=True, port=5001)
