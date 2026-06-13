import random
import string
import datetime
from collections import defaultdict

from database.db_manager import DBManager  # Central config helper
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import sessionmaker

# ----------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------
def random_name():
    first = random.choice(
        [
            "Aarav",
            "Aditi",
            "Rohan",
            "Sneha",
            "Kiran",
            "Maya",
            "Vikram",
            "Priya",
            "Nikhil",
            "Ananya",
            "Sanjay",
            "Riya",
            "Arjun",
            "Neha",
            "Vivek",
            "Pooja",
        ]
    )
    last = random.choice(
        [
            "Sharma",
            "Patel",
            "Gupta",
            "Singh",
            "Kumar",
            "Verma",
            "Reddy",
            "Iyer",
            "Das",
            "Chowdhury",
            "Nair",
            "Ghosh",
            "Mehta",
            "Jain",
        ]
    )
    return f"{first} {last}"


def random_gender():
    return random.choice(["Male", "Female", "Other"])


def random_date(start_year=2016, end_year=2022):
    start = datetime.date(start_year, 1, 1)
    end = datetime.date(end_year, 12, 31)
    delta = end - start
    return start + datetime.timedelta(days=random.randint(0, delta.days))


def generate_registration_number(admission_year, seq):
    # Example: 2020ENG00123
    return f"{admission_year}ENG{seq:05d}"

# ----------------------------------------------------------------------
# Main population routine
# ----------------------------------------------------------------------
def main():
    # --------------------------------------------------------------
    # 1. Fetch ERP connection string from central SQLite config
    # --------------------------------------------------------------
    db_manager = DBManager()
    engine = db_manager.get_erp_engine()
    if engine is None:
        raise RuntimeError(
            "Unable to obtain ERP connection string. Make sure the ERP has been configured in the Central DB."
        )

    metadata = MetaData()

    # --------------------------------------------------------------
    # 2. Define schema (drop if exists → recreate)
    # --------------------------------------------------------------
    # Departments
    dept = Table(
        "departments",
        metadata,
        Column("dept_id", Integer, primary_key=True, autoincrement=True),
        Column("dept_code", String(10), unique=True, nullable=False),
        Column("dept_name", String(100), nullable=False),
        Column("dept_head_id", Integer, ForeignKey("hods.hod_id")),
    )

    # HODs
    hod = Table(
        "hods",
        metadata,
        Column("hod_id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(100), nullable=False),
        Column("email", String(120), unique=True, nullable=False),
        Column("dept_id", Integer, ForeignKey("departments.dept_id")),
    )

    # Faculty
    faculty = Table(
        "faculty",
        metadata,
        Column("faculty_id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(100), nullable=False),
        Column("email", String(120), unique=True, nullable=False),
        Column("designation", String(50), nullable=False),
        Column("dept_id", Integer, ForeignKey("departments.dept_id")),
    )

    # Students
    student = Table(
        "students",
        metadata,
        Column("student_id", Integer, primary_key=True, autoincrement=True),
        Column("registration_no", String(20), unique=True, nullable=False),
        Column("name", String(100), nullable=False),
        Column("gender", String(10), nullable=False),
        Column("admission_year", Integer, nullable=False),
        Column("dept_id", Integer, ForeignKey("departments.dept_id")),
        Column("year", Integer, nullable=False),  # 1‑4
    )

    # Courses (department‑wide)
    course = Table(
        "courses",
        metadata,
        Column("course_id", Integer, primary_key=True, autoincrement=True),
        Column("course_code", String(10), nullable=False),
        Column("course_name", String(100), nullable=False),
        Column("dept_id", Integer, ForeignKey("departments.dept_id")),
        UniqueConstraint("course_code", "dept_id", name="uq_course_dept"),
    )

    # Subjects (linked to courses)
    subject = Table(
        "subjects",
        metadata,
        Column("subject_id", Integer, primary_key=True, autoincrement=True),
        Column("subject_code", String(10), nullable=False),
        Column("subject_name", String(100), nullable=False),
        Column("course_id", Integer, ForeignKey("courses.course_id")),
        UniqueConstraint("subject_code", "course_id", name="uq_subject_course"),
    )

    # Enrollments (student ↔ subject per semester)
    enrollment = Table(
        "enrollments",
        metadata,
        Column("enrollment_id", Integer, primary_key=True, autoincrement=True),
        Column("student_id", Integer, ForeignKey("students.student_id")),
        Column("subject_id", Integer, ForeignKey("subjects.subject_id")),
        Column("semester", Integer, nullable=False),  # 1‑8 (2 per year)
        Column("year", Integer, nullable=False),
    )

    # Academic records (per student per semester)
    academic = Table(
        "academic_records",
        metadata,
        Column("record_id", Integer, primary_key=True, autoincrement=True),
        Column("student_id", Integer, ForeignKey("students.student_id")),
        Column("semester", Integer, nullable=False),
        Column("year", Integer, nullable=False),
        Column("cgpa", Float, nullable=False),
        Column("attendance_percentage", Float, nullable=False),
        Column("backlog_count", Integer, nullable=False),
        Column("internal_marks", Float, nullable=False),
        Column("mid_exam_score", Float, nullable=False),
        Column("lab_performance", Float, nullable=False),
        Column("assignment_marks", Float, nullable=False),
    )

    # Attendance logs (detailed per day)
    attendance = Table(
        "attendance_logs",
        metadata,
        Column("log_id", Integer, primary_key=True, autoincrement=True),
        Column("student_id", Integer, ForeignKey("students.student_id")),
        Column("date", Date, nullable=False),
        Column("present", Integer, nullable=False),  # 1 = present, 0 = absent
    )

    # Exams (optional detailed table)
    exam = Table(
        "exams",
        metadata,
        Column("exam_id", Integer, primary_key=True, autoincrement=True),
        Column("student_id", Integer, ForeignKey("students.student_id")),
        Column("subject_id", Integer, ForeignKey("subjects.subject_id")),
        Column("semester", Integer, nullable=False),
        Column("score", Float, nullable=False),
    )

    # Labs (optional detailed table)
    lab = Table(
        "labs",
        metadata,
        Column("lab_id", Integer, primary_key=True, autoincrement=True),
        Column("student_id", Integer, ForeignKey("students.student_id")),
        Column("subject_id", Integer, ForeignKey("subjects.subject_id")),
        Column("semester", Integer, nullable=False),
        Column("score", Float, nullable=False),
    )

    # --------------------------------------------------------------
    # 3. Reset database (drop all tables)
    # --------------------------------------------------------------
    print("Dropping existing ERP tables if any...")
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF;"))
        for tbl in reversed(metadata.sorted_tables):
            conn.execute(text(f"DROP TABLE IF EXISTS {tbl.name};"))
        conn.execute(text("PRAGMA foreign_keys = ON;"))

    # --------------------------------------------------------------
    # 4. Create tables
    # --------------------------------------------------------------
    print("Creating ERP schema...")
    metadata.create_all(engine)

    # --------------------------------------------------------------
    # 5. Populate static reference data
    # --------------------------------------------------------------
    Session = sessionmaker(bind=engine)
    session = Session()

    departments_info = [
        ("CSE", "Computer Science and Engineering"),
        ("AI_DS", "Artificial Intelligence and Data Science"),
        ("AI_ML", "Artificial Intelligence and Machine Learning"),
        ("CYBER", "Cyber Security"),
        ("IT", "Information Technology"),
        ("ECE", "Electronics and Communication Engineering"),
        ("EEE", "Electrical and Electronics Engineering"),
        ("MECH", "Mechanical Engineering"),
        ("CIVIL", "Civil Engineering"),
        ("DESIGN", "Design Engineering"),
        ("CSM", "Computer Science and Mathematics"),
        ("IOT", "Internet of Things"),
    ]

    dept_id_map = {}
    print("Inserting departments -> HODs -> faculty...")
    for code, name in departments_info:
        # Insert department (dept_head_id will be set later)
        ins = dept.insert().values(dept_code=code, dept_name=name, dept_head_id=None)
        result = session.execute(ins)
        dept_pk = result.inserted_primary_key[0]
        dept_id_map[code] = dept_pk

        # Create HOD (one per department)
        hod_name = random_name()
        hod_email = f"{hod_name.replace(' ', '.').lower()}@{code.lower()}.edu"
        hod_ins = hod.insert().values(name=hod_name, email=hod_email, dept_id=dept_pk)
        hod_res = session.execute(hod_ins)
        hod_pk = hod_res.inserted_primary_key[0]

        # Update department with HOD reference
        session.execute(
            dept.update()
            .where(dept.c.dept_id == dept_pk)
            .values(dept_head_id=hod_pk)
        )

        # Faculty members (5‑10 per department)
        for _ in range(random.randint(5, 10)):
            fac_name = random_name()
            # ensure uniqueness
            fac_email = (
                f"{fac_name.lower().replace(' ', '.')}{random.randint(100, 999)}@{code.lower()}.edu"
            )
            designation = random.choice(
                ["Assistant Professor", "Associate Professor", "Professor"]
            )
            session.execute(
                faculty.insert().values(
                    name=fac_name,
                    email=fac_email,
                    designation=designation,
                    dept_id=dept_pk,
                )
            )

    session.commit()

    # --------------------------------------------------------------
    # 6. Create courses and subjects per department
    # --------------------------------------------------------------
    print("Creating courses and subjects...")
    subject_counter = 1
    for code, name in departments_info:
        dept_pk = dept_id_map[code]
        # Each department gets 4‑6 courses (including labs & theory)
        for i in range(1, random.randint(4, 6) + 1):
            course_code = f"{code}{i:02d}"
            course_name = f"{name} Course {i}"
            course_res = session.execute(
                course.insert().values(
                    course_code=course_code,
                    course_name=course_name,
                    dept_id=dept_pk,
                )
            )
            course_pk = course_res.inserted_primary_key[0]

            # Each course gets 3‑5 subjects
            for j in range(1, random.randint(3, 5) + 1):
                subj_code = f"{course_code}{j}"
                subj_name = f"{course_name} Subject {j}"
                session.execute(
                    subject.insert().values(
                        subject_code=subj_code,
                        subject_name=subj_name,
                        course_id=course_pk,
                    )
                )
                subject_counter += 1

    session.commit()

    # --------------------------------------------------------------
    # 7. Generate student population (≈2 500 total)
    # --------------------------------------------------------------
    print("Generating student records...")
    total_students = 2500
    years = [1, 2, 3, 4]
    students_per_dept_year = total_students // (len(departments_info) * len(years))
    extra = total_students % (len(departments_info) * len(years))

    student_seq = 1
    student_pk_map = {}  # dept_year → list of student ids
    for dept_code, _ in departments_info:
        dept_pk = dept_id_map[dept_code]
        for year in years:
            count = students_per_dept_year
            if extra > 0:
                count += 1
                extra -= 1
            for _ in range(count):
                name = random_name()
                gender = random_gender()
                admission_year = 2020 + random.randint(0, 2)  # 2020‑2022
                reg_no = generate_registration_number(admission_year, student_seq)
                stu_res = session.execute(
                    student.insert().values(
                        registration_no=reg_no,
                        name=name,
                        gender=gender,
                        admission_year=admission_year,
                        dept_id=dept_pk,
                        year=year,
                    )
                )
                stu_pk = stu_res.inserted_primary_key[0]
                student_pk_map.setdefault((dept_pk, year), []).append(stu_pk)
                student_seq += 1

    session.commit()

    # --------------------------------------------------------------
    # 8. Enroll students in subjects (per semester)
    # --------------------------------------------------------------
    print("Creating enrollments & academic records...")
    semesters_per_year = 2
    # Build lookup tables for subjects per course
    subject_lookup = {}
    for row in session.execute(text("SELECT subject_id, course_id FROM subjects")):
        subject_id, course_id = row
        subject_lookup.setdefault(course_id, []).append(subject_id)

    # Courses per department
    dept_courses = {}
    for row in session.execute(
        text(
            "SELECT c.course_id, c.dept_id FROM courses c "
            "JOIN departments d ON c.dept_id = d.dept_id"
        )
    ):
        c_id, d_id = row
        dept_courses.setdefault(d_id, []).append(c_id)

    for (dept_pk, year), stu_ids in student_pk_map.items():
        for stu_id in stu_ids:
            for sem in range(1, semesters_per_year + 1):
                semester_number = (year - 1) * 2 + sem

                # Enrollments (random subjects)
                available_course_ids = dept_courses.get(dept_pk, [])
                chosen_course_ids = random.sample(
                    available_course_ids,
                    k=min(len(available_course_ids), random.randint(3, 5)),
                )
                enrolled_subjects = []
                for c_id in chosen_course_ids:
                    subs = subject_lookup.get(c_id, [])
                    if subs:
                        enrolled_subjects.append(random.choice(subs))

                for sub_id in enrolled_subjects:
                    session.execute(
                        enrollment.insert().values(
                            student_id=stu_id,
                            subject_id=sub_id,
                            semester=semester_number,
                            year=year,
                        )
                    )

                # Academic record (realistic mix)
                perf = random.choices(
                    population=["high", "average", "at_risk", "improving", "declining"],
                    weights=[0.05, 0.10, 0.60, 0.05, 0.20],
                    k=1,
                )[0]

                if perf == "high":
                    cgpa = round(random.uniform(8.5, 10.0), 2)
                    att_val = round(random.uniform(90, 100), 2)
                    backlog = 0
                elif perf == "average":
                    cgpa = round(random.uniform(6.0, 8.4), 2)
                    att_val = round(random.uniform(75, 89), 2)
                    backlog = random.choice([0, 1])
                elif perf == "at_risk":
                    cgpa = round(random.uniform(4.0, 5.9), 2)
                    att_val = round(random.uniform(50, 74), 2)
                    backlog = random.randint(2, 4)
                elif perf == "improving":
                    base_cgpa = 4.5 + (semester_number * 0.2)
                    cgpa = min(round(base_cgpa, 2), 9.0)
                    att_val = min(round(55 + (semester_number * 5), 2), 95)
                    backlog = max(0, 3 - semester_number)
                else:  # declining
                    base_cgpa = 9.0 - (semester_number * 0.3)
                    cgpa = max(round(base_cgpa, 2), 3.5)
                    att_val = max(round(95 - (semester_number * 5), 2), 45)
                    backlog = min(3, semester_number)

                session.execute(
                    academic.insert().values(
                        student_id=stu_id,
                        semester=semester_number,
                        year=year,
                        cgpa=cgpa,
                        attendance_percentage=att_val,
                        backlog_count=backlog,
                        internal_marks=round(random.uniform(60, 100), 2),
                        mid_exam_score=round(random.uniform(60, 100), 2),
                        lab_performance=round(random.uniform(60, 100), 2),
                        assignment_marks=round(random.uniform(60, 100), 2),
                    )
                )

                # Attendance logs (30‑day month)
                month_start = datetime.date(2022 + year, (sem - 1) * 6 + 1, 1)
                for day_offset in range(30):
                    cur_date = month_start + datetime.timedelta(days=day_offset)
                    present = 1 if random.random() * 100 < att_val else 0
                    session.execute(
                        attendance.insert().values(
                            student_id=stu_id, date=cur_date, present=present
                        )
                    )

    session.commit()
    print("ERP database has been rebuilt and populated successfully.")
    session.close()

if __name__ == "__main__":
    main()
