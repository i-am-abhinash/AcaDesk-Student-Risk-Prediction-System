"""
AcaDesk DBHandler — Backward-Compatible Facade
================================================
This is now a thin facade over the new 4-layer architecture.

All data reads are served from the Session Cache (Layer 4).
The legacy ERP connection is used ONLY for:
  - validate_tables() during login to verify connectivity
  - get_branch_map() if cache is empty

All write operations (monthly snapshots) are preserved for
backward compatibility but now operate on local/central dbs.

IMPORTANT: No debug_filter.txt writes. All logging via the
standard logging module.
"""

import sys
import os
import logging

_log = logging.getLogger(__name__)


class DBHandler:
    """
    Backward-compatible facade.
    All UI and analytics code continues to call this API unchanged.
    Internally, reads are served from SessionCache (Layer 4).
    """

    def __init__(self, config_dict=None):
        self.config = config_dict or {}
        self.connected = False
        self.conn = None
        self.cursor = None
        self.cache_mode = True

        if not self.config:
            return

        from logic.sql_utils import sanitize_identifier

        def s(val):
            return sanitize_identifier(val) if val else val

        self.map = {
            "tbl_student":   s(self.config.get("tbl_student", "student")),
            "tbl_academic":  s(self.config.get("tbl_academic", "academics")),
            "tbl_history":   s(self.config.get("tbl_history", "academic_history")),
            "tbl_branch":    s(self.config.get("tbl_branch", "branch")),
            "join_student":  s(self.config.get("col_student_join", "student_id")),
            "join_branch":   s(self.config.get("col_branch_join", "branch_id")),
            "col_semester":  s(self.config.get("col_semester", "semester")),
            "id":            s(self.config.get("col_id", "roll_no")),
            "name":          s(self.config.get("col_name", "name")),
            "branch_name":   s(self.config.get("col_branch_name", "branch_name")),
            "year":          s(self.config.get("col_year", "year")),
            "att":           s(self.config.get("col_att", "attendance")),
            "marks":         s(self.config.get("col_marks", "internal_marks")),
            "cgpa":          s(self.config.get("col_cgpa", "cgpa")),
            "backlogs":      s(self.config.get("col_backlogs", "backlogs")),
            "tenth":         s(self.config.get("col_tenth", "tenth_percentage")),
            "inter":         s(self.config.get("col_inter", "intermediate_percentage")),
            "diploma":       s(self.config.get("col_diploma", "diploma_percentage")),
            "lab_perf":      s(self.config.get("col_lab_perf", "lab_performance")),
            "mid_exam":      s(self.config.get("col_mid_exam", "mid_exam_score")),
            "cons_abs":      s(self.config.get("col_cons_abs", "consecutive_absences")),
            "leave_freq":    s(self.config.get("col_leave_freq", "leave_frequency")),
            "assign_marks":  s(self.config.get("col_assign_marks", "assignment_marks")),
            "parent_phone":  s(self.config.get("col_parent_phone", "parent_phone")),
            "parent_email":  s(self.config.get("col_p_email")),
            "email":         s(self.config.get("col_email")),
        }
        self._connect_erp()

    def _connect_erp(self):
        """Connects to the ERP (used only for validate_tables)."""
        host = self.config.get("host", "localhost")
        user = self.config.get("user", "root")
        password = self.config.get("password", "")
        database = self.config.get("database", "")
        port = int(self.config.get("port", 3306))
        try:
            import mysql.connector
            self.conn = mysql.connector.connect(
                host=host, user=user, password=password,
                database=database, port=port, connect_timeout=10
            )
            self.cursor = self.conn.cursor(dictionary=True)
            self.connected = True
        except Exception as e:
            _log.error(f"ERP connection error: {e}")
            self.connected = False

    def close(self):
        try:
            if self.cursor:
                self.cursor.close()
        except Exception:
            pass
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.connected = False

    def validate_tables(self):
        """Validates that the configured tables exist in the ERP."""
        if not self.conn or not self.connected:
            return False, "Not connected to ERP database."
        try:
            self.cursor.execute("SHOW TABLES")
            tables = [r[list(r.keys())[0]].lower() for r in self.cursor.fetchall()]
            missing = []
            s_tbl = self.map.get("tbl_student", "").strip("`").lower()
            a_tbl = self.map.get("tbl_academic", "").strip("`").lower()
            b_tbl = self.map.get("tbl_branch", "").strip("`").lower()
            if s_tbl and s_tbl not in tables:
                missing.append(s_tbl)
            if a_tbl and a_tbl not in tables:
                missing.append(a_tbl)
            if b_tbl and b_tbl not in tables:
                missing.append(b_tbl)
            if missing:
                return False, f"Missing tables: {', '.join(missing)}"
            return True, "Valid"
        except Exception as e:
            return False, f"Error validating tables: {e}"

    # ------------------------------------------------------------------
    # READ OPERATIONS — All served from Session Cache (Layer 4)
    # ------------------------------------------------------------------

    def get_branch_map(self):
        """Returns {branch_id: branch_name} from session cache."""
        try:
            from logic.session_cache import get_session_cache
            session = get_session_cache()
            depts = session.get_departments()
            if depts:
                return depts
        except Exception as e:
            _log.debug(f"Session cache branch map read failed: {e}")

        # Fallback: legacy local_cache
        try:
            from logic.local_cache import cache
            with cache.get_connection() as c_conn:
                c_cursor = c_conn.cursor()
                c_cursor.execute("SELECT dept_id, dept_name FROM departments")
                res = c_cursor.fetchall()
                if res:
                    return {str(r["dept_id"]): str(r["dept_name"]) for r in res}
        except Exception as e:
            _log.debug(f"Legacy local_cache branch map failed: {e}")

        return {}

    def get_all_branches(self):
        return list(self.get_branch_map().keys())

    def get_students(self, branch_id, year):
        """
        Returns students for a branch/year from session cache.
        Normalizes year to an integer 1-4 before querying.
        """
        y_str = str(year).lower()
        if "1" in y_str or "first" in y_str:
            numeric_year = 1
        elif "2" in y_str or "second" in y_str:
            numeric_year = 2
        elif "3" in y_str or "third" in y_str:
            numeric_year = 3
        elif "4" in y_str or "fourth" in y_str:
            numeric_year = 4
        else:
            try:
                numeric_year = max(1, min(4, int(float(y_str))))
            except (ValueError, TypeError):
                numeric_year = 1

        try:
            from logic.session_cache import get_session_cache
            session = get_session_cache()
            rows = session.get_students(str(branch_id), numeric_year)
            if rows:
                return [self._normalize_row(r) for r in rows]
        except Exception as e:
            _log.error(f"Session cache get_students failed: {e}")

        return []

    def get_all_students(self):
        """Returns all students from session cache."""
        try:
            from logic.session_cache import get_session_cache
            session = get_session_cache()
            rows = session.get_all_students()
            if rows:
                return [self._normalize_row(r) for r in rows]
        except Exception as e:
            _log.error(f"Session cache get_all_students failed: {e}")
        return []

    def get_student_history(self, student_id):
        """
        Returns semester history from session cache as a list of dicts
        with 'semester', 'cgpa', 'attendance', 'backlogs' keys.
        """
        try:
            from logic.session_cache import get_session_cache
            session = get_session_cache()
            records = session.get_semester_history(str(student_id))
            return [
                {
                    "semester": r["semester_number"],
                    "cgpa": r["cgpa_that_semester"],
                    "attendance": r["attendance_that_semester"],
                    "backlogs": r["backlogs_that_semester"],
                }
                for r in records
            ]
        except Exception as e:
            _log.debug(f"get_student_history failed: {e}")
        return []

    def get_training_data(self):
        """Returns all students as training data (from session cache)."""
        return self.get_all_students()

    def _normalize_row(self, r: dict) -> dict:
        """
        Converts a session cache row to the legacy dict format expected
        by all existing UI components and analytics modules.
        Preserves all existing field names.
        """
        student_id = r.get("student_id") or r.get("id") or r.get("sid", "")
        full_name = r.get("full_name") or r.get("name") or r.get("display_name", "Unknown")
        branch_id = r.get("branch_id") or r.get("branch") or r.get("bid", "")
        year_val = r.get("current_year") or r.get("syear") or r.get("year", 1)

        return {
            # Primary identity fields (all legacy aliases populated)
            "id": student_id,
            "sid": student_id,
            "student_id": student_id,
            "display_reg_no": r.get("display_reg_no") or student_id,
            "registration_no": r.get("registration_no") or student_id,
            "name": full_name,
            "sname": full_name,
            "full_name": full_name,
            "display_name": r.get("display_name") or full_name,
            "branch": str(branch_id),
            "branch_id": str(branch_id),
            "bid": str(branch_id),
            "branch_name": r.get("branch_name", ""),
            "year": str(year_val),
            "syear": str(year_val),
            "current_year": int(year_val) if str(year_val).isdigit() else 1,
            "current_semester": r.get("current_semester", 1),
            # Academic indicators — use canonical names AND legacy aliases
            "avg_attendance": float(r.get("attendance_pct") or r.get("avg_attendance") or 0.0),
            "attendance_pct": float(r.get("attendance_pct") or r.get("avg_attendance") or 0.0),
            "att": float(r.get("attendance_pct") or 0.0),
            "avg_marks": float(r.get("internal_marks") or r.get("avg_marks") or 0.0),
            "internal_marks": float(r.get("internal_marks") or r.get("avg_marks") or 0.0),
            "marks": float(r.get("internal_marks") or 0.0),
            "backlogs": int(r.get("backlog_count") or r.get("backlogs") or 0),
            "backlog_count": int(r.get("backlog_count") or r.get("backlogs") or 0),
            "cgpa": float(r.get("cgpa") or 0.0),
            "mid_exam_score": float(r.get("mid_exam_score") or 0.0),
            "assignment_marks": float(r.get("assignment_marks") or 0.0),
            "lab_performance": float(r.get("lab_performance") or 0.0),
            "consecutive_absences": int(r.get("consecutive_absences") or 0),
            "leave_frequency": int(r.get("leave_frequency") or 0),
            # Prior background
            "tenth": float(r.get("tenth_percentage") or r.get("tenth") or 0.0),
            "tenth_percentage": float(r.get("tenth_percentage") or r.get("tenth") or 0.0),
            "inter": float(r.get("inter_percentage") or r.get("inter") or 0.0),
            "inter_percentage": float(r.get("inter_percentage") or r.get("inter") or 0.0),
            "diploma": float(r.get("diploma_percentage") or r.get("diploma") or 0.0),
            "diploma_percentage": float(r.get("diploma_percentage") or r.get("diploma") or 0.0),
            # Contact
            "email": r.get("email"),
            "parent_email": r.get("parent_email"),
            "parent_phone": r.get("parent_phone"),
            # AI prediction (pre-joined from session cache)
            "risk_score": r.get("risk_score"),
            "risk_category": r.get("risk_category"),
            "confidence": r.get("confidence"),
            "report_json": r.get("report_json"),
        }

    # ------------------------------------------------------------------
    # Write Operations (preserved for backward compatibility)
    # ------------------------------------------------------------------

    def get_interventions(self, student_id):
        return []

    def save_intervention(self, student_id, text, priority, status, reason):
        return None

    def update_intervention_status(self, intervention_id, status):
        return False

    def save_monthly_snapshot(self, branch_id, month_str, health_score,
                               att_avg, cgpa_avg, risk_dist):
        """Preserved for backward compatibility with analytics modules."""
        try:
            from logic.local_cache import cache
            with cache.get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS monthly_trends (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        branch_id TEXT,
                        snapshot_month TEXT,
                        health_score REAL,
                        att_avg REAL,
                        cgpa_avg REAL,
                        high_risk INTEGER,
                        med_risk INTEGER,
                        low_risk INTEGER,
                        UNIQUE (branch_id, snapshot_month)
                    )
                """)
                conn.execute("""
                    INSERT OR REPLACE INTO monthly_trends
                        (branch_id, snapshot_month, health_score, att_avg, cgpa_avg,
                         high_risk, med_risk, low_risk)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    branch_id, month_str, health_score, att_avg, cgpa_avg,
                    risk_dist.get("High", 0), risk_dist.get("Medium", 0),
                    risk_dist.get("Low", 0)
                ))
                conn.commit()
            return True
        except Exception as e:
            _log.error(f"save_monthly_snapshot error: {e}")
            return False

    def get_monthly_trends(self, branch_id=None):
        try:
            from logic.local_cache import cache
            with cache.get_connection() as conn:
                if branch_id:
                    cursor = conn.execute(
                        "SELECT * FROM monthly_trends WHERE branch_id=? ORDER BY snapshot_month ASC",
                        (branch_id,)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM monthly_trends ORDER BY snapshot_month ASC"
                    )
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            _log.debug(f"get_monthly_trends error: {e}")
            return []

    # ------------------------------------------------------------------
    # Faculty Notes — delegate to CentralAuth
    # ------------------------------------------------------------------

    def create_note(self, student_id, faculty_username, department, note_text):
        try:
            from logic.central_auth import CentralAuth
            return CentralAuth().add_faculty_note(
                student_id, faculty_username, department, note_text
            )
        except Exception as e:
            _log.error(f"create_note error: {e}")
            return False, str(e)

    def update_note(self, note_id, note_text):
        try:
            from logic.central_auth import CentralAuth
            return CentralAuth().update_faculty_note(note_id, note_text)
        except Exception as e:
            _log.error(f"update_note error: {e}")
            return False, str(e)

    def delete_note(self, note_id):
        try:
            from logic.central_auth import CentralAuth
            return CentralAuth().delete_faculty_note(note_id)
        except Exception as e:
            _log.error(f"delete_note error: {e}")
            return False, str(e)

    def get_student_notes(self, student_id):
        try:
            from logic.central_auth import CentralAuth
            return CentralAuth().get_faculty_notes(student_id=student_id)
        except Exception as e:
            _log.debug(f"get_student_notes error: {e}")
            return []

    def get_all_notes_filtered(self, department=None):
        try:
            from logic.central_auth import CentralAuth
            return CentralAuth().get_faculty_notes(department=department)
        except Exception as e:
            _log.debug(f"get_all_notes_filtered error: {e}")
            return []
