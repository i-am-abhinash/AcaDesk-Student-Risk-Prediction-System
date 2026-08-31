import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from logic.config_manager import PROJECT_ROOT

CACHE_DB_PATH = os.path.join(PROJECT_ROOT, "acadesk_cache.db")

class LocalCache:
    def __init__(self, db_path=CACHE_DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Sync Metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_sync_time DATETIME,
                    last_successful_sync DATETIME,
                    cache_version TEXT,
                    record_count INTEGER
                )
            """)

            # Departments
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS departments (
                    dept_id TEXT PRIMARY KEY,
                    dept_name TEXT
                )
            """)

            # Flat Student Academic Cache (Pre-joined for maximum UI speed)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students_cache (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    display_name TEXT,
                    branch TEXT,
                    year TEXT,
                    syear TEXT,
                    display_reg_no TEXT,
                    registration_no TEXT,
                    avg_attendance REAL,
                    avg_marks REAL,
                    backlogs INTEGER,
                    tenth REAL,
                    inter REAL,
                    diploma REAL,
                    lab_performance REAL,
                    mid_exam_score REAL,
                    consecutive_absences INTEGER,
                    leave_frequency INTEGER,
                    cgpa REAL,
                    assignment_marks REAL,
                    email TEXT,
                    parent_phone TEXT,
                    parent_email TEXT
                )
            """)

            # AI Predictions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_predictions (
                    student_id TEXT PRIMARY KEY,
                    risk_score REAL,
                    risk_category TEXT,
                    confidence REAL,
                    prediction_timestamp DATETIME,
                    academic_hash TEXT,
                    report_json TEXT
                )
            """)

            # Faculty Notes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faculty_notes (
                    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT,
                    faculty_username TEXT,
                    department TEXT,
                    note_text TEXT,
                    note_status TEXT,
                    created_at DATETIME
                )
            """)

            # Create Indexes for instant filtering
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_branch ON students_cache(branch)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_year ON students_cache(year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_branch_year ON students_cache(branch, year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_student ON faculty_notes(student_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_student ON ai_predictions(student_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_category ON ai_predictions(risk_category)")
            
            conn.commit()

    def get_metadata(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sync_metadata ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_metadata(self, last_sync, record_count):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_metadata (last_sync_time, last_successful_sync, cache_version, record_count)
                VALUES (?, ?, '2.0', ?)
            """, (last_sync, last_sync, record_count))
            conn.commit()

    def clear_cache(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students_cache")
            cursor.execute("DELETE FROM departments")
            cursor.execute("DELETE FROM faculty_notes")
            cursor.execute("DELETE FROM ai_predictions") 
            conn.commit()

    def bulk_insert(self, table_name, data_dicts):
        if not data_dicts: return
        keys = list(data_dicts[0].keys())
        columns = ", ".join(keys)
        placeholders = ", ".join(["?"] * len(keys))
        sql = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
        values = [[d.get(k) for k in keys] for d in data_dicts]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, values)
            conn.commit()

    # --- AI Predictions Cache ---
    def get_prediction(self, student_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ai_predictions WHERE student_id = ?", (str(student_id),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_predictions(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT student_id, risk_score, risk_category FROM ai_predictions")
            res = cursor.fetchall()
            return {str(r['student_id']): dict(r) for r in res} if res else {}

    def save_prediction(self, student_id, risk_score, risk_category, confidence, academic_hash=None, report_json=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO ai_predictions (student_id, risk_score, risk_category, confidence, prediction_timestamp, academic_hash, report_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (str(student_id), risk_score, risk_category, confidence, datetime.now().isoformat(), academic_hash, report_json))
            conn.commit()

# Singleton
cache = LocalCache()
