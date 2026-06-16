import mysql.connector
import random
import string

import os

DB_HOST = os.environ.get("ERP_DB_HOST", "127.0.0.1")
DB_USER = os.environ.get("ERP_DB_USER")
DB_PASSWORD = os.environ.get("ERP_DB_PASSWORD")
DB_NAME = os.environ.get("ERP_DB_NAME", "engineering_college")

if not DB_USER or not DB_PASSWORD:
    raise ValueError("Missing ERP database credentials. Please set ERP_DB_USER and ERP_DB_PASSWORD environment variables.")

# Schema definitions
DEPARTMENTS = [
    "CSE",
    "ECE",
    "MECH",
    "CIVIL",
    "EEE",
    "IT",
    "AIDS",
    "AIML"
]

YEARS = ["First Year", "Second Year", "Third Year", "Fourth Year"]

NUM_STUDENTS = 1000

def random_name():
    first = random.choice(["Amit", "Rohit", "Sneha", "Priya", "Kiran", "Anita", "Deepak", "Neha", "Vijay", "Anjali"])
    last = random.choice(["Sharma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Verma", "Iyer", "Mishra", "Das"])
    return f"{first} {last}"

def random_gender():
    return random.choice(["M", "F", "O"])

def random_email(name):
    username = "".join(name.lower().split())
    domain = random.choice(["example.com", "college.edu", "mail.com"])
    return f"{username}@{domain}"

def random_phone():
    return "".join(random.choices(string.digits, k=10))

def generate_schema(cursor):
    # Drop existing database and create a fresh one
    cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
    cursor.execute(f"CREATE DATABASE {DB_NAME}")
    cursor.execute(f"USE {DB_NAME}")

    # Create tables
    cursor.execute("""
        CREATE TABLE departments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE years (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            registration_no VARCHAR(20) UNIQUE,
            name VARCHAR(100),
            gender VARCHAR(1),
            admission_year YEAR,
            year_id INT,
            department_id INT,
            FOREIGN KEY (year_id) REFERENCES years(id),
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE faculty (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            designation VARCHAR(50),
            department_id INT,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE hod (
            id INT AUTO_INCREMENT PRIMARY KEY,
            faculty_id INT,
            department_id INT,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id),
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE academic_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            semester INT,
            cgpa FLOAT,
            internal_marks FLOAT,
            mid_exam_score FLOAT,
            lab_performance FLOAT,
            assignment_marks FLOAT,
            attendance_percentage FLOAT,
            backlog_count INT,
            tenth_percentage FLOAT,
            intermediate_percentage FLOAT,
            diploma_percentage FLOAT,
            consecutive_absences INT,
            leave_frequency INT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            attendance_date DATE,
            status ENUM('P','A') NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE parent_contacts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            parent_name VARCHAR(100),
            email VARCHAR(100),
            phone VARCHAR(15),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE semester_enrollment (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            semester INT,
            year_id INT,
            department_id INT,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (year_id) REFERENCES years(id),
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    """)

def populate_static_data(cursor):
    # Insert departments
    dept_ids = {}
    for dept in DEPARTMENTS:
        cursor.execute("INSERT INTO departments (name) VALUES (%s)", (dept,))
        dept_ids[dept] = cursor.lastrowid
    # Insert years
    year_ids = {}
    for yr in YEARS:
        cursor.execute("INSERT INTO years (name) VALUES (%s)", (yr,))
        year_ids[yr] = cursor.lastrowid
    return dept_ids, year_ids

def generate_students(cursor, dept_ids, year_ids):
    student_ids = []
    total_depts = len(DEPARTMENTS)
    per_dept = NUM_STUDENTS // total_depts
    remainder = NUM_STUDENTS % total_depts
    student_counter = 1
    for idx, dept_name in enumerate(DEPARTMENTS):
        count = per_dept + (1 if idx < remainder else 0)
        for _ in range(count):
            name = random_name()
            gender = random_gender()
            reg_no = f"REG{student_counter:05d}"
            admission_year = random.choice([2019, 2020, 2021, 2022])
            year_name = random.choice(YEARS)
            cursor.execute(
                """
                INSERT INTO students (registration_no, name, gender, admission_year, year_id, department_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (reg_no, name, gender, admission_year, year_ids[year_name], dept_ids[dept_name])
            )
            student_ids.append(cursor.lastrowid)
            student_counter += 1
    return student_ids

def generate_faculty(cursor, dept_ids):
    faculty_ids = {}
    for dept, d_id in dept_ids.items():
        num_fac = random.randint(3, 5)
        for _ in range(num_fac):
            name = random_name()
            designation = random.choice(["Professor", "Associate Professor", "Assistant Professor", "Lecturer"])
            cursor.execute(
                "INSERT INTO faculty (name, designation, department_id) VALUES (%s, %s, %s)",
                (name, designation, d_id)
            )
            fid = cursor.lastrowid
            faculty_ids.setdefault(dept, []).append(fid)
    # Assign HOD (first faculty of each department)
    for dept, fids in faculty_ids.items():
        hod_fid = fids[0]
        cursor.execute(
            "INSERT INTO hod (faculty_id, department_id) VALUES (%s, %s)",
            (hod_fid, dept_ids[dept])
        )
    return faculty_ids

def generate_academic_records(cursor, student_ids):
    for sid in student_ids:
        # Pre-generate historical data per student so it stays consistent across semesters
        tenth = round(random.uniform(50.0, 98.0), 2)
        has_diploma = random.choice([True, False])
        inter = 0.0 if has_diploma else round(random.uniform(50.0, 98.0), 2)
        diploma = round(random.uniform(50.0, 95.0), 2) if has_diploma else 0.0
        
        cursor.execute("SELECT y.name FROM students s JOIN years y ON s.year_id = y.id WHERE s.id = %s", (sid,))
        year_name = cursor.fetchone()[0].lower()
        
        if '1' in year_name or 'first' in year_name: num_sem = random.randint(1, 2)
        elif '2' in year_name or 'second' in year_name: num_sem = random.randint(3, 4)
        elif '3' in year_name or 'third' in year_name: num_sem = random.randint(5, 6)
        else: num_sem = random.randint(7, 8)
        
        for sem in range(1, num_sem + 1):
            cgpa = random.choices([
                round(random.uniform(7.5, 10.0), 2),
                round(random.uniform(6.0, 7.5), 2),
                round(random.uniform(4.0, 6.0), 2)
            ], weights=[70, 20, 10])[0]
            
            internal = round(random.uniform(50, 100), 2)
            mid = round(random.uniform(50, 100), 2)
            lab = round(random.uniform(50, 100), 2)
            assign = round(random.uniform(50, 100), 2)
            
            attendance = random.choices([
                round(random.uniform(80, 100), 2),
                round(random.uniform(65, 80), 2),
                round(random.uniform(40, 65), 2)
            ], weights=[70, 20, 10])[0]
            
            backlogs = random.choices([0, 1, 2, 3], weights=[70, 15, 10, 5])[0]
            cons_abs = random.choices([0, 1, 2, 3, 4, 5], weights=[60, 20, 10, 5, 3, 2])[0]
            leave_freq = random.choices([0, 1, 2, 3, 4, 5], weights=[50, 20, 15, 10, 3, 2])[0]
            cursor.execute(
                """
                INSERT INTO academic_records (student_id, semester, cgpa, internal_marks, mid_exam_score, lab_performance, assignment_marks, attendance_percentage, backlog_count, tenth_percentage, intermediate_percentage, diploma_percentage, consecutive_absences, leave_frequency)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (sid, sem, cgpa, internal, mid, lab, assign, attendance, backlogs, tenth, inter, diploma, cons_abs, leave_freq)
            )

def generate_attendance(cursor, student_ids):
    import calendar
    from datetime import date
    
    attendance_records = []
    for sid in student_ids:
        # retrieve semesters for the student
        cursor.execute("SELECT semester FROM academic_records WHERE student_id = %s", (sid,))
        semesters = [row[0] for row in cursor.fetchall()]
        for sem in semesters:
            # Determine month number (use semester as month, wrap around if >12)
            month = sem if sem <= 12 else ((sem - 1) % 12) + 1
            year = 2023
            _, month_days = calendar.monthrange(year, month)
            days_to_generate = min(30, month_days)
            for day_offset in range(days_to_generate):
                attendance_date = date(year, month, day_offset + 1)
                status = random.choice(['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P', 'A']) # Weight towards present
                attendance_records.append((sid, attendance_date, status))
                
        # Batch insert every 10000 records to save memory but still be very fast
        if len(attendance_records) >= 10000:
            cursor.executemany(
                "INSERT INTO attendance (student_id, attendance_date, status) VALUES (%s, %s, %s)",
                attendance_records
            )
            attendance_records.clear()
            
    # Insert any remaining records
    if attendance_records:
        cursor.executemany(
            "INSERT INTO attendance (student_id, attendance_date, status) VALUES (%s, %s, %s)",
            attendance_records
        )

def generate_parent_contacts(cursor, student_ids):
    for sid in student_ids:
        parent_name = random_name()
        email = random_email(parent_name)
        phone = random_phone()
        cursor.execute(
            "INSERT INTO parent_contacts (student_id, parent_name, email, phone) VALUES (%s, %s, %s, %s)",
            (sid, parent_name, email, phone)
        )

def main():
    print(f"Connecting to MySQL at {DB_HOST}...")
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    cursor = conn.cursor()
    generate_schema(cursor)
    dept_ids, year_ids = populate_static_data(cursor)
    student_ids = generate_students(cursor, dept_ids, year_ids)
    generate_faculty(cursor, dept_ids)
    generate_academic_records(cursor, student_ids)
    generate_attendance(cursor, student_ids)
    generate_parent_contacts(cursor, student_ids)
    conn.commit()
    cursor.close()
    conn.close()
    print("Database reconstruction complete. Created", NUM_STUDENTS, "students.")

if __name__ == "__main__":
    main()
