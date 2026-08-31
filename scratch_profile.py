import os
import sys
import time

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.db_handler import DBHandler
from logic.session_cache import get_session_cache
from logic.data_contract import NormalizedStudent

# Setup minimal config
config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "college",
    "tbl_student": "students",
    "tbl_academic": "academics",
    "tbl_branch": "branches"
}

def run_profile():
    print("--- PERFORMANCE PROFILING: STUDENT LIST LOADING ---")
    
    # 1. Initialize Cache
    t0 = time.time()
    session = get_session_cache()
    t1 = time.time()
    print(f"[Timing] Session Cache Init: {(t1-t0)*1000:.2f} ms")
    
    dummy_students = []
    for i in range(1000):
        dummy_students.append(NormalizedStudent(
            student_id=str(i),
            full_name=f"Student {i}",
            branch_id="CS01",
            branch_name="Computer Science",
            current_year=2,
            current_semester=3,
            attendance_pct=85.0,
            internal_marks=75.0,
            backlog_count=0
        ))
    
    t2 = time.time()
    session.bulk_insert_students(dummy_students)
    t3 = time.time()
    print(f"[Timing] Inserted 1000 Dummy Students: {(t3-t2)*1000:.2f} ms")
    
    t4 = time.time()
    db = DBHandler(config)
    t5 = time.time()
    print(f"[Timing] DBHandler Init: {(t5-t4)*1000:.2f} ms")
    
    print("\n--- SIMULATING USER SELECTION ---")
    t6 = time.time()
    students = db.get_students("CS01", 2)
    t7 = time.time()
    print(f"[Timing] db.get_students (Cache Read + Normalize): {(t7-t6)*1000:.2f} ms")
    print(f"Returned {len(students)} records.")
    
    t8 = time.time()
    query = ""
    
    filtered_students = []
    for s in students:
        is_match = query in str(s['id']).lower() or query in str(s['name']).lower()
        if is_match:
            filtered_students.append(s)

    processed_students = []
    import json
    for s in filtered_students:
        score = s.get('risk_score', 0.0) or 0.0
        level = s.get('risk_category', 'Low') or 'Low'
        report = {
            'score': score,
            'level': level,
            'risk_score': score,
            'risk_category': level,
            'confidence': s.get('confidence', 90)
        }
        report_json = s.get('report_json')
        if report_json:
            parsed = json.loads(report_json)
            report.update(parsed)
        processed_students.append((s, report))
        
    t9 = time.time()
    print(f"[Timing] Dashboard Data Filtering & Processing: {(t9-t8)*1000:.2f} ms")
    
    print("\n--- SUMMARY ---")
    total_load = (t7-t6) + (t9-t8)
    print(f"Total time from selection to ready for render: {total_load*1000:.2f} ms")

if __name__ == "__main__":
    run_profile()
