"""
seed_data.py – Populate MongoDB with SmartHire AI demo data (2026 cohort).
Run once:  python seed_data.py
"""
import os
import random
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
client    = MongoClient(MONGO_URI)
mdb       = client["smarthire"]

# ── Ensure indexes ────────────────────────────────────────────────────────────
def ensure_indexes():
    mdb.students.create_index("email", unique=True)
    mdb.companies.create_index("email", unique=True)
    mdb.applications.create_index(
        [("student_id", ASCENDING), ("drive_id", ASCENDING)], unique=True
    )

# ── Check existing data ───────────────────────────────────────────────────────
def check_existing():
    print("=" * 55)
    print("EXISTING DATA")
    print(f"  Students    : {mdb.students.count_documents({})}")
    print(f"  Companies   : {mdb.companies.count_documents({})}")
    print(f"  Drives      : {mdb.drives.count_documents({})}")
    print(f"  Applications: {mdb.applications.count_documents({})}")
    print("=" * 55)

# ── Companies ─────────────────────────────────────────────────────────────────
COMPANIES = [
    ("TCS",       "hr@tcs.com",              "tcs@123",      "1800-209-3111",
     "Mumbai, Maharashtra",   "IT Services",  "https://www.tcs.com",
     "Tata Consultancy Services is a global IT services, consulting and business solutions organization.",
     "2025-10-15 09:00:00"),
    ("Infosys",   "careers@infosys.com",      "infosys@123",  "1800-425-4968",
     "Bengaluru, Karnataka",  "IT Services",  "https://www.infosys.com",
     "Infosys is a global leader in next-generation digital services and consulting.",
     "2025-10-28 10:30:00"),
    ("Wipro",     "talent@wipro.com",          "wipro@123",    "1800-102-5799",
     "Bengaluru, Karnataka",  "IT Services",  "https://www.wipro.com",
     "Wipro Limited is a leading global information technology, consulting and business process services company.",
     "2025-11-10 11:00:00"),
    ("Google",    "campus@google.com",         "google@123",   "+1-650-253-0000",
     "Hyderabad, Telangana",  "Technology",   "https://careers.google.com",
     "Google LLC is an American multinational technology company focusing on search engine, cloud computing, and AI.",
     "2025-11-20 14:00:00"),
    ("Microsoft", "mscampus@microsoft.com",    "msft@123",     "+1-425-882-8080",
     "Hyderabad, Telangana",  "Technology",   "https://careers.microsoft.com",
     "Microsoft Corporation is an American multinational technology corporation producing software, electronics, and cloud services.",
     "2025-12-05 09:30:00"),
]

# ── Students ──────────────────────────────────────────────────────────────────
STUDENTS = [
    ("Arjun Sharma",    "arjun.sharma@student.edu",   "pass@123", "9876543210", "2005-03-15",
     "CSE",  "B.Tech", 4, 8.7, 88.4, 91.2,
     "Python,Java,Machine Learning,SQL,Django,Git",
     "Passionate about AI and backend development.", "Male",   "Delhi",     "2026-02-10 09:15:00"),
    ("Priya Nair",      "priya.nair@student.edu",     "pass@123", "9876543211", "2005-07-22",
     "CSE",  "B.Tech", 4, 9.1, 92.0, 89.5,
     "Python,React,Node.js,MongoDB,REST API,Docker",
     "Full-stack developer with a love for clean UI.", "Female", "Kochi",    "2026-02-18 10:30:00"),
    ("Rahul Verma",     "rahul.verma@student.edu",    "pass@123", "9876543212", "2005-11-05",
     "IT",   "B.Tech", 4, 7.8, 80.0, 85.0,
     "Java,Spring Boot,MySQL,Git,Linux",
     "Backend enthusiast, loves building scalable systems.", "Male", "Pune",  "2026-01-22 08:45:00"),
    ("Sneha Reddy",     "sneha.reddy@student.edu",    "pass@123", "9876543213", "2006-01-30",
     "IT",   "B.Tech", 4, 8.3, 85.5, 87.0,
     "JavaScript,React,HTML,CSS,TypeScript,Figma",
     "UI/UX focused frontend developer.", "Female", "Hyderabad", "2026-03-05 11:00:00"),
    ("Karthik Menon",   "karthik.menon@student.edu",  "pass@123", "9876543214", "2005-09-18",
     "ECE",  "B.Tech", 4, 7.5, 78.0, 82.0,
     "C,C++,Embedded Systems,Python,MATLAB",
     "Interested in IoT and embedded systems.", "Male", "Chennai", "2026-02-01 14:20:00"),
    ("Divya Patel",     "divya.patel@student.edu",    "pass@123", "9876543215", "2006-05-12",
     "ECE",  "B.Tech", 4, 8.0, 83.0, 88.5,
     "Python,Data Science,NumPy,Pandas,Tableau",
     "Data enthusiast with strong analytical skills.", "Female", "Ahmedabad", "2026-01-15 09:00:00"),
    ("Amit Kumar",      "amit.kumar@student.edu",     "pass@123", "9876543216", "2005-12-25",
     "MECH", "B.Tech", 4, 7.2, 75.0, 79.0,
     "AutoCAD,SolidWorks,MATLAB,Python,Excel",
     "Mechanical engineer exploring data analytics.", "Male", "Jaipur", "2026-01-28 16:10:00"),
    ("Pooja Singh",     "pooja.singh@student.edu",    "pass@123", "9876543217", "2006-08-08",
     "MECH", "B.Tech", 4, 7.6, 79.5, 83.0,
     "Python,Excel,Power BI,SQL,AutoCAD",
     "Bridging mechanical engineering with data science.", "Female", "Lucknow", "2026-03-12 10:45:00"),
    ("Vikram Iyer",     "vikram.iyer@student.edu",    "pass@123", "9876543218", "2005-06-14",
     "EEE",  "B.Tech", 4, 8.5, 87.0, 90.0,
     "Python,MATLAB,C,Embedded Systems,AWS",
     "Electrical engineer with cloud computing interest.", "Male", "Bengaluru", "2026-04-03 08:30:00"),
    ("Ananya Bose",     "ananya.bose@student.edu",    "pass@123", "9876543219", "2006-04-03",
     "EEE",  "B.Tech", 4, 9.3, 94.0, 92.5,
     "Python,Machine Learning,TensorFlow,Deep Learning,NLP",
     "AI researcher passionate about neural networks.", "Female", "Kolkata", "2026-04-20 13:00:00"),
]

# ── Drives ────────────────────────────────────────────────────────────────────
# (title, role, location, salary, deadline, description, req_cgpa, req_degree,
#  req_skills, req_year, status, created)
DRIVES_TEMPLATE = {
    "TCS": [
        ("TCS NQT 2026 – Software Engineer", "Software Engineer",
         "Pan India", 350000, "2026-07-20",
         "TCS National Qualifier Test for fresh graduates. Roles in application development and maintenance.",
         6.5, "B.Tech", "Python,Java,SQL", 4, "active", "2026-01-10 09:00:00"),
        ("TCS Digital – Full Stack Developer", "Full Stack Developer",
         "Hyderabad", 700000, "2026-07-05",
         "Premium hiring for full-stack roles. Work on cutting-edge digital transformation projects.",
         7.5, "B.Tech", "React,Node.js,MongoDB,REST API", 4, "active", "2026-02-05 10:00:00"),
        ("TCS Research – Data Analyst", "Data Analyst",
         "Pune", 550000, "2026-05-30",
         "Analyze large datasets to drive business insights. Strong SQL and Python skills required.",
         7.0, "B.Tech", "Python,SQL,Pandas,Tableau", 4, "closed", "2026-01-20 09:00:00"),
        ("TCS BPS – Business Analyst", "Business Analyst",
         "Chennai", 420000, "2026-06-28",
         "Support business process transformation using data-driven insights.",
         6.5, "B.Tech", "Excel,SQL,Power BI", 4, "active", "2026-03-01 11:00:00"),
    ],
    "Infosys": [
        ("Infosys InfyTQ 2026 – Systems Engineer", "Systems Engineer",
         "Bengaluru", 380000, "2026-07-10",
         "Entry-level systems engineering role. Training provided in Java, Python, and cloud technologies.",
         6.5, "B.Tech", "Java,Python,SQL,Git", 4, "active", "2026-01-25 09:30:00"),
        ("Infosys Power Programmer 2026", "Software Developer",
         "Pune", 800000, "2026-06-30",
         "Elite track for top performers. Work on AI/ML and cloud-native applications.",
         8.0, "B.Tech", "Python,Machine Learning,AWS,Docker", 4, "active", "2026-02-15 10:00:00"),
        ("Infosys – Cloud Engineer", "Cloud Engineer",
         "Hyderabad", 650000, "2026-05-20",
         "Design and deploy cloud infrastructure on AWS and Azure.",
         7.5, "B.Tech", "AWS,Docker,Kubernetes,Linux", 4, "closed", "2026-01-18 09:00:00"),
        ("Infosys – Data Science Associate", "Data Scientist",
         "Bengaluru", 750000, "2026-07-30",
         "Build predictive models and data pipelines for enterprise clients.",
         7.5, "B.Tech", "Python,Machine Learning,TensorFlow,SQL", 4, "active", "2026-03-10 11:30:00"),
    ],
    "Wipro": [
        ("Wipro WILP 2026 – Software Engineer", "Software Engineer",
         "Pan India", 360000, "2026-07-15",
         "Work Integrated Learning Program. Earn while you learn with Wipro.",
         6.0, "B.Tech", "Java,C,SQL", 4, "active", "2026-02-08 09:00:00"),
        ("Wipro Turbo – Senior Developer", "Senior Software Developer",
         "Bengaluru", 650000, "2026-06-25",
         "Fast-track program for high-potential candidates with strong coding skills.",
         7.5, "B.Tech", "Python,Java,Spring Boot,MySQL", 4, "active", "2026-03-20 10:00:00"),
        ("Wipro – QA Engineer", "QA Engineer",
         "Chennai", 420000, "2026-05-10",
         "Manual and automated testing for enterprise applications.",
         6.5, "B.Tech", "Python,Selenium,SQL,Git", 4, "closed", "2026-01-28 09:00:00"),
    ],
    "Google": [
        ("Google STEP Intern 2026 – Software Engineering", "Software Engineering Intern",
         "Hyderabad", 1200000, "2026-08-20",
         "Google's Student Training in Engineering Program. Work on real Google products.",
         8.5, "B.Tech", "Python,Java,C++,Data Structures,Algorithms", 4, "active", "2026-03-15 10:00:00"),
        ("Google – Associate Product Manager", "Associate Product Manager",
         "Hyderabad", 1800000, "2026-08-05",
         "Drive product strategy and roadmap for Google's consumer products.",
         8.0, "B.Tech", "Python,SQL,Data Science,REST API", 4, "active", "2026-03-22 11:00:00"),
        ("Google – Machine Learning Engineer", "ML Engineer",
         "Hyderabad", 2200000, "2026-08-10",
         "Build and deploy ML models at Google scale. Work with TensorFlow and Google Cloud.",
         8.5, "B.Tech", "Python,Machine Learning,TensorFlow,Deep Learning,NLP", 4, "active", "2026-04-01 09:30:00"),
        ("Google – Site Reliability Engineer", "SRE",
         "Hyderabad", 1900000, "2026-05-05",
         "Ensure reliability and scalability of Google's infrastructure.",
         8.0, "B.Tech", "Python,Linux,Docker,Kubernetes,AWS", 4, "closed", "2026-02-10 09:00:00"),
        ("Google – UX Engineer", "UX Engineer",
         "Hyderabad", 1600000, "2026-07-25",
         "Bridge design and engineering to create exceptional user experiences.",
         7.5, "B.Tech", "JavaScript,React,TypeScript,HTML,CSS,Figma", 4, "active", "2026-04-10 10:00:00"),
    ],
    "Microsoft": [
        ("Microsoft – Software Engineer II", "Software Engineer",
         "Hyderabad", 2000000, "2026-08-15",
         "Build next-generation cloud services on Azure. Work with world-class engineers.",
         8.0, "B.Tech", "Python,Java,C++,Azure,Docker", 4, "active", "2026-03-05 09:00:00"),
        ("Microsoft – Data Engineer", "Data Engineer",
         "Hyderabad", 1700000, "2026-07-28",
         "Design and build data pipelines for Microsoft's analytics platform.",
         7.5, "B.Tech", "Python,SQL,Azure,Spark,Pandas", 4, "active", "2026-03-18 10:30:00"),
        ("Microsoft – AI Research Intern", "AI Research Intern",
         "Hyderabad", 1500000, "2026-07-20",
         "Conduct cutting-edge AI research with Microsoft Research India.",
         8.5, "B.Tech", "Python,Machine Learning,Deep Learning,TensorFlow,PyTorch", 4, "active", "2026-04-05 09:00:00"),
        ("Microsoft – DevOps Engineer", "DevOps Engineer",
         "Hyderabad", 1600000, "2026-05-15",
         "Automate and streamline CI/CD pipelines for Microsoft products.",
         7.0, "B.Tech", "Docker,Kubernetes,Azure,Linux,Git", 4, "closed", "2026-02-18 09:30:00"),
    ],
}

# ── AI match score (mirrors app.py logic) ─────────────────────────────────────
def ai_match_score(student, drive):
    score    = 0
    cgpa     = student.get("cgpa", 0) or 0
    req_cgpa = drive.get("req_cgpa", 0) or 0
    if cgpa >= req_cgpa:          score += 30
    elif cgpa >= req_cgpa - 0.5:  score += 15
    req = [s.strip().lower() for s in (drive.get("req_skills") or "").split(",") if s.strip()]
    stu = [s.strip().lower() for s in (student.get("skills") or "").split(",") if s.strip()]
    if req:
        matched = sum(1 for r in req if any(r in s or s in r for s in stu))
        score  += int((matched / len(req)) * 40)
    else:
        score += 30
    if not drive.get("req_degree") or student.get("degree") == drive.get("req_degree"):
        score += 20
    else:
        score += 5
    if not drive.get("req_year") or (student.get("year") or 0) >= (drive.get("req_year") or 0):
        score += 10
    return round(score, 1)

# ── Insert helpers ────────────────────────────────────────────────────────────
def insert_companies():
    inserted, skipped = [], []
    for name, email, pwd, phone, location, industry, website, about, created in COMPANIES:
        if mdb.companies.find_one({"email": email}):
            skipped.append(name); continue
        mdb.companies.insert_one({
            "name": name, "email": email, "pwd": pwd, "phone": phone,
            "location": location, "industry": industry,
            "website": website, "about": about, "created": created
        })
        inserted.append(name)
    return inserted, skipped

def insert_students():
    inserted, skipped = [], []
    for (name, email, pwd, phone, dob, branch, degree, year,
         cgpa, p12, p10, skills, bio, gender, location, created) in STUDENTS:
        if mdb.students.find_one({"email": email}):
            skipped.append(name); continue
        mdb.students.insert_one({
            "name": name, "email": email, "pwd": pwd, "phone": phone,
            "dob": dob, "branch": branch, "degree": degree, "year": year,
            "cgpa": cgpa, "p12": p12, "p10": p10,
            "skills": skills, "bio": bio, "gender": gender,
            "location": location, "photo": "", "resume": "",
            "resume_uploaded_on": "", "created": created
        })
        inserted.append(name)
    return inserted, skipped

def insert_drives():
    inserted, skipped = [], []
    for company_name, drive_list in DRIVES_TEMPLATE.items():
        company = mdb.companies.find_one({"name": company_name})
        if not company:
            print(f"  [WARN] Company '{company_name}' not found, skipping drives.")
            continue
        cid_str = str(company["_id"])
        for (title, role, loc, salary, deadline, desc,
             req_cgpa, req_degree, req_skills, req_year, status, created) in drive_list:
            if mdb.drives.find_one({"company_id": cid_str, "title": title}):
                skipped.append(title); continue
            mdb.drives.insert_one({
                "company_id": cid_str, "title": title, "role": role,
                "location": loc, "salary": salary, "deadline": deadline,
                "description": desc, "req_cgpa": req_cgpa,
                "req_degree": req_degree, "req_skills": req_skills,
                "req_year": req_year, "status": status, "created": created
            })
            inserted.append(f"{company_name} – {title}")
    return inserted, skipped

def insert_applications():
    inserted = 0
    skipped  = 0
    all_students = list(mdb.students.find())
    all_drives   = list(mdb.drives.find())
    if not all_students or not all_drives:
        print("  [WARN] No students or drives found – skipping applications.")
        return 0, 0

    status_pool = (
        ["applied"] * 3 + ["eligible"] * 3 + ["test"] * 2 +
        ["interview"] * 2 + ["selected"] * 2 + ["rejected"] * 2
    )
    start_date      = datetime(2025, 9, 1)
    end_date        = datetime(2026, 6, 12)
    date_range_days = (end_date - start_date).days
    random.seed(42)

    for student in all_students:
        sid_str    = str(student["_id"])
        num_apps   = random.randint(2, 4)
        chosen     = random.sample(all_drives, min(num_apps, len(all_drives)))
        for drive in chosen:
            did_str = str(drive["_id"])
            if mdb.applications.find_one({"student_id": sid_str, "drive_id": did_str}):
                skipped += 1; continue
            score      = ai_match_score(student, drive)
            status     = random.choice(status_pool)
            offset     = random.randint(0, date_range_days)
            applied_on = (start_date + timedelta(days=offset)).strftime("%Y-%m-%d %H:%M:%S")
            try:
                mdb.applications.insert_one({
                    "student_id": sid_str, "drive_id": did_str,
                    "status": status, "ai_score": score, "applied_on": applied_on
                })
                inserted += 1
            except DuplicateKeyError:
                skipped += 1
    return inserted, skipped

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n🔧 Ensuring indexes...")
    ensure_indexes()

    print("\n📊 STEP 1 – Checking existing data...")
    check_existing()

    print("\n🏢 STEP 2 – Inserting companies...")
    ins_co, skip_co = insert_companies()
    for n in ins_co:  print(f"  ✅ Added   : {n}")
    for n in skip_co: print(f"  ⏭  Skipped : {n} (already exists)")

    print("\n🎓 STEP 3 – Inserting students...")
    ins_st, skip_st = insert_students()
    for n in ins_st:  print(f"  ✅ Added   : {n}")
    for n in skip_st: print(f"  ⏭  Skipped : {n} (already exists)")

    print("\n📋 STEP 4 – Inserting drives...")
    ins_dr, skip_dr = insert_drives()
    for n in ins_dr:  print(f"  ✅ Added   : {n}")
    for n in skip_dr: print(f"  ⏭  Skipped : {n} (already exists)")

    print("\n📝 STEP 5 – Inserting applications...")
    ins_ap, skip_ap = insert_applications()
    print(f"  ✅ Added   : {ins_ap} applications")
    print(f"  ⏭  Skipped : {skip_ap} (already exist)")

    print("\n" + "=" * 55)
    print("FINAL SUMMARY")
    check_existing()

    from collections import Counter
    print("\nApplication status breakdown:")
    statuses = [a["status"] for a in mdb.applications.find({}, {"status": 1})]
    for status, cnt in Counter(statuses).most_common():
        print(f"  {status:<12}: {cnt}")

    scores = [a["ai_score"] for a in mdb.applications.find({}, {"ai_score": 1}) if a.get("ai_score")]
    if scores:
        print(f"\nAI score range:  Min={min(scores)}  Max={max(scores)}  Avg={round(sum(scores)/len(scores),1)}")

    from collections import defaultdict
    monthly = defaultdict(int)
    for a in mdb.applications.find({}, {"applied_on": 1}):
        m = (a.get("applied_on") or "")[:7]
        if m: monthly[m] += 1
    print("\nApplications per month:")
    for m in sorted(monthly)[:12]:
        print(f"  {m}: {monthly[m]} applications")

    print("\n✅ Seeding complete!")

if __name__ == "__main__":
    main()
