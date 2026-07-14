"""
AcaDesk Session Cache — Layer 4
=================================
An ephemeral SQLite database that lives only for the duration of a single
application session.

GUARANTEES:
  1. Created fresh at session start in a unique temp directory.
  2. Never shares data across sessions.
  3. Completely destroyed on application close via atexit AND WM_DELETE_WINDOW.
  4. Stores ONLY NormalizedStudent records (AcaDesk's Internal Data Contract).
     It does NOT mirror ERP schema columns.
  5. The college ERP database remains the single source of truth.
"""

from __future__ import annotations
import atexit
import logging
import os
import shutil
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from typing import Generator, List, Optional

from logic.data_contract import NormalizedStudent, SemesterRecord

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton session cache instance
# ---------------------------------------------------------------------------

_SESSION_CACHE: Optional["SessionCache"] = None
_LOCK = threading.Lock()


def get_session_cache() -> "SessionCache":
    """Returns the application-wide singleton session cache, creating it if needed."""
    global _SESSION_CACHE
    if _SESSION_CACHE is None:
        with _LOCK:
            if _SESSION_CACHE is None:
                _SESSION_CACHE = SessionCache()
    return _SESSION_CACHE


def destroy_session_cache() -> None:
    """Destroy the session cache. Called by atexit and WM_DELETE_WINDOW."""
    global _SESSION_CACHE
    if _SESSION_CACHE is not None:
        _log.info("Destroying session cache on application exit.")
        try:
            _SESSION_CACHE.destroy()
        except Exception as e:
            _log.warning(f"Error during session cache destruction: {e}")
        _SESSION_CACHE = None


def get_dashboard_summary() -> list:
    """Returns pre-aggregated branch risk data from the session cache for all dashboard panels."""
    cache = get_session_cache()
    if not cache._initialized:
        return []
    with cache.get_connection() as conn:
        cursor = conn.execute("""
            SELECT 
                s.branch_id,
                s.branch_name,
                r.risk_category as risk_level,
                COUNT(*) as count,
                AVG(s.attendance_pct) as avg_att,
                AVG(s.cgpa) as avg_cgpa,
                AVG(s.backlog_count) as avg_bkl
            FROM ai_predictions r
            JOIN students s ON r.student_id = s.student_id
            GROUP BY s.branch_id, s.branch_name, r.risk_category
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_all_students_for_prediction() -> list:
    """Returns all students from session cache as dictionaries for model evaluation."""
    cache = get_session_cache()
    if not cache._initialized:
        return []
    with cache.get_connection() as conn:
        cursor = conn.execute("SELECT * FROM students")
        return [dict(row) for row in cursor.fetchall()]

# Register cleanup with atexit as the primary safety net
atexit.register(destroy_session_cache)

destroy = destroy_session_cache

class SessionCache:
    """
    Ephemeral SQLite session cache.

    Schema uses the NormalizedStudent Internal Data Contract — not ERP columns.
    """

    def __init__(self):
        self._temp_dir = tempfile.mkdtemp(prefix="acadesk_session_")
        self._db_path = os.path.join(self._temp_dir, "session.db")
        self._local = threading.local()
        self._lock = threading.Lock()
        self._initialized = False
        _log.info(f"Session cache created at: {self._db_path}")
        self._init_schema()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Thread-safe connection context manager with guaranteed closure."""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Schema Initialization
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS departments (
                    dept_id   TEXT PRIMARY KEY,
                    dept_name TEXT
                );

                CREATE TABLE IF NOT EXISTS students (
                    student_id               TEXT PRIMARY KEY,
                    full_name                TEXT,
                    display_name             TEXT,
                    display_reg_no           TEXT,
                    registration_no          TEXT,
                    branch_id                TEXT,
                    branch_name              TEXT,
                    current_year             INTEGER DEFAULT 1,
                    current_semester         INTEGER DEFAULT 1,
                    total_semesters_completed INTEGER DEFAULT 0,
                    admission_type           TEXT,
                    entrance_rank            INTEGER,
                    attendance_pct           REAL DEFAULT 0.0,
                    internal_marks           REAL DEFAULT 0.0,
                    mid_exam_score           REAL DEFAULT 0.0,
                    assignment_marks         REAL DEFAULT 0.0,
                    lab_performance          REAL DEFAULT 0.0,
                    cgpa                     REAL DEFAULT 0.0,
                    backlog_count            INTEGER DEFAULT 0,
                    consecutive_absences     INTEGER DEFAULT 0,
                    leave_frequency          INTEGER DEFAULT 0,
                    tenth_percentage         REAL,
                    inter_percentage         REAL,
                    diploma_percentage       REAL,
                    email                    TEXT,
                    parent_email             TEXT,
                    parent_phone             TEXT
                );

                CREATE TABLE IF NOT EXISTS semester_history (
                    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id             TEXT,
                    semester_number        INTEGER,
                    cgpa_that_semester     REAL DEFAULT 0.0,
                    attendance_that_semester REAL DEFAULT 0.0,
                    backlogs_that_semester INTEGER DEFAULT 0,
                    FOREIGN KEY (student_id) REFERENCES students(student_id)
                );

                CREATE TABLE IF NOT EXISTS ai_predictions (
                    student_id           TEXT PRIMARY KEY,
                    risk_score           REAL,
                    risk_category        TEXT,
                    confidence           REAL,
                    prediction_timestamp TEXT,
                    report_json          TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_student_branch
                    ON students(branch_id);
                CREATE INDEX IF NOT EXISTS idx_student_year
                    ON students(current_year);
                CREATE INDEX IF NOT EXISTS idx_student_branch_year
                    ON students(branch_id, current_year);
                CREATE INDEX IF NOT EXISTS idx_history_student
                    ON semester_history(student_id);
                CREATE INDEX IF NOT EXISTS idx_ai_student
                    ON ai_predictions(student_id);
                CREATE INDEX IF NOT EXISTS idx_ai_category
                    ON ai_predictions(risk_category);
            """)
            conn.commit()
        self._initialized = True
        _log.debug("Session cache schema initialized.")

    # ------------------------------------------------------------------
    # Write Operations
    # ------------------------------------------------------------------

    def bulk_insert_students(self, students: List[NormalizedStudent]) -> None:
        """Inserts or replaces a batch of NormalizedStudent records."""
        if not students:
            return
        rows = [s.to_dict() for s in students]
        keys = [
            "student_id", "full_name", "display_name", "display_reg_no",
            "registration_no", "branch_id", "branch_name", "current_year",
            "current_semester", "total_semesters_completed", "admission_type",
            "entrance_rank", "attendance_pct", "internal_marks", "mid_exam_score",
            "assignment_marks", "lab_performance", "cgpa", "backlog_count",
            "consecutive_absences", "leave_frequency", "tenth_percentage",
            "inter_percentage", "diploma_percentage", "email", "parent_email",
            "parent_phone",
        ]
        cols = ", ".join(keys)
        placeholders = ", ".join(["?"] * len(keys))
        sql = f"INSERT OR REPLACE INTO students ({cols}) VALUES ({placeholders})"
        values = [[r.get(k) for k in keys] for r in rows]
        with self.get_connection() as conn:
            conn.executemany(sql, values)
            conn.commit()
        _log.debug(f"Inserted {len(students)} students into session cache.")

    def bulk_insert_students_page(self, students: List[NormalizedStudent]) -> None:
        """Alias for bulk_insert_students to support pagination."""
        self.bulk_insert_students(students)

    def bulk_insert_semester_history(self, records: List[SemesterRecord]) -> None:
        """Inserts semester history records."""
        if not records:
            return
        sql = """
            INSERT OR REPLACE INTO semester_history
                (student_id, semester_number, cgpa_that_semester,
                 attendance_that_semester, backlogs_that_semester)
            VALUES (?, ?, ?, ?, ?)
        """
        values = [
            (r.student_id, r.semester_number, r.cgpa_that_semester,
             r.attendance_that_semester, r.backlogs_that_semester)
            for r in records
        ]
        with self.get_connection() as conn:
            conn.executemany(sql, values)
            conn.commit()

    def bulk_insert_departments(self, dept_data: list) -> None:
        """dept_data: list of {'dept_id': ..., 'dept_name': ...}"""
        if not dept_data:
            return
        sql = "INSERT OR REPLACE INTO departments (dept_id, dept_name) VALUES (?, ?)"
        values = [(str(d["dept_id"]), str(d["dept_name"])) for d in dept_data]
        with self.get_connection() as conn:
            conn.executemany(sql, values)
            conn.commit()

    def save_prediction(self, student_id: str, risk_score: float,
                        risk_category: str, confidence: float,
                        report_json: str) -> None:
        import datetime
        sql = """
            INSERT OR REPLACE INTO ai_predictions
                (student_id, risk_score, risk_category, confidence,
                 prediction_timestamp, report_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            conn.execute(sql, (
                str(student_id), risk_score, risk_category, confidence,
                datetime.datetime.now().isoformat(), report_json
            ))
            conn.commit()

    def bulk_insert_predictions(self, predictions: list) -> None:
        """predictions: list of dicts with student_id, risk_score, risk_category, confidence, report_json"""
        if not predictions:
            return
        import datetime
        now = datetime.datetime.now().isoformat()
        sql = """
            INSERT OR REPLACE INTO ai_predictions
                (student_id, risk_score, risk_category, confidence,
                 prediction_timestamp, report_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        values = [
            (str(p["student_id"]), p.get("risk_score", 0.0),
             p.get("risk_category", "Low"), p.get("confidence", 90.0),
             now, p.get("report_json", "{}"))
            for p in predictions
        ]
        with self.get_connection() as conn:
            conn.executemany(sql, values)
            conn.commit()

    # ------------------------------------------------------------------
    # Read Operations
    # ------------------------------------------------------------------

    def get_departments(self) -> dict:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT dept_id, dept_name FROM departments")
            rows = cursor.fetchall()
            return {str(r["dept_id"]): str(r["dept_name"]) for r in rows}

    def get_students(self, branch_id: str, year) -> List[dict]:
        """
        Returns students for a given branch and year as dicts (compatible with
        legacy code). Joins with ai_predictions for precomputed scores.
        The year parameter accepts either an int (1-4) or a display string like '3rd Year'.
        """
        # Convert year display string to integer if needed
        year_int = year
        if isinstance(year, str):
            from logic.data_retrieval import _parse_year
            year_int = _parse_year(year)
        elif year is None:
            year_int = 1
        else:
            try:
                year_int = int(year)
            except (ValueError, TypeError):
                year_int = 1
        sql = """
            SELECT s.*, a.risk_score, a.risk_category, a.confidence, a.report_json
            FROM students s
            LEFT JOIN ai_predictions a ON s.student_id = a.student_id
            WHERE s.branch_id = ? AND s.current_year = ?
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (str(branch_id), year_int))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_all_students(self) -> List[dict]:
        """Returns all students with AI predictions joined."""
        sql = """
            SELECT s.*, a.risk_score, a.risk_category, a.confidence, a.report_json
            FROM students s
            LEFT JOIN ai_predictions a ON s.student_id = a.student_id
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_semester_history(self, student_id: str) -> List[dict]:
        """Returns semester history records for a student, ordered by semester."""
        sql = """
            SELECT semester_number, cgpa_that_semester,
                   attendance_that_semester, backlogs_that_semester
            FROM semester_history
            WHERE student_id = ?
            ORDER BY semester_number ASC
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (str(student_id),))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_all_predictions(self) -> dict:
        """Returns {student_id: {risk_score, risk_category}} for all students."""
        sql = "SELECT student_id, risk_score, risk_category FROM ai_predictions"
        with self.get_connection() as conn:
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
            return {str(r["student_id"]): dict(r) for r in rows}

    def is_populated(self) -> bool:
        """Returns True if students table has at least one record."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM students")
            row = cursor.fetchone()
            return row["cnt"] > 0

    def clear(self) -> None:
        """Clears all student data (for re-sync)."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM students")
            conn.execute("DELETE FROM semester_history")
            conn.execute("DELETE FROM ai_predictions")
            conn.execute("DELETE FROM departments")
            conn.commit()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def destroy(self) -> None:
        """
        Closes all connections and deletes the temp directory.
        Called on application exit — guaranteed via atexit and WM_DELETE_WINDOW.
        """
        try:
            if os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir, ignore_errors=True)
                _log.info(f"Session cache temp directory destroyed: {self._temp_dir}")
        except Exception as e:
            _log.warning(f"Could not delete session cache temp dir: {e}")
