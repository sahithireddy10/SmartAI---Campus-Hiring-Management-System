"""
seed_data.py – Populate MongoDB with SmartHire AI demo data (2026 cohort).
Two colleges with completely different students, companies and drives.
Run once:  python seed_data.py
"""
import os, random
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
client    = MongoClient(MONGO_URI)
mdb       = client["smarthire"]

# ── Indexes ───────────────────────────────────────────────────────────────────
def ensure_indexes():
    mdb.colleges.create_index("email", unique=True)
    mdb.colleges.create_index("code",  unique=True)
    mdb.students.create_index([("email",1),("college_id",1)], unique=True)
    mdb.companies.create_index([("email",1),("college_id",1)], unique=True)
    mdb.applications.create_index(
        [("student_id", ASCENDING), ("drive_id", ASCENDING)], unique=True)
    mdb.drives.create_index("college_id")
    mdb.students.create_index("college_id")
    mdb.companies.create_index("college_id")

def check_existing():
    print("=" * 55)
    for k, v in [("Colleges", mdb.colleges.count_documents({})),
                 ("Students", mdb.students.count_documents({})),
                 ("Companies", mdb.companies.count_documents({})),
                 ("Drives", mdb.drives.count_documents({})),
                 ("Applications", mdb.applications.count_documents({}))]:
        print(f"  {k:<14}: {v}")
    print("=" * 55)

# ─────────────────────────────────────────────────────────────────────────────
# COLLEGES
# ─────────────────────────────────────────────────────────────────────────────
DEMO_COLLEGES = [
    {
        "name": "Woxsen University",
        "code": "WU2026",
        "email": "admin@woxsen.edu.in",
        "pwd":   "woxsen@123",
        "phone": "040-23456789",
        "location": "Hyderabad, Telangana",
        "university": "Woxsen University",
        "active": True,
        "created": "2025-10-01 09:00:00",
        "admins": [
            {"name":"Dr. Priya Sharma","email":"admin@woxsen.edu.in",
             "pwd":"woxsen@123","phone":"9876500001","role":"primary"},
            {"name":"Mr. Rahul Nair","email":"rahul.nair@woxsen.edu.in",
             "pwd":"rahul@123","phone":"9876500002","role":"secondary"},
        ]
    },
    {
        "name": "Lords Institute of Engineering and Technology",
        "code": "LIET2026",
        "email": "tpo@lords.ac.in",
        "pwd":   "lords@123",
        "phone": "040-23056789",
        "location": "Hyderabad, Telangana",
        "university": "Lords Institute of Engineering and Technology",
        "active": True,
        "created": "2025-10-05 10:00:00",
        "admins": [
            {"name":"Dr. Sameera Khan","email":"tpo@lords.ac.in",
             "pwd":"lords@123","phone":"9876500003","role":"primary"},
            {"name":"Mr. Arun Prakash","email":"arun.prakash@lords.ac.in",
             "pwd":"arun@123","phone":"9876500004","role":"secondary"},
        ]
    },
]

def get_or_create_colleges():
    result = []
    for c in DEMO_COLLEGES:
        existing = mdb.colleges.find_one({"code": c["code"]})
        if existing:
            print(f"  ⏭  Exists: {c['name']}")
            result.append((str(existing["_id"]), c["name"]))
        else:
            ins = mdb.colleges.insert_one(c.copy())
            print(f"  ✅ Created: {c['name']}")
            print(f"     Admin 1: {c['admins'][0]['email']} / {c['admins'][0]['pwd']}")
            print(f"     Admin 2: {c['admins'][1]['email']} / {c['admins'][1]['pwd']}")
            result.append((str(ins.inserted_id), c["name"]))
    return result

# ─────────────────────────────────────────────────────────────────────────────
# WOXSEN DATA
# ─────────────────────────────────────────────────────────────────────────────
WOXSEN_STUDENTS = [
    # (name, email, pwd, phone, dob, branch, degree, year, cgpa, p12, p10, skills, bio, gender, location, created)
    ("Arjun Sharma",  "arjun.sharma@woxsen.edu.in",  "pass@123","9876541001","2005-03-15",
     "CSE","B.Tech",4,8.7,88.4,91.2,"Python,Java,Machine Learning,SQL,Django,Git",
     "Passionate about AI and backend development.","Male","Delhi","2026-02-10 09:15:00"),
    ("Priya Nair",    "priya.nair@woxsen.edu.in",    "pass@123","9876541002","2005-07-22",
     "CSE","B.Tech",4,9.1,92.0,89.5,"Python,React,Node.js,MongoDB,REST API,Docker",
     "Full-stack developer with a love for clean UI.","Female","Kochi","2026-02-18 10:30:00"),
    ("Sneha Reddy",   "sneha.reddy@woxsen.edu.in",   "pass@123","9876541003","2006-01-30",
     "IT","B.Tech",4,8.3,85.5,87.0,"JavaScript,React,HTML,CSS,TypeScript,Figma",
     "UI/UX focused frontend developer.","Female","Hyderabad","2026-03-05 11:00:00"),
    ("Vikram Iyer",   "vikram.iyer@woxsen.edu.in",   "pass@123","9876541004","2005-06-14",
     "EEE","B.Tech",4,8.5,87.0,90.0,"Python,MATLAB,C,Embedded Systems,AWS",
     "Electrical engineer with cloud computing interest.","Male","Bengaluru","2026-04-03 08:30:00"),
    ("Ananya Bose",   "ananya.bose@woxsen.edu.in",   "pass@123","9876541005","2006-04-03",
     "EEE","B.Tech",4,9.3,94.0,92.5,"Python,Machine Learning,TensorFlow,Deep Learning,NLP",
     "AI researcher passionate about neural networks.","Female","Kolkata","2026-04-20 13:00:00"),
    ("Rohit Gupta",   "rohit.gupta@woxsen.edu.in",   "pass@123","9876541006","2005-11-20",
     "CSE","B.Tech",4,8.0,82.0,86.0,"Java,Spring Boot,Microservices,Kubernetes,Docker",
     "Backend developer with microservices expertise.","Male","Mumbai","2026-03-15 10:00:00"),
    ("Meera Joshi",   "meera.joshi@woxsen.edu.in",   "pass@123","9876541007","2006-02-14",
     "IT","B.Tech",4,7.9,80.5,84.0,"Python,Data Science,Pandas,NumPy,Tableau",
     "Data analyst with a passion for visualization.","Female","Pune","2026-02-28 11:30:00"),
    ("Aditya Rao",    "aditya.rao@woxsen.edu.in",    "pass@123","9876541008","2005-08-30",
     "MECH","B.Tech",4,7.4,76.0,80.0,"AutoCAD,ANSYS,SolidWorks,MATLAB",
     "Mechanical engineer with simulation expertise.","Male","Hyderabad","2026-01-20 09:00:00"),
    ("Kavya Menon",   "kavya.menon@woxsen.edu.in",   "pass@123","9876541009","2006-06-18",
     "CSE","B.Tech",4,8.8,90.0,88.0,"Python,AWS,Terraform,Linux,Docker",
     "Cloud enthusiast aiming for DevOps career.","Female","Chennai","2026-05-01 14:00:00"),
    ("Siddharth Das", "siddharth.das@woxsen.edu.in", "pass@123","9876541010","2005-04-25",
     "IT","B.Tech",4,7.6,79.0,83.5,"SQL,Power BI,Excel,Python,Tableau",
     "Business intelligence and analytics focused.","Male","Kolkata","2026-03-22 12:00:00"),
]

WOXSEN_COMPANIES = [
    # (name, email, pwd, phone, location, industry, website, about, created)
    ("TCS","hr.woxsen@tcs.com","tcs@123","1800-209-3111","Mumbai, Maharashtra","IT Services",
     "https://www.tcs.com","Tata Consultancy Services – global IT leader.","2025-10-15 09:00:00"),
    ("Infosys","campus.woxsen@infosys.com","infosys@123","1800-425-4968","Bengaluru, Karnataka","IT Services",
     "https://www.infosys.com","Infosys – next-generation digital services.","2025-10-28 10:30:00"),
    ("Google","woxsen@google.com","google@123","+1-650-253-0000","Hyderabad, Telangana","Technology",
     "https://careers.google.com","Google – search, cloud, and AI.","2025-11-20 14:00:00"),
    ("Microsoft","woxsen@microsoft.com","msft@123","+1-425-882-8080","Hyderabad, Telangana","Technology",
     "https://careers.microsoft.com","Microsoft – cloud and productivity software.","2025-12-05 09:30:00"),
    ("Amazon","woxsen@amazon.com","amazon@123","+1-206-266-1000","Hyderabad, Telangana","E-Commerce & Cloud",
     "https://amazon.jobs","Amazon – e-commerce, AWS, and AI.","2025-12-10 10:00:00"),
]

WOXSEN_DRIVES = {
    "TCS": [
        ("TCS NQT 2026 – Software Engineer","Software Engineer","Pan India",350000,"2026-07-20",
         "TCS NQT for fresh B.Tech graduates.",6.5,"B.Tech","Python,Java,SQL",4,"active","2026-01-10 09:00:00"),
        ("TCS Digital – Full Stack Developer","Full Stack Developer","Hyderabad",700000,"2026-07-05",
         "Premium full-stack roles in digital transformation.",7.5,"B.Tech","React,Node.js,MongoDB",4,"active","2026-02-05 10:00:00"),
        ("TCS BPS – Business Analyst","Business Analyst","Chennai",420000,"2026-06-28",
         "Data-driven business process transformation.",6.5,"B.Tech","Excel,SQL,Power BI",4,"active","2026-03-01 11:00:00"),
    ],
    "Infosys": [
        ("Infosys InfyTQ 2026 – Systems Engineer","Systems Engineer","Bengaluru",380000,"2026-07-10",
         "Entry-level systems engineering with training.",6.5,"B.Tech","Java,Python,SQL,Git",4,"active","2026-01-25 09:30:00"),
        ("Infosys Power Programmer 2026","Software Developer","Pune",800000,"2026-06-30",
         "Elite track for top performers in AI/ML.",8.0,"B.Tech","Python,Machine Learning,AWS,Docker",4,"active","2026-02-15 10:00:00"),
        ("Infosys – Data Science Associate","Data Scientist","Bengaluru",750000,"2026-07-30",
         "Build predictive models for enterprise clients.",7.5,"B.Tech","Python,Machine Learning,TensorFlow,SQL",4,"active","2026-03-10 11:30:00"),
    ],
    "Google": [
        ("Google STEP Intern 2026","Software Engineering Intern","Hyderabad",1200000,"2026-08-20",
         "Student Training in Engineering Program.",8.5,"B.Tech","Python,Java,C++,Algorithms",4,"active","2026-03-15 10:00:00"),
        ("Google – ML Engineer","ML Engineer","Hyderabad",2200000,"2026-08-10",
         "Build ML models at Google scale.",8.5,"B.Tech","Python,Machine Learning,TensorFlow,Deep Learning",4,"active","2026-04-01 09:30:00"),
        ("Google – UX Engineer","UX Engineer","Hyderabad",1600000,"2026-07-25",
         "Bridge design and engineering for user experiences.",7.5,"B.Tech","JavaScript,React,TypeScript,Figma",4,"active","2026-04-10 10:00:00"),
    ],
    "Microsoft": [
        ("Microsoft – Software Engineer II","Software Engineer","Hyderabad",2000000,"2026-08-15",
         "Build cloud services on Azure.",8.0,"B.Tech","Python,Java,C++,Azure,Docker",4,"active","2026-03-05 09:00:00"),
        ("Microsoft – AI Research Intern","AI Research Intern","Hyderabad",1500000,"2026-07-20",
         "Cutting-edge AI research with Microsoft Research.",8.5,"B.Tech","Python,Machine Learning,Deep Learning,PyTorch",4,"active","2026-04-05 09:00:00"),
    ],
    "Amazon": [
        ("Amazon – SDE I","Software Development Engineer I","Hyderabad",1800000,"2026-08-01",
         "Build and maintain large-scale distributed systems.",7.5,"B.Tech","Java,Python,AWS,Data Structures",4,"active","2026-03-20 10:00:00"),
        ("Amazon – Data Analyst","Data Analyst","Hyderabad",1200000,"2026-07-15",
         "Analyse business data to drive product decisions.",7.0,"B.Tech","SQL,Python,Tableau,Excel",4,"active","2026-03-25 11:00:00"),
        ("Amazon AWS – Cloud Support","Cloud Support Engineer","Hyderabad",950000,"2026-05-30",
         "Provide technical support for AWS services.",6.5,"B.Tech","AWS,Linux,Networking,Python",4,"closed","2026-02-10 09:00:00"),
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# LORDS DATA
# ─────────────────────────────────────────────────────────────────────────────
LORDS_STUDENTS = [
    ("Mohammed Salman","salman.m@lords.ac.in","pass@123","9876542001","2005-05-10",
     "CSE","B.Tech",4,7.8,80.0,85.0,"Python,MySQL,Django,HTML,CSS",
     "Web developer learning full-stack technologies.","Male","Hyderabad","2026-02-12 09:00:00"),
    ("Fatima Shaikh",  "fatima.s@lords.ac.in",  "pass@123","9876542002","2006-03-20",
     "IT","B.Tech",4,8.1,83.5,87.0,"JavaScript,React,Node.js,MongoDB",
     "Frontend developer passionate about UI.","Female","Mumbai","2026-02-20 10:00:00"),
    ("Ravi Teja",      "ravi.teja@lords.ac.in",  "pass@123","9876542003","2005-10-05",
     "ECE","B.Tech",4,7.3,75.0,79.0,"C,C++,Embedded Systems,Arduino,IoT",
     "Embedded systems engineer building IoT products.","Male","Hyderabad","2026-01-18 08:30:00"),
    ("Lakshmi Devi",   "lakshmi.d@lords.ac.in",  "pass@123","9876542004","2006-07-14",
     "IT","B.Tech",4,8.5,87.0,89.0,"Java,Spring Boot,Hibernate,MySQL,Git",
     "Backend Java developer with spring expertise.","Female","Vijayawada","2026-03-10 11:00:00"),
    ("Suresh Babu",    "suresh.b@lords.ac.in",   "pass@123","9876542005","2005-12-01",
     "MECH","B.Tech",4,7.0,72.0,76.0,"AutoCAD,SolidWorks,MATLAB,Python",
     "Mechanical engineer interested in automation.","Male","Hyderabad","2026-01-25 09:30:00"),
    ("Nisha Rani",     "nisha.r@lords.ac.in",    "pass@123","9876542006","2006-09-22",
     "CSE","B.Tech",4,8.4,86.0,88.5,"Python,Machine Learning,Scikit-learn,NumPy,Pandas",
     "Data science enthusiast with ML knowledge.","Female","Nalgonda","2026-04-05 10:00:00"),
    ("Kiran Kumar",    "kiran.k@lords.ac.in",    "pass@123","9876542007","2005-07-08",
     "EEE","B.Tech",4,7.6,78.5,82.0,"MATLAB,Simulink,Python,PLC,SCADA",
     "Electrical engineer with automation skills.","Male","Warangal","2026-02-08 09:00:00"),
    ("Pooja Reddy",    "pooja.reddy@lords.ac.in","pass@123","9876542008","2006-11-30",
     "CSE","B.Tech",4,9.0,91.5,93.0,"Python,Java,C++,Data Structures,Algorithms",
     "Strong in competitive programming and DSA.","Female","Hyderabad","2026-05-02 13:00:00"),
    ("Arshad Khan",    "arshad.k@lords.ac.in",   "pass@123","9876542009","2005-02-18",
     "IT","B.Tech",4,7.5,77.0,81.5,"SQL,Power BI,Tableau,Excel,Python",
     "Business intelligence and reporting analyst.","Male","Hyderabad","2026-03-18 10:30:00"),
    ("Deepika Rao",    "deepika.r@lords.ac.in",  "pass@123","9876542010","2006-01-05",
     "CSE","B.Tech",4,8.2,84.0,86.5,"Android,Kotlin,Java,Firebase,REST API",
     "Mobile app developer focused on Android.","Female","Karimnagar","2026-04-15 14:00:00"),
]

LORDS_COMPANIES = [
    ("Wipro","hr.lords@wipro.com","wipro@123","1800-102-5799","Bengaluru, Karnataka","IT Services",
     "https://www.wipro.com","Wipro – global IT consulting and services.","2025-11-10 11:00:00"),
    ("HCL Technologies","campus@hcl.com","hcl@123","0120-6125000","Noida, Uttar Pradesh","IT Services",
     "https://www.hcltech.com","HCL Technologies – IT services and consulting.","2025-11-15 09:30:00"),
    ("Tech Mahindra","talent@techmahindra.com","techm@123","020-66601000","Pune, Maharashtra","IT Services",
     "https://www.techmahindra.com","Tech Mahindra – digital transformation company.","2025-11-20 10:00:00"),
    ("Capgemini","campus@capgemini.com","capgemini@123","022-67551234","Mumbai, Maharashtra","IT Consulting",
     "https://www.capgemini.com","Capgemini – global IT and consulting services.","2025-12-01 09:00:00"),
    ("L&T Infotech","nxtwave@lntecc.com","lnt@123","022-67525656","Mumbai, Maharashtra","IT Services",
     "https://www.ltimindtree.com","LTIMindtree – engineering and IT services.","2025-12-08 10:00:00"),
]

LORDS_DRIVES = {
    "Wipro": [
        ("Wipro WILP 2026 – Software Engineer","Software Engineer","Pan India",360000,"2026-07-15",
         "Work Integrated Learning Program.",6.0,"B.Tech","Java,C,SQL",4,"active","2026-02-08 09:00:00"),
        ("Wipro Turbo – Senior Developer","Senior Software Developer","Bengaluru",650000,"2026-06-25",
         "Fast-track for high-potential candidates.",7.5,"B.Tech","Python,Java,Spring Boot,MySQL",4,"active","2026-03-20 10:00:00"),
        ("Wipro – QA Engineer","QA Engineer","Chennai",420000,"2026-05-10",
         "Manual and automated testing.",6.5,"B.Tech","Python,Selenium,SQL,Git",4,"closed","2026-01-28 09:00:00"),
    ],
    "HCL Technologies": [
        ("HCL – Software Engineer Trainee","Software Engineer Trainee","Noida",420000,"2026-07-20",
         "Graduate trainee program with full-stack training.",6.5,"B.Tech","Java,Python,SQL,HTML,CSS",4,"active","2026-02-01 09:00:00"),
        ("HCL – Data Analyst","Data Analyst","Chennai",500000,"2026-07-10",
         "Analyse and visualise data for client decisions.",7.0,"B.Tech","Python,SQL,Tableau,Excel",4,"active","2026-02-20 10:30:00"),
        ("HCL – Embedded Engineer","Embedded Engineer","Bengaluru",480000,"2026-06-20",
         "Firmware development for industrial systems.",6.5,"B.Tech","C,C++,Embedded Systems,RTOS",4,"active","2026-03-05 11:00:00"),
    ],
    "Tech Mahindra": [
        ("TechM – Associate Software Engineer","Associate Software Engineer","Pune",380000,"2026-07-25",
         "Entry-level software engineering role.",6.0,"B.Tech","Java,Python,SQL,Git",4,"active","2026-02-15 09:30:00"),
        ("TechM – Network Engineer","Network Engineer","Hyderabad",450000,"2026-07-05",
         "Design and maintain enterprise networks.",6.5,"B.Tech","Networking,Linux,Python,CCNA",4,"active","2026-03-01 10:00:00"),
    ],
    "Capgemini": [
        ("Capgemini – Analyst","Analyst","Mumbai",600000,"2026-08-01",
         "Business and IT analysis for global clients.",7.0,"B.Tech","Python,SQL,Excel,Power BI",4,"active","2026-03-10 09:00:00"),
        ("Capgemini – Software Engineer","Software Engineer","Bengaluru",700000,"2026-08-15",
         "Full-stack development for enterprise projects.",7.5,"B.Tech","Java,React,Spring Boot,MySQL",4,"active","2026-03-22 10:00:00"),
        ("Capgemini – DevOps Intern","DevOps Intern","Pune",550000,"2026-05-20",
         "CI/CD pipelines and cloud automation.",7.0,"B.Tech","Docker,Kubernetes,Jenkins,Git,Linux",4,"closed","2026-02-05 09:00:00"),
    ],
    "L&T Infotech": [
        ("LTIMindtree – Graduate Engineer","Graduate Engineer Trainee","Mumbai",420000,"2026-07-30",
         "Engineering trainee with hands-on project exposure.",6.5,"B.Tech","Java,Python,SQL",4,"active","2026-02-25 09:00:00"),
        ("LTIMindtree – Data Engineer","Data Engineer","Pune",750000,"2026-08-05",
         "Build data pipelines and ETL processes.",7.5,"B.Tech","Python,SQL,Spark,AWS",4,"active","2026-03-15 10:30:00"),
    ],
}

# ── AI match score ────────────────────────────────────────────────────────────
def ai_match_score(student, drive):
    score = 0
    cgpa, req_cgpa = student.get("cgpa",0) or 0, drive.get("req_cgpa",0) or 0
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
def insert_companies(college_id, companies):
    ins, skp = [], []
    for name, email, pwd, phone, location, industry, website, about, created in companies:
        if mdb.companies.find_one({"email": email, "college_id": college_id}):
            skp.append(name); continue
        mdb.companies.insert_one({"college_id": college_id, "name": name, "email": email,
            "pwd": pwd, "phone": phone, "location": location, "industry": industry,
            "website": website, "about": about, "created": created})
        ins.append(name)
    return ins, skp

def insert_students(college_id, students):
    ins, skp = [], []
    for (name, email, pwd, phone, dob, branch, degree, year,
         cgpa, p12, p10, skills, bio, gender, location, created) in students:
        if mdb.students.find_one({"email": email, "college_id": college_id}):
            skp.append(name); continue
        mdb.students.insert_one({"college_id": college_id, "name": name, "email": email,
            "pwd": pwd, "phone": phone, "dob": dob, "branch": branch, "degree": degree,
            "year": year, "cgpa": cgpa, "p12": p12, "p10": p10, "skills": skills,
            "bio": bio, "gender": gender, "location": location, "photo": "", "resume": "",
            "resume_uploaded_on": "", "created": created})
        ins.append(name)
    return ins, skp

def insert_drives(college_id, drives_template):
    ins, skp = [], []
    for company_name, drive_list in drives_template.items():
        company = mdb.companies.find_one({"name": company_name, "college_id": college_id})
        if not company:
            print(f"  [WARN] Company '{company_name}' not found"); continue
        cid_str = str(company["_id"])
        for (title, role, loc, salary, deadline, desc,
             req_cgpa, req_degree, req_skills, req_year, status, created) in drive_list:
            if mdb.drives.find_one({"company_id": cid_str, "title": title, "college_id": college_id}):
                skp.append(title); continue
            mdb.drives.insert_one({"college_id": college_id, "company_id": cid_str,
                "title": title, "role": role, "location": loc, "salary": salary,
                "deadline": deadline, "description": desc, "req_cgpa": req_cgpa,
                "req_degree": req_degree, "req_skills": req_skills,
                "req_year": req_year, "status": status, "created": created})
            ins.append(f"{company_name} – {title}")
    return ins, skp

def insert_applications(college_id):
    ins, skp = 0, 0
    all_students = list(mdb.students.find({"college_id": college_id}))
    all_drives   = list(mdb.drives.find({"college_id": college_id}))
    if not all_students or not all_drives:
        print("  [WARN] No students or drives – skipping."); return 0, 0
    status_pool = (["applied"]*3 + ["eligible"]*3 + ["test"]*2 +
                   ["interview"]*2 + ["selected"]*2 + ["rejected"]*2)
    start_date, end_date = datetime(2025, 9, 1), datetime(2026, 6, 12)
    days = (end_date - start_date).days
    random.seed(42)
    for student in all_students:
        sid = str(student["_id"])
        for drive in random.sample(all_drives, min(random.randint(2,4), len(all_drives))):
            did = str(drive["_id"])
            if mdb.applications.find_one({"student_id": sid, "drive_id": did}):
                skp += 1; continue
            try:
                mdb.applications.insert_one({"student_id": sid, "drive_id": did,
                    "status": random.choice(status_pool),
                    "ai_score": ai_match_score(student, drive),
                    "applied_on": (start_date + timedelta(days=random.randint(0,days))).strftime("%Y-%m-%d %H:%M:%S")
                }); ins += 1
            except DuplicateKeyError:
                skp += 1
    return ins, skp

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n🔧 Ensuring indexes...")
    ensure_indexes()

    print("\n📊 STEP 1 – Existing data:")
    check_existing()

    print("\n🏫 STEP 2 – Colleges...")
    colleges = get_or_create_colleges()

    # Map each college to its data
    college_data = {
        "Woxsen University": {
            "students":  WOXSEN_STUDENTS,
            "companies": WOXSEN_COMPANIES,
            "drives":    WOXSEN_DRIVES,
        },
        "Lords Institute of Engineering and Technology": {
            "students":  LORDS_STUDENTS,
            "companies": LORDS_COMPANIES,
            "drives":    LORDS_DRIVES,
        },
    }

    for college_id, college_name in colleges:
        data = college_data.get(college_name)
        if not data:
            print(f"\n  [SKIP] No data defined for: {college_name}")
            continue

        print(f"\n{'='*55}")
        print(f"🏫  {college_name}")
        print(f"{'='*55}")

        print("\n🏢 Companies...")
        ins, skp = insert_companies(college_id, data["companies"])
        for n in ins: print(f"  ✅ {n}")
        for n in skp: print(f"  ⏭  {n}")

        print("\n🎓 Students...")
        ins, skp = insert_students(college_id, data["students"])
        for n in ins: print(f"  ✅ {n}")
        for n in skp: print(f"  ⏭  {n}")

        print("\n📋 Drives...")
        ins, skp = insert_drives(college_id, data["drives"])
        for n in ins: print(f"  ✅ {n}")
        for n in skp: print(f"  ⏭  {n}")

        print("\n📝 Applications...")
        ins, skp = insert_applications(college_id)
        print(f"  ✅ Added: {ins}  ⏭  Skipped: {skp}")

    print("\n" + "="*55)
    print("FINAL SUMMARY")
    check_existing()

    from collections import Counter
    print("\nStatus breakdown:")
    for s, c in Counter(a["status"] for a in mdb.applications.find({},{"status":1})).most_common():
        print(f"  {s:<12}: {c}")

    print("\n✅ Done!")
    print("\n📋 Credentials:")
    print("  Super Admin: superadmin@smarthire.ai / super@123  →  /superadmin/login")
    for c in DEMO_COLLEGES:
        print(f"\n  🏫 {c['name']}")
        for a in c["admins"]:
            print(f"     {a['role']}: {a['email']} / {a['pwd']}")
    print("\n  Woxsen students:  arjun.sharma@woxsen.edu.in / pass@123")
    print("  Lords  students:  salman.m@lords.ac.in / pass@123")
    print("  Woxsen companies: hr.woxsen@tcs.com / tcs@123")
    print("  Lords  companies: hr.lords@wipro.com / wipro@123")

if __name__ == "__main__":
    main()
