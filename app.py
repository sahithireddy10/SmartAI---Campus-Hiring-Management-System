from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
import os, requests as http_req
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import DuplicateKeyError
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "smarthire_ai_secret_2024")

# ── API Keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY       = os.environ.get("GEMINI_API_KEY", "")
ELEVENLABS_API_KEY   = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID  = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
SARVAM_API_KEY       = os.environ.get("SARVAM_API_KEY", "")
GITHUB_CLIENT_ID     = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
SUPER_ADMIN_EMAIL    = os.environ.get("SUPER_ADMIN_EMAIL", "superadmin@smarthire.ai")
SUPER_ADMIN_PWD      = os.environ.get("SUPER_ADMIN_PWD", "super@123")

# ─── MongoDB ──────────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
_client   = MongoClient(MONGO_URI)
mdb       = _client["smarthire"]

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_PHOTO  = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_RESUME = {"pdf", "doc", "docx"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────
def oid(val):
    if isinstance(val, ObjectId): return val
    try:    return ObjectId(str(val))
    except: return None

def fix(doc):
    if doc is None: return None
    d = dict(doc)
    d["id"] = str(d.pop("_id", ""))
    return d

def fix_all(docs):
    return [fix(d) for d in docs]

def college_id():
    """Return current session's college_id (str)."""
    return session.get("college_id", "")

def scoped(extra=None):
    """Base filter scoped to current college."""
    f = {"college_id": college_id()}
    if extra: f.update(extra)
    return f

# ─── Gemini helper ────────────────────────────────────────────────────────────
def gemini(prompt: str, timeout: int = 60) -> str:
    """Call Gemini 2.5 Flash with thinking disabled for speed."""
    resp = http_req.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}}
        },
        timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

# ─── Indexes (run once on startup) ────────────────────────────────────────────
def ensure_indexes():
    mdb.colleges.create_index("email", unique=True)
    mdb.colleges.create_index("code",  unique=True)
    mdb.students.create_index([("email",1),("college_id",1)], unique=True)
    mdb.companies.create_index([("email",1),("college_id",1)], unique=True)
    mdb.applications.create_index(
        [("student_id", ASCENDING), ("drive_id", ASCENDING)], unique=True
    )
    mdb.drives.create_index([("company_id", ASCENDING), ("status", ASCENDING)])
    mdb.drives.create_index("college_id")
    mdb.applications.create_index("drive_id")
    mdb.applications.create_index("student_id")
    mdb.students.create_index("college_id")
    mdb.companies.create_index("college_id")

with app.app_context():
    ensure_indexes()

# ─── AI helpers ───────────────────────────────────────────────────────────────
def ai_match_score(student, drive):
    score = 0
    cgpa     = student.get("cgpa", 0) or 0
    req_cgpa = drive.get("req_cgpa", 0) or 0
    if cgpa >= req_cgpa:
        score += 30
    elif cgpa >= req_cgpa - 0.5:
        score += 15
    req = [s.strip().lower() for s in (drive.get("req_skills") or "").split(",") if s.strip()]
    stu = [s.strip().lower() for s in (student.get("skills") or "").split(",") if s.strip()]
    if req:
        matched = sum(1 for r in req if any(r in s or s in r for s in stu))
        score += int((matched / len(req)) * 40)
    else:
        score += 30
    if not drive.get("req_degree") or student.get("degree") == drive.get("req_degree"):
        score += 20
    else:
        score += 5
    if not drive.get("req_year") or (student.get("year") or 0) >= (drive.get("req_year") or 0):
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
    if rtype == "HR":       return bank["HR"]
    if rtype == "Aptitude": return bank["Aptitude"]
    r = role.lower()
    if any(k in r for k in ["ml","ai","data","machine"]): return bank["Technical"]["ml"]
    if any(k in r for k in ["web","front","back","full"]): return bank["Technical"]["web"]
    return bank["Technical"]["default"]

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    cid = college_id()
    if cid:
        stats = {
            "students":  mdb.students.count_documents({"college_id": cid}),
            "companies": mdb.companies.count_documents({"college_id": cid}),
            "drives":    mdb.drives.count_documents({"college_id": cid, "status": "active"}),
            "placed":    len(mdb.applications.distinct("student_id",
                             {"status": "selected",
                              "drive_id": {"$in": [str(d["_id"]) for d in mdb.drives.find({"college_id": cid}, {"_id":1})]}})),
        }
    else:
        stats = {
            "students":  mdb.students.count_documents({}),
            "companies": mdb.companies.count_documents({}),
            "drives":    mdb.drives.count_documents({"status": "active"}),
            "placed":    len(mdb.applications.distinct("student_id", {"status": "selected"})),
        }
    return render_template("index.html", stats=stats)

# ── College self-registration ─────────────────────────────────────────────────
@app.route("/college/register", methods=["GET","POST"])
def college_register_page():
    if request.method == "POST":
        f = request.form
        if f.get("pwd") != f.get("pwd2"):
            return render_template("college_register.html", error="Passwords do not match.")
        try:
            mdb.colleges.insert_one({
                "name":       f["name"].strip(),
                "code":       f["code"].strip().upper(),
                "email":      f["email"].strip().lower(),
                "pwd":        f["pwd"],
                "phone":      f.get("phone","").strip(),
                "location":   f.get("location","").strip(),
                "university": f.get("university","").strip(),
                "active":     True,
                "created":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            return render_template("college_register.html", success=True)
        except DuplicateKeyError:
            return render_template("college_register.html", error="Email or code already registered.")
    return render_template("college_register.html")

# ── Super Admin routes ────────────────────────────────────────────────────────
@app.route("/superadmin/login", methods=["GET","POST"])
def superadmin_login():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        pwd   = request.form.get("pwd","").strip()
        if email == SUPER_ADMIN_EMAIL and pwd == SUPER_ADMIN_PWD:
            session.update({"role":"superadmin","name":"Super Admin","email":email})
            return redirect(url_for("superadmin_dash"))
        return render_template("login.html", error="Invalid super admin credentials.", superadmin=True)
    return render_template("login.html", superadmin=True)

@app.route("/superadmin/logout")
def superadmin_logout():
    session.clear()
    return redirect(url_for("superadmin_login"))

@app.route("/superadmin")
def superadmin_dash():
    if session.get("role") != "superadmin":
        return redirect(url_for("superadmin_login"))
    colleges_raw = list(mdb.colleges.find().sort("created", DESCENDING))
    colleges = fix_all(colleges_raw)

    # Per-college stats
    c_stats = {}
    for c in colleges:
        cid = c["id"]
        drive_ids = [str(d["_id"]) for d in mdb.drives.find({"college_id": cid}, {"_id":1})]
        c_stats[cid] = {
            "students": mdb.students.count_documents({"college_id": cid}),
            "drives":   len(drive_ids),
            "placed":   len(mdb.applications.distinct("student_id",
                            {"status":"selected","drive_id":{"$in": drive_ids}})) if drive_ids else 0,
        }

    total_students = sum(v["students"] for v in c_stats.values())
    total_placed   = sum(v["placed"]   for v in c_stats.values())
    stats = {"colleges": len(colleges), "students": total_students, "placed": total_placed}

    add_error   = request.args.get("add_error","")
    add_success = request.args.get("add_success","")
    return render_template("superadmin.html", colleges=colleges, c_stats=c_stats,
                           stats=stats, add_error=add_error, add_success=add_success)

@app.route("/superadmin/college/add", methods=["POST"])
def superadmin_add_college():
    if session.get("role") != "superadmin":
        return redirect(url_for("superadmin_login"))
    f = request.form
    try:
        mdb.colleges.insert_one({
            "name":       f["name"].strip(),
            "code":       f["code"].strip().upper(),
            "email":      f["email"].strip().lower(),
            "pwd":        f["pwd"],
            "phone":      f.get("phone","").strip(),
            "location":   f.get("location","").strip(),
            "university": f.get("university","").strip(),
            "active":     True,
            "created":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return redirect(url_for("superadmin_dash") + "?add_success=College+created+successfully")
    except DuplicateKeyError:
        return redirect(url_for("superadmin_dash") + "?add_error=Email+or+code+already+exists")

@app.route("/superadmin/college/<cid>/toggle", methods=["POST"])
def superadmin_toggle_college(cid):
    if session.get("role") != "superadmin":
        return redirect(url_for("superadmin_login"))
    col = mdb.colleges.find_one({"_id": oid(cid)})
    if col:
        mdb.colleges.update_one({"_id": oid(cid)}, {"$set": {"active": not col.get("active", True)}})
    return redirect(url_for("superadmin_dash"))

@app.route("/superadmin/college/<cid>/delete", methods=["POST"])
def superadmin_delete_college(cid):
    if session.get("role") != "superadmin":
        return redirect(url_for("superadmin_login"))
    # Remove all college data
    mdb.colleges.delete_one({"_id": oid(cid)})
    mdb.students.delete_many({"college_id": cid})
    mdb.companies.delete_many({"college_id": cid})
    drive_ids = [str(d["_id"]) for d in mdb.drives.find({"college_id": cid}, {"_id":1})]
    mdb.drives.delete_many({"college_id": cid})
    if drive_ids:
        mdb.applications.delete_many({"drive_id": {"$in": drive_ids}})
    return redirect(url_for("superadmin_dash"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        pwd   = request.form.get("pwd","").strip()
        role  = request.form.get("role","")

        # ── College admin login ───────────────────────────────────────────────
        if role == "admin":
            col = mdb.colleges.find_one({"email": email})
            if not col:
                return render_template("login.html", error="College not found.")
            if not col.get("active", True):
                return render_template("login.html", error="This college portal has been deactivated.")
            if col["pwd"] != pwd:
                return render_template("login.html", error="Wrong password.")
            session.update({
                "uid": str(col["_id"]), "role": "admin",
                "name": col["name"], "email": email,
                "college_id": str(col["_id"]), "college_name": col["name"]
            })
            return redirect(url_for("admin_dash"))

        # ── Student / Company login (scoped to college) ───────────────────────
        # Find the college first from the email domain or let user pick
        col_id = request.form.get("college_id","").strip()
        query  = {"email": email}
        if col_id:
            query["college_id"] = col_id

        db_col = mdb.students if role == "student" else mdb.companies
        row    = db_col.find_one(query)
        if not row:
            return render_template("login.html", error="Account not found.")
        if row["pwd"] != pwd:
            return render_template("login.html", error="Wrong password.")
        cid  = row.get("college_id","")
        col  = mdb.colleges.find_one({"_id": oid(cid)}) if cid else None
        if col and not col.get("active", True):
            return render_template("login.html", error="Your college portal has been deactivated.")
        session.update({
            "uid": str(row["_id"]), "role": role,
            "name": row["name"], "email": email,
            "college_id": cid,
            "college_name": col["name"] if col else ""
        })
        return redirect(url_for("student_dash" if role == "student" else "company_dash"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/register/student", methods=["GET","POST"])
def student_register():
    if request.method == "POST":
        f   = request.form
        cid = f.get("college_id","").strip()
        if not cid:
            return render_template("student_register.html", error="College not specified.")
        col = mdb.colleges.find_one({"_id": oid(cid)})
        if not col or not col.get("active", True):
            return render_template("student_register.html", error="Invalid or inactive college.")
        try:
            mdb.students.insert_one({
                "college_id": cid,
                "name": f["name"], "email": f["email"], "pwd": f["pwd"],
                "phone": f["phone"], "dob": f["dob"],
                "branch": f["branch"], "degree": f["degree"],
                "year": int(f["year"]), "cgpa": float(f["cgpa"]),
                "p12": float(f["p12"]), "p10": float(f["p10"]),
                "skills": f.get("skills",""), "bio": f.get("bio",""),
                "gender": "", "location": "", "photo": "", "resume": "",
                "resume_uploaded_on": "",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return render_template("student_register.html", success=True, college=fix(col))
        except DuplicateKeyError:
            return render_template("student_register.html", error="Email already registered in this college.", college=fix(col))
    # Pass college list for the dropdown
    cid = request.args.get("college_id","")
    col = fix(mdb.colleges.find_one({"_id": oid(cid)})) if cid else None
    colleges = fix_all(mdb.colleges.find({"active": True}).sort("name", ASCENDING))
    return render_template("student_register.html", colleges=colleges, college=col)

@app.route("/register/company", methods=["GET","POST"])
def company_register():
    if request.method == "POST":
        f   = request.form
        cid = f.get("college_id","").strip()
        if not cid:
            return render_template("company_register.html", error="College not specified.")
        col = mdb.colleges.find_one({"_id": oid(cid)})
        if not col or not col.get("active", True):
            return render_template("company_register.html", error="Invalid or inactive college.")
        try:
            mdb.companies.insert_one({
                "college_id": cid,
                "name": f["name"], "email": f["email"], "pwd": f["pwd"],
                "phone": f["phone"], "location": f["location"],
                "industry": f["industry"], "website": f.get("website",""),
                "about": f.get("about",""),
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return render_template("company_register.html", success=True, college=fix(col))
        except DuplicateKeyError:
            return render_template("company_register.html", error="Email already registered in this college.", college=fix(col))
    cid = request.args.get("college_id","")
    col = fix(mdb.colleges.find_one({"_id": oid(cid)})) if cid else None
    colleges = fix_all(mdb.colleges.find({"active": True}).sort("name", ASCENDING))
    return render_template("company_register.html", colleges=colleges, college=col)

@app.route("/student")
def student_dash():
    if session.get("role") != "student": return redirect(url_for("login"))
    uid = oid(session["uid"])
    cid = college_id()
    student = fix(mdb.students.find_one({"_id": uid}))
    if not student: return redirect(url_for("logout"))

    active_drives_raw = list(mdb.drives.find({"college_id": cid, "status": "active"}).sort("created", DESCENDING))
    my_apps_raw   = list(mdb.applications.find({"student_id": str(uid)}))
    apps_by_drive = {a["drive_id"]: a for a in my_apps_raw}

    drives = []
    for d in active_drives_raw:
        did_str = str(d["_id"])
        company = mdb.companies.find_one({"_id": oid(d["company_id"])}, {"name":1,"industry":1})
        row = fix(d)
        row["company_name"] = company["name"] if company else ""
        row["industry"]     = company.get("industry","") if company else ""
        app = apps_by_drive.get(did_str)
        if app:
            row["app_id"]     = str(app["_id"])
            row["app_status"] = app.get("status","")
            row["ai_score"]   = app.get("ai_score", 0)
        else:
            row["app_id"] = row["app_status"] = None
            row["ai_score"] = 0
        row["computed_score"] = row["ai_score"] if row["app_id"] and row["ai_score"] else ai_match_score(student, row)
        drives.append(row)

    my_apps = []
    for a in sorted(my_apps_raw, key=lambda x: x.get("applied_on",""), reverse=True):
        drive   = mdb.drives.find_one({"_id": oid(a["drive_id"])})
        if not drive: continue
        company = mdb.companies.find_one({"_id": oid(drive.get("company_id"))}, {"name":1})
        row = fix(a)
        row["title"]        = drive.get("title","")
        row["role"]         = drive.get("role","")
        row["salary"]       = drive.get("salary", 0)
        row["job_loc"]      = drive.get("location","")
        row["company_name"] = company["name"] if company else ""
        my_apps.append(row)

    unapplied = [d for d in drives if not d["app_id"]]
    recommendations = sorted(
        [{"drive": d, "score": d["computed_score"]} for d in unapplied],
        key=lambda x: x["score"], reverse=True
    )[:3]

    status_counts = {"applied":0,"eligible":0,"test":0,"interview":0,"selected":0,"rejected":0}
    for a in my_apps:
        s = a.get("status","")
        if s in status_counts: status_counts[s] += 1

    skills_list = [s.strip() for s in (student.get("skills") or "").split(",") if s.strip()]
    return render_template("student_dash.html", student=student,
                           drives=drives, my_apps=my_apps, skills_list=skills_list,
                           recommendations=recommendations, status_counts=status_counts)

@app.route("/apply/<drive_id>", methods=["POST"])
def apply(drive_id):
    if session.get("role") != "student": return redirect(url_for("login"))
    uid = oid(session["uid"])
    student = fix(mdb.students.find_one({"_id": uid}))
    drive   = fix(mdb.drives.find_one({"_id": oid(drive_id)}))
    if not drive: return redirect(url_for("student_dash"))
    score = ai_match_score(student, drive)
    try:
        mdb.applications.insert_one({
            "student_id": str(uid),
            "drive_id":   drive_id,
            "status":     "applied",
            "ai_score":   score,
            "applied_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except DuplicateKeyError:
        pass
    return redirect(url_for("student_dash"))

@app.route("/company")
def company_dash():
    if session.get("role") != "company": return redirect(url_for("login"))
    uid     = oid(session["uid"])
    company = fix(mdb.companies.find_one({"_id": uid}))
    if not company: return redirect(url_for("logout"))
    cid_str = str(uid)

    # Drives for this company with aggregated application counts
    drives_raw = list(mdb.drives.find({"company_id": cid_str}).sort("created", DESCENDING))
    drives = []
    for d in drives_raw:
        did_str = str(d["_id"])
        apps = list(mdb.applications.find({"drive_id": did_str}))
        row = fix(d)
        row["app_count"]       = len(apps)
        row["selected_count"]  = len(set(a["student_id"] for a in apps if a.get("status") == "selected"))
        row["interview_count"] = len(set(a["student_id"] for a in apps if a.get("status") == "interview"))
        row["eligible_count"]  = sum(1 for a in apps if a.get("status") == "eligible")
        row["test_count"]      = sum(1 for a in apps if a.get("status") == "test")
        row["rejected_count"]  = sum(1 for a in apps if a.get("status") == "rejected")
        drives.append(row)

    total_apps       = sum(d["app_count"]       for d in drives)
    total_selected   = sum(d["selected_count"]  for d in drives)
    total_interviews = sum(d["interview_count"] for d in drives)
    stats = {
        "drives":     len(drives),
        "apps":       total_apps,
        "selected":   total_selected,
        "interviews": total_interviews,
        "offers":     total_selected,
    }

    # Status breakdown for donut chart
    drive_ids = [str(d["_id"]) for d in drives_raw]
    status_counts = {"applied":0,"eligible":0,"test":0,"interview":0,"selected":0,"rejected":0}
    for a in mdb.applications.find({"drive_id": {"$in": drive_ids}}):
        s = a.get("status","")
        if s in status_counts: status_counts[s] += 1

    # Timeline — applications per day grouped (last 30 unique days)
    from collections import defaultdict
    timeline_data = defaultdict(lambda: {"cnt": 0, "shortlisted": 0})
    shortlist_statuses = {"eligible","test","interview","selected"}
    for a in mdb.applications.find({"drive_id": {"$in": drive_ids}}):
        day = (a.get("applied_on") or "")[:10]
        if day:
            timeline_data[day]["cnt"] += 1
            if a.get("status") in shortlist_statuses:
                timeline_data[day]["shortlisted"] += 1
    sorted_days = sorted(timeline_data.keys())[-30:]
    timeline_labels    = sorted_days
    timeline_apps      = [timeline_data[d]["cnt"] for d in sorted_days]
    timeline_shortlist = [timeline_data[d]["shortlisted"] for d in sorted_days]

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
        mdb.drives.insert_one({
            "college_id":  college_id(),
            "company_id":  str(oid(session["uid"])),
            "title":       f["title"], "role": f["role"],
            "location":    f["location"], "salary": float(f["salary"]),
            "deadline":    f["deadline"], "description": f.get("description",""),
            "req_cgpa":    float(f.get("req_cgpa",0)), "req_degree": f.get("req_degree",""),
            "req_skills":  f.get("req_skills",""), "req_year": int(f.get("req_year",0)),
            "status":      "active",
            "created":     datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return redirect(url_for("company_dash") + "?section=drives")
    return render_template("create_drive.html")

@app.route("/drive/<drive_id>/toggle", methods=["POST"])
def toggle_drive(drive_id):
    if session.get("role") != "company": return redirect(url_for("login"))
    d = mdb.drives.find_one({"_id": oid(drive_id), "company_id": str(oid(session["uid"]))})
    if d:
        new_status = "closed" if d["status"] == "active" else "active"
        mdb.drives.update_one({"_id": oid(drive_id)}, {"$set": {"status": new_status}})
    return redirect(url_for("company_dash") + "?section=drives")

@app.route("/drive/<drive_id>/applicants")
def drive_applicants(drive_id):
    if session.get("role") != "company": return redirect(url_for("login"))
    drive = fix(mdb.drives.find_one({"_id": oid(drive_id), "company_id": str(oid(session["uid"]))}))
    if not drive: return redirect(url_for("company_dash"))
    apps_raw = list(mdb.applications.find({"drive_id": drive_id}).sort("ai_score", DESCENDING))
    apps = []
    for a in apps_raw:
        student = mdb.students.find_one({"_id": oid(a["student_id"])},
                                        {"name":1,"email":1,"cgpa":1,"branch":1,"degree":1,"skills":1,"phone":1})
        row = fix(a)
        row["sname"]  = student["name"]   if student else ""
        row["semail"] = student["email"]  if student else ""
        row["cgpa"]   = student["cgpa"]   if student else 0
        row["branch"] = student["branch"] if student else ""
        row["degree"] = student["degree"] if student else ""
        row["skills"] = student["skills"] if student else ""
        row["phone"]  = student["phone"]  if student else ""
        apps.append(row)
    return render_template("drive_applicants.html", drive=drive, apps=apps)

@app.route("/app/<app_id>/status", methods=["POST"])
def update_status(app_id):
    if session.get("role") != "company": return redirect(url_for("login"))
    status = request.form.get("status")
    mdb.applications.update_one({"_id": oid(app_id)}, {"$set": {"status": status}})
    row = mdb.applications.find_one({"_id": oid(app_id)}, {"drive_id": 1})
    return redirect(url_for("drive_applicants", drive_id=row["drive_id"]))

@app.route("/admin")
def admin_dash():
    if session.get("role") != "admin": return redirect(url_for("login"))
    cid = college_id()

    from collections import Counter, defaultdict

    # ── Core stats (scoped to this college)
    college_drive_ids = [str(d["_id"]) for d in mdb.drives.find({"college_id": cid}, {"_id":1})]

    n_students  = mdb.students.count_documents({"college_id": cid})
    n_companies = mdb.companies.count_documents({"college_id": cid})
    n_drives    = len(college_drive_ids)
    n_apps      = mdb.applications.count_documents({"drive_id": {"$in": college_drive_ids}}) if college_drive_ids else 0
    n_selected  = len(mdb.applications.distinct("student_id",
                      {"status":"selected","drive_id":{"$in": college_drive_ids}})) if college_drive_ids else 0
    stats = {
        "students":  n_students, "companies": n_companies,
        "drives":    n_drives,   "apps":      n_apps,   "selected": n_selected,
    }
    placement_rate = min(round((n_selected / n_students * 100), 1), 100.0) if n_students else 0

    # ── Recent drives
    drives_raw = list(mdb.drives.find({"college_id": cid}).sort("created", DESCENDING).limit(10))
    drives = []
    for d in drives_raw:
        company = mdb.companies.find_one({"_id": oid(d.get("company_id"))}, {"name":1})
        row = fix(d)
        row["company_name"] = company["name"] if company else ""
        row["app_count"]    = mdb.applications.count_documents({"drive_id": row["id"]})
        drives.append(row)

    # ── All students
    students_raw = list(mdb.students.find({"college_id": cid}).sort("created", DESCENDING))
    students = []
    for s in students_raw:
        sid_str = str(s["_id"])
        apps_agg = list(mdb.applications.find({"student_id": sid_str}, {"ai_score":1}))
        row = fix(s)
        row["app_count"]  = len(apps_agg)
        row["best_score"] = max((a.get("ai_score",0) for a in apps_agg), default=0)
        students.append(row)

    student_apps = {}
    for s in students:
        apps = []
        for a in mdb.applications.find({"student_id": s["id"]}).sort("applied_on", DESCENDING):
            drive   = mdb.drives.find_one({"_id": oid(a["drive_id"])}, {"title":1,"role":1,"company_id":1})
            company = mdb.companies.find_one({"_id": oid(drive.get("company_id") if drive else None)}, {"name":1}) if drive else None
            apps.append({
                "status": a.get("status",""), "ai_score": a.get("ai_score",0),
                "applied_on": a.get("applied_on",""),
                "title": drive["title"] if drive else "",
                "role":  drive["role"]  if drive else "",
                "company_name": company["name"] if company else "",
            })
        student_apps[s["id"]] = apps

    # ── Companies
    companies_raw = list(mdb.companies.find({"college_id": cid}).sort("created", DESCENDING))
    companies = []
    for co in companies_raw:
        cid_str = str(co["_id"])
        co_drive_ids = [str(d["_id"]) for d in mdb.drives.find({"company_id": cid_str}, {"_id":1})]
        co_apps      = list(mdb.applications.find({"drive_id": {"$in": co_drive_ids}})) if co_drive_ids else []
        row = fix(co)
        row["drive_count"]    = len(co_drive_ids)
        row["app_count"]      = len(co_apps)
        row["selected_count"] = len(set(a["student_id"] for a in co_apps if a.get("status")=="selected"))
        companies.append(row)

    company_drives = {}; company_applicants = {}; company_selected = {}
    for co in companies:
        co_id         = co["id"]
        co_drives_raw = list(mdb.drives.find({"company_id": co_id}).sort("created", DESCENDING))
        c_drives = []
        for d in co_drives_raw:
            row = fix(d)
            row["app_count"] = mdb.applications.count_documents({"drive_id": row["id"]})
            c_drives.append(row)
        company_drives[co_id] = c_drives
        co_drive_ids = [d["id"] for d in c_drives]
        applicants = []
        for a in mdb.applications.find({"drive_id": {"$in": co_drive_ids}}).sort("applied_on", DESCENDING) if co_drive_ids else []:
            stu   = mdb.students.find_one({"_id": oid(a["student_id"])}, {"name":1,"email":1,"branch":1,"cgpa":1})
            drv   = mdb.drives.find_one({"_id": oid(a["drive_id"])}, {"title":1})
            applicants.append({
                "name": stu["name"] if stu else "", "email": stu["email"] if stu else "",
                "branch": stu.get("branch","") if stu else "", "cgpa": stu.get("cgpa",0) if stu else 0,
                "status": a.get("status",""), "ai_score": a.get("ai_score",0),
                "applied_on": a.get("applied_on",""), "drive_title": drv["title"] if drv else "",
            })
        company_applicants[co_id] = applicants
        company_selected[co_id]   = [r for r in applicants if r["status"]=="selected"]

    # ── Analytics
    sel_apps = list(mdb.applications.find({"status":"selected","drive_id":{"$in": college_drive_ids}})) if college_drive_ids else []
    branch_counter = Counter()
    for a in sel_apps:
        s = mdb.students.find_one({"_id": oid(a["student_id"])}, {"branch":1})
        if s: branch_counter[s.get("branch","")] += 1
    branch_stats = [{"branch": b, "placed": c} for b, c in branch_counter.most_common()]

    monthly_data = defaultdict(lambda: {"apps":0,"placed":0})
    all_apps_q   = mdb.applications.find({"drive_id":{"$in": college_drive_ids}}) if college_drive_ids else []
    for a in all_apps_q:
        month = (a.get("applied_on") or "")[:7]
        if month:
            monthly_data[month]["apps"] += 1
            if a.get("status") == "selected": monthly_data[month]["placed"] += 1
    sorted_months  = sorted(monthly_data.keys())[-12:]
    monthly_labels = sorted_months
    monthly_apps   = [monthly_data[m]["apps"]   for m in sorted_months]
    monthly_placed = [monthly_data[m]["placed"] for m in sorted_months]

    company_hire_count = Counter()
    for a in sel_apps:
        drive = mdb.drives.find_one({"_id": oid(a["drive_id"])}, {"company_id":1})
        if drive:
            co = mdb.companies.find_one({"_id": oid(drive["company_id"])}, {"name":1})
            if co: company_hire_count[co["name"]] += 1
    top_companies = [{"name": n, "hired": c} for n, c in company_hire_count.most_common(5)]

    status_counts = {"applied":0,"eligible":0,"test":0,"interview":0,"selected":0,"rejected":0}
    all_apps_status = mdb.applications.find({"drive_id":{"$in": college_drive_ids}}, {"status":1}) if college_drive_ids else []
    for a in all_apps_status:
        s = a.get("status","")
        if s in status_counts: status_counts[s] += 1

    recent_students  = [dict(fix(s), type="student")  for s in mdb.students.find({"college_id":cid}).sort("created", DESCENDING).limit(5)]
    recent_companies = [dict(fix(c), type="company") for c in mdb.companies.find({"college_id":cid}).sort("created", DESCENDING).limit(5)]
    recent_regs = sorted(recent_students + recent_companies, key=lambda x: x.get("created",""), reverse=True)[:10]

    return render_template("admin_dash.html",
        stats=stats, placement_rate=placement_rate,
        drives=drives, students=students, companies=companies,
        student_apps=student_apps,
        company_drives=company_drives, company_applicants=company_applicants, company_selected=company_selected,
        branch_stats=branch_stats,
        monthly_labels=monthly_labels, monthly_apps=monthly_apps, monthly_placed=monthly_placed,
        top_companies=top_companies, status_counts=status_counts, recent_regs=recent_regs,
        college_name=session.get("college_name","")
    )

@app.route("/admin/register/student", methods=["GET","POST"])
def admin_register_student():
    if session.get("role") != "admin": return redirect(url_for("login"))
    if request.method == "POST":
        f   = request.form
        cid = college_id()
        try:
            mdb.students.insert_one({
                "college_id": cid,
                "name": f["name"], "email": f["email"], "pwd": f["pwd"],
                "phone": f["phone"], "dob": f["dob"],
                "branch": f["branch"], "degree": f["degree"],
                "year": int(f["year"]), "cgpa": float(f["cgpa"]),
                "p12": float(f["p12"]), "p10": float(f["p10"]),
                "skills": f.get("skills",""), "bio": f.get("bio",""),
                "gender": "", "location": "", "photo": "", "resume": "",
                "resume_uploaded_on": "",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return redirect(url_for("admin_dash") + "?section=registrations&msg=student_added")
        except Exception as e:
            return render_template("admin_dash.html", reg_error=str(e))
    return redirect(url_for("admin_dash") + "?section=registrations")

@app.route("/admin/register/company", methods=["GET","POST"])
def admin_register_company():
    if session.get("role") != "admin": return redirect(url_for("login"))
    if request.method == "POST":
        f   = request.form
        cid = college_id()
        try:
            mdb.companies.insert_one({
                "college_id": cid,
                "name": f["name"], "email": f["email"], "pwd": f["pwd"],
                "phone": f["phone"], "location": f["location"],
                "industry": f["industry"], "website": f.get("website",""),
                "about": f.get("about",""),
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return redirect(url_for("admin_dash") + "?section=registrations&msg=company_added")
        except Exception as e:
            return redirect(url_for("admin_dash") + "?section=registrations&err=" + str(e))
    return redirect(url_for("admin_dash") + "?section=registrations")

# ── AI API endpoints ──────────────────────────────────────────────────────────
@app.route("/ai/match/<drive_id>")
def ai_match(drive_id):
    if session.get("role") != "student": return jsonify({"error": "unauthorized"})
    student = fix(mdb.students.find_one({"_id": oid(session["uid"])}))
    drive   = fix(mdb.drives.find_one({"_id": oid(drive_id)}))
    if not drive: return jsonify({"error": "not found"})
    score = ai_match_score(student, drive)
    req = [s.strip() for s in (drive.get("req_skills") or "").split(",") if s.strip()]
    stu = [s.strip().lower() for s in (student.get("skills") or "").split(",") if s.strip()]
    matched = [r for r in req if any(r.lower() in s or s in r.lower() for s in stu)]
    missing = [r for r in req if r not in matched]
    return jsonify({
        "score": score, "matched": matched, "missing": missing,
        "cgpa_ok": (student.get("cgpa") or 0) >= (drive.get("req_cgpa") or 0)
    })

@app.route("/ai/questions")
def get_questions():
    role  = request.args.get("role", "Software Engineer")
    rtype = request.args.get("round", "Technical")
    return jsonify({"questions": ai_questions(role, rtype), "role": role, "round": rtype})

@app.route("/ai/extract", methods=["POST"])
def extract_skills():
    text   = request.json.get("text","")
    skills = ai_extract_skills(text)
    return jsonify({"skills": skills})

@app.route("/chatbot", methods=["POST"])
def chatbot():
    msg  = request.json.get("message", "")
    name = session.get("name", "there")
    role = session.get("role", "student")

    # ── Gemini AI chatbot ──────────────────────────────────────────────────────
    if GEMINI_API_KEY:
        system_prompt = (
            f"You are SmartHire AI, a friendly campus placement assistant. "
            f"The user '{name}' is a {role}. "
            "Answer questions about job drives, eligibility, application status, "
            "interview tips, skills, and placement process. "
            "Keep responses concise (2-3 sentences max). Be warm and encouraging."
        )
        try:
            reply = gemini(f"{system_prompt}\n\nUser: {msg}")
            return jsonify({"reply": reply})
        except Exception:
            pass  # fall through to keyword fallback

    # ── Keyword fallback ──────────────────────────────────────────────────────
    msg_lower = msg.lower()
    if any(w in msg_lower for w in ["interview","schedule","when"]):
        reply = "Your interviews are listed in 'My Applications'. Check the status column for scheduled rounds."
    elif any(w in msg_lower for w in ["eligible","qualify"]):
        reply = "Eligibility is checked automatically when you apply. The AI match score shows how well you fit each role."
    elif any(w in msg_lower for w in ["score","match","ai"]):
        reply = "Your AI match score is based on CGPA, skills, degree, and year of passing vs job requirements."
    elif any(w in msg_lower for w in ["job","drive","opening"]):
        reply = "Browse all active drives in the 'Explore Drives' section. Filter by role, location, or salary."
    elif any(w in msg_lower for w in ["skill","resume","extract"]):
        reply = "Use the AI Skill Extractor — paste your resume text and AI will auto-detect your skills!"
    elif any(w in msg_lower for w in ["status","applied"]):
        reply = "Track applications in 'My Applications'. Flow: Applied → Eligible → Test → Interview → Selected."
    elif any(w in msg_lower for w in ["hello","hi","hey"]):
        reply = f"Hi {name}! 👋 I'm SmartHire AI. Ask me about jobs, eligibility, or your applications."
    else:
        reply = "I can help with: job eligibility, application status, AI match scores, interview prep, and skill tips!"
    return jsonify({"reply": reply})


# ── Gemini: Career Advice ─────────────────────────────────────────────────────
@app.route("/ai/career-advice", methods=["POST"])
def career_advice():
    if session.get("role") != "student":
        return jsonify({"error": "unauthorized"})
    data    = request.json or {}
    topic   = data.get("topic", "career growth")
    student = fix(mdb.students.find_one({"_id": oid(session["uid"])}))
    if not GEMINI_API_KEY:
        return jsonify({"advice": "Gemini API key not configured."})
    prompt = (
        f"Student profile: branch={student.get('branch')}, degree={student.get('degree')}, "
        f"CGPA={student.get('cgpa')}, skills={student.get('skills')}.\n"
        f"Give practical, specific career advice about: {topic}.\n"
        f"Keep it to 3-4 bullet points, actionable and encouraging."
    )
    try:
        text = gemini(prompt)
        return jsonify({"advice": text})
    except Exception as e:
        return jsonify({"advice": f"Could not fetch advice: {str(e)}"})


# ── Gemini: Mock Interview Feedback ──────────────────────────────────────────
@app.route("/ai/mock-feedback", methods=["POST"])
def mock_feedback():
    if session.get("role") != "student":
        return jsonify({"error": "unauthorized"})
    data    = request.json or {}
    answers = data.get("answers", [])
    role    = data.get("role", "Software Engineer")
    if not GEMINI_API_KEY:
        return jsonify({"feedback": "Gemini API key not configured."})
    qa_text = "\n".join([f"Q{i+1}: {a}" for i, a in enumerate(answers) if a.strip()])
    prompt = (
        f"You are an expert campus recruiter evaluating a student applying for '{role}'.\n"
        f"Review these interview answers:\n{qa_text}\n\n"
        "Provide structured feedback:\n"
        "1. Strengths (2 points)\n"
        "2. Areas to Improve (2 points)\n"
        "3. Overall Score out of 10 with a one-line verdict.\n"
        "Be constructive, specific, and encouraging."
    )
    try:
        feedback = gemini(prompt)
        return jsonify({"feedback": feedback})
    except Exception as e:
        return jsonify({"feedback": f"Could not generate feedback: {str(e)}"})


# ── ElevenLabs: Text-to-Speech ────────────────────────────────────────────────
@app.route("/ai/speak", methods=["POST"])
def speak():
    if not session.get("role"):
        return jsonify({"error": "unauthorized"})
    text = (request.json or {}).get("text", "")[:500]
    if not text:
        return jsonify({"error": "no text"})
    if not ELEVENLABS_API_KEY:
        return jsonify({"error": "ElevenLabs not configured"})
    try:
        resp = http_req.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            },
            timeout=15
        )
        if resp.status_code == 200:
            from flask import Response
            return Response(resp.content, mimetype="audio/mpeg")
        return jsonify({"error": f"ElevenLabs error {resp.status_code}"})
    except Exception as e:
        return jsonify({"error": str(e)})


# ── Sarvam: Translate text to Hindi ──────────────────────────────────────────
@app.route("/ai/translate", methods=["POST"])
def translate():
    if not session.get("role"):
        return jsonify({"error": "unauthorized"})
    data   = request.json or {}
    text   = data.get("text", "")
    target = data.get("target_language", "hi-IN")
    if not SARVAM_API_KEY:
        return jsonify({"error": "Sarvam not configured"})
    try:
        resp = http_req.post(
            "https://api.sarvam.ai/translate",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "input": text,
                "source_language_code": "en-IN",
                "target_language_code": target,
                "speaker_gender": "Female",
                "mode": "formal",
                "model": "mayura:v1"
            },
            timeout=10
        )
        result = resp.json()
        translated = result.get("translated_text", text)
        return jsonify({"translated": translated})
    except Exception as e:
        return jsonify({"error": str(e)})


# ── GitHub OAuth ──────────────────────────────────────────────────────────────
@app.route("/auth/github")
def github_login():
    # If student is already logged in, this connects their GitHub
    state = session.get("uid", "login")
    return redirect(
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}&scope=user:email,public_repo&state={state}"
    )

@app.route("/auth/github/callback")
def github_callback():
    code  = request.args.get("code")
    state = request.args.get("state", "login")
    if not code:
        return redirect(url_for("login"))
    try:
        token_resp = http_req.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET, "code": code},
            timeout=10
        )
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return redirect(url_for("student_dash") + "?section=profile&github_error=1")

        # Fetch GitHub user + repos
        gh_headers = {"Authorization": f"Bearer {access_token}"}
        gh_user    = http_req.get("https://api.github.com/user", headers=gh_headers, timeout=10).json()
        repos_raw  = http_req.get(
            f"https://api.github.com/users/{gh_user['login']}/repos?sort=updated&per_page=6",
            headers=gh_headers, timeout=10
        ).json()
        repos = [
            {
                "name":        r.get("name",""),
                "description": r.get("description","") or "",
                "url":         r.get("html_url",""),
                "language":    r.get("language","") or "",
                "stars":       r.get("stargazers_count", 0),
                "forks":       r.get("forks_count", 0),
            }
            for r in (repos_raw if isinstance(repos_raw, list) else [])
        ]

        gh_data = {
            "github_login":    gh_user.get("login",""),
            "github_name":     gh_user.get("name","") or gh_user.get("login",""),
            "github_avatar":   gh_user.get("avatar_url",""),
            "github_bio":      gh_user.get("bio","") or "",
            "github_location": gh_user.get("location","") or "",
            "github_repos":    repos,
            "github_token":    access_token,
        }

        # If already logged in → connect to existing student
        if session.get("role") == "student":
            mdb.students.update_one({"_id": oid(session["uid"])}, {"$set": gh_data})
            return redirect(url_for("student_dash") + "?section=profile&github=1")

        # Otherwise → login/register flow
        emails_resp = http_req.get("https://api.github.com/user/emails", headers=gh_headers, timeout=10)
        emails  = emails_resp.json()
        primary = next((e["email"] for e in emails if e.get("primary")), gh_user.get("email"))
        name    = gh_user.get("name") or gh_user.get("login", "GitHub User")
        if not primary:
            return redirect(url_for("login"))
        student = mdb.students.find_one({"email": primary})
        if not student:
            result = mdb.students.insert_one({
                "name": name, "email": primary, "pwd": "",
                "phone": "", "dob": "", "branch": "CSE", "degree": "B.Tech",
                "year": 4, "cgpa": 0.0, "p12": 0.0, "p10": 0.0,
                "skills": "", "bio": gh_user.get("bio","") or "",
                "gender": "", "location": gh_user.get("location",""),
                "photo": "", "resume": "", "resume_uploaded_on": "",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                **gh_data
            })
            uid = str(result.inserted_id)
        else:
            mdb.students.update_one({"_id": student["_id"]}, {"$set": gh_data})
            uid = str(student["_id"])
        session.update({"uid": uid, "role": "student", "name": name, "email": primary})
        return redirect(url_for("student_dash") + "?section=profile&github=1")
    except Exception as e:
        return redirect(url_for("student_dash") + f"?section=profile&github_error=1"
                        if session.get("role") == "student" else url_for("login"))


# ── GitHub: student profile data (for company/admin views) ───────────────────
@app.route("/student/<student_id>/github")
def student_github(student_id):
    if not session.get("role") in ("company", "admin", "student"):
        return jsonify({"error": "unauthorized"})
    s = mdb.students.find_one({"_id": oid(student_id)}, {"github_login":1, "github_repos":1, "github_bio":1, "github_avatar":1})
    if not s or not s.get("github_login"):
        return jsonify({"github_login": None, "repos": []})
    return jsonify({
        "github_login": s.get("github_login",""),
        "github_bio":   s.get("github_bio",""),
        "github_avatar":s.get("github_avatar",""),
        "repos":        s.get("github_repos", [])
    })

# ── Upload: profile photo ─────────────────────────────────────────────────────
@app.route("/student/upload/photo", methods=["POST"])
def upload_photo():
    if session.get("role") != "student": return redirect(url_for("login"))
    f = request.files.get("photo")
    if not f or f.filename == "": return redirect(url_for("student_dash") + "#profile")
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_PHOTO: return redirect(url_for("student_dash") + "#profile")
    filename = f"photo_{session['uid']}.{ext}"
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    mdb.students.update_one({"_id": oid(session["uid"])}, {"$set": {"photo": filename}})
    return redirect(url_for("student_dash") + "?section=profile")

# ── Upload: resume ────────────────────────────────────────────────────────────
@app.route("/student/upload/resume", methods=["POST"])
def upload_resume():
    if session.get("role") != "student": return redirect(url_for("login"))
    f = request.files.get("resume")
    if not f or f.filename == "": return redirect(url_for("student_dash") + "?section=profile")
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_RESUME: return redirect(url_for("student_dash") + "?section=profile")
    orig_name   = secure_filename(f.filename)
    filename    = f"resume_{session['uid']}_{orig_name}"
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    uploaded_on = datetime.now().strftime("%d %b %Y")
    mdb.students.update_one(
        {"_id": oid(session["uid"])},
        {"$set": {"resume": filename, "resume_uploaded_on": uploaded_on}}
    )
    return redirect(url_for("student_dash") + "?section=profile")

# ── Download resume ───────────────────────────────────────────────────────────
@app.route("/student/resume/download")
def download_resume():
    if session.get("role") != "student": return redirect(url_for("login"))
    row = mdb.students.find_one({"_id": oid(session["uid"])}, {"resume": 1})
    if not row or not row.get("resume"): return "No resume uploaded", 404
    return send_from_directory(UPLOAD_FOLDER, row["resume"], as_attachment=True)

if __name__ == "__main__":
    ensure_indexes()
    print("\n✅  SmartHire AI — Campus Hiring Management System (MongoDB)")
    print("   Open: http://127.0.0.1:5001\n")
    app.run(debug=True, port=5001)
