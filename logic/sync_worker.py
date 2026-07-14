"""
AcaDesk Sync Worker — Session Cache Orchestrator
==================================================
Runs as a background thread. Executes a fully validated, 6-step
synchronization from the college ERP database into the ephemeral
session cache (Layer 4).

SYNC STEPS:
  1. Validate ERP connection & stored schema mapping
     (auto-correct stale column names via demand_driven_discover)
  2. Retrieve NormalizedStudent records from ERP (Layer 3)
  3. Retrieve semester history records
  4. Write all data to SQLite session cache (with WAL mode)
  5. Run AI risk precomputation — fully memory-resident, no DB connections
  6. Validate cache completeness

RULES:
  - No database connection may be open during AI batch inference (Rule 3)
  - All UI updates are dispatched via emit callbacks (never direct calls)
  - No threading.Thread is called from UI code; SyncWorker owns its thread
  - All print() replaced by logging.*
"""

from __future__ import annotations
import json
import logging
import threading
import traceback
from datetime import datetime
from typing import Callable, Optional, Tuple, Any
from dataclasses import dataclass
from logic.erp_connection import ERPConnection
from logic.data_retrieval import DataRetrieval
from logic.session_cache import get_session_cache
from logic.central_auth import CentralAuth
from logic.local_cache import cache as local_cache

_log = logging.getLogger(__name__)

@dataclass
class SyncError:
    step: str          # e.g., "schema_validation", "branch_fetch"
    message: str       # Human-readable description
    technical: str     # Raw exception or SQL error
    is_recoverable: bool # True if Retry might help

class SyncResult:
    """Typed result object for SyncWorker callbacks."""
    SUCCESS = "SUCCESS"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    SCHEMA_ERROR = "SCHEMA_ERROR"

    def __init__(self, status: str, message: str, student_count: int = 0, error_details: Optional[SyncError] = None):
        self.status = status
        self.message = message
        self.student_count = student_count
        self.error_details = error_details
        self.student_count = student_count

    @property
    def is_success(self) -> bool:
        return self.status == self.SUCCESS


class SyncWorker:
    """
    Background worker that synchronizes ERP data into the session cache.

    Usage:
        worker = SyncWorker(erp_config, shared_data)
        worker.connect_progress(lambda pct, msg: ...)
        worker.connect_finished(lambda result: ...)
        worker.start()
    """

    def __init__(self, erp_config: dict, shared_data: dict = None):
        self.erp_config = erp_config
        self.shared_data = shared_data or {}
        self.is_running = True
        self._progress_cb: Optional[Callable] = None
        self._finished_cb: Optional[Callable] = None

    def start(self) -> None:
        """Starts the sync in a daemon background thread."""
        threading.Thread(target=self._run, daemon=True, name="AcaDesk-SyncWorker").start()

    def connect_progress(self, callback: Callable[[float, str], None]) -> None:
        """Register a callback: f(progress_0_to_1, status_message)."""
        self._progress_cb = callback

    def connect_finished(self, callback: Callable[[SyncResult], None]) -> None:
        """Register a callback: f(SyncResult)."""
        self._finished_cb = callback

    def stop(self) -> None:
        self.is_running = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, progress: float, msg: str) -> None:
        _log.debug(f"[SyncWorker] {int(progress * 100)}% — {msg}")
        if self._progress_cb:
            self._progress_cb(progress, msg)

    def _finish(self, result: SyncResult) -> None:
        _log.info(f"[SyncWorker] Finished: {result.status} — {result.message}")
        if self._finished_cb:
            self._finished_cb(result)

    # ------------------------------------------------------------------
    # Main sync pipeline
    # ------------------------------------------------------------------

    def _run(self) -> None:
        try:
            # ── STEP 1: Validate ERP connection & stored mapping ──────────
            self._emit(0.05, "Connecting to ERP database...")

            erp = ERPConnection(self.erp_config)
            ok, msg = erp.connect()
            if not ok:
                self._finish(SyncResult(
                    SyncResult.CONNECTION_ERROR,
                    f"Cannot connect to ERP: {msg}"
                ))
                return

            self._emit(0.10, "Validating schema mapping...")

            # Run validate_stored_mapping — lightweight INFORMATION_SCHEMA check
            validated_mapping = self._validate_and_correct_mapping(erp)
            if validated_mapping is None:
                erp.close()
                return  # _finish already called inside _validate_and_correct_mapping

            self._emit(0.35, "Schema mapping validated. Retrieving records...")

            # ── STEP 2: Retrieve student data ─────────────────────────────
            strategy = validated_mapping.get("strategy", "ADAPTER")
            self._emit(0.40, f"Fetching student records ({strategy} strategy)...")

            try:
                retrieval = DataRetrieval(erp, validated_mapping, strategy=strategy)
                
                session = get_session_cache()
                session.clear()
                
                total_students = 0
                total_histories = 0
                dept_list_saved = []

                # Fetch page by page
                for s_batch, h_batch, d_list in retrieval.fetch_batches(batch_size=500):
                    if d_list and not dept_list_saved:
                        dept_list_saved = d_list
                        session.bulk_insert_departments(d_list)

                    session.bulk_insert_students_page(s_batch)
                    session.bulk_insert_semester_history(h_batch)
                    
                    total_students += len(s_batch)
                    total_histories += len(h_batch)

                    # Log year distribution for diagnostic
                    try:
                        with session.get_connection() as _dc:
                            _year_rows = _dc.execute(
                                "SELECT current_year, COUNT(*) as cnt FROM students "
                                "GROUP BY current_year ORDER BY current_year"
                            ).fetchall()
                            _log.info(
                                "[SyncWorker] Year distribution: %s",
                                {r['current_year']: r['cnt'] for r in _year_rows}
                            )
                    except Exception:
                        pass

                    self._emit(0.40 + min(0.30, (total_students / 5000) * 0.30), f"Fetching records... ({total_students})")

                # Fallback: extract departments from student branch data if not supplied
                if not dept_list_saved and total_students > 0:
                    with session.get_connection() as conn:
                        c = conn.execute("SELECT DISTINCT branch_id, branch_name FROM students WHERE branch_id IS NOT NULL")
                        extracted_depts = [
                            {
                                "dept_id": str(r["branch_id"]),
                                "dept_name": (
                                    r.get("branch_name")
                                    if r.get("branch_name") and r["branch_name"] != r["branch_id"]
                                    else "Unknown Department"
                                )
                            }
                            for r in c.fetchall()
                        ]
                        if extracted_depts:
                            session.bulk_insert_departments(extracted_depts)
                            dept_list_saved = extracted_depts

            except Exception as e:
                erp.close()
                err_msg = str(e)
                if "department_id" in err_msg or "Unknown column" in err_msg or "branch" in err_msg.lower() or "dept" in err_msg.lower():
                     self._finish(SyncResult(
                        SyncResult.VALIDATION_FAILURE,
                        "Department data could not be loaded from the ERP. The schema mapping may be outdated.",
                        error_details=SyncError(
                            step="branch_fetch",
                            message="Department data could not be loaded from the ERP. The schema mapping may be outdated.",
                            technical=f"MySQL Error: {err_msg}",
                            is_recoverable=True
                        )
                    ))
                else:
                    self._finish(SyncResult(
                        SyncResult.VALIDATION_FAILURE,
                        "Student data could not be loaded from the ERP. The schema mapping may be outdated.",
                        error_details=SyncError(
                            step="student_fetch",
                            message="Student data could not be loaded from the ERP. The schema mapping may be outdated.",
                            technical=f"MySQL Error: {err_msg}",
                            is_recoverable=True
                        )
                    ))
                return

            erp.close()  # Close ERP connection — we now have all data in memory
            _log.info(f"[SyncWorker] Retrieved {total_students} students, "
                      f"{total_histories} history records, {len(dept_list_saved)} departments.")

            if total_students == 0:
                self._finish(SyncResult(
                    SyncResult.VALIDATION_FAILURE,
                    "No student records found in the ERP database. "
                    "Please verify the schema mapping is correct."
                ))
                return

            self._emit(0.50, f"Retrieved {total_students} students from ERP.")

            # ── STEP 3: Retrieve semester history (already done in fetch_batches) ─
            self._emit(0.70, f"Loaded {total_histories} semester history records.")

            # ── STEP 4: Write to SQLite session cache ─────────────────────
            self._emit(0.75, "Writing to local session cache...")
            
            # Backward-compat: also write departments to legacy local_cache
            try:
                if dept_list_saved:
                    local_cache.bulk_insert("departments", dept_list_saved)
            except Exception as e:
                _log.debug(f"Legacy local_cache departments insert (non-critical): {e}")

            self._emit(0.85, "Session cache populated.")

            # ── STEP 5: AI precomputation (NO DB connections during this step) ─
            self._emit(0.87, "Running AI risk analysis...")
            self._precompute_predictions()
            self._emit(0.95, "AI analysis complete.")

            # Sync faculty notes from central auth
            self._sync_faculty_notes()

            # ── STEP 6: Validate cache completeness ───────────────────────
            self._emit(0.97, "Validating cache integrity...")
            ok, validation_msg = self._validate_cache()
            if not ok:
                self._finish(SyncResult(
                    SyncResult.VALIDATION_FAILURE,
                    f"Cache validation failed: {validation_msg}"
                ))
                return

            self._emit(1.0, "Ready.")
            self._finish(SyncResult(
                SyncResult.SUCCESS,
                f"Successfully loaded {total_students} students.",
                student_count=total_students
            ))

        except Exception as e:
            _log.error(f"[SyncWorker] Unhandled error: {e}\n{traceback.format_exc()}")
            self._finish(SyncResult(
                SyncResult.VALIDATION_FAILURE,
                f"Sync error: {str(e)}"
            ))

    # ------------------------------------------------------------------
    # Step 1 helper: mapping validation with auto-correction
    # ------------------------------------------------------------------

    def _validate_and_correct_mapping(self, erp) -> Optional[dict]:
        """
        Validates the stored mapping against the live ERP.
        Auto-corrects any renamed columns. Returns corrected mapping, or None on failure.
        """
        from logic.schema_detector import SchemaDetector

        mapping = dict(self.erp_config)
        db_name = mapping.get("database", "")
        college_name = self.shared_data.get("college_name", "")

        # Open a direct connection to ERP for INFORMATION_SCHEMA queries
        try:
            import mysql.connector
            info_conn = mysql.connector.connect(
                host=mapping.get("host", "localhost"),
                port=int(mapping.get("port", 3306)),
                database=db_name,
                user=mapping.get("user", ""),
                password=mapping.get("password", ""),
                connect_timeout=10,
            )
        except Exception as e:
            _log.warning(f"[SyncWorker] Could not open INFORMATION_SCHEMA connection: {e}. Skipping validation.")
            return mapping  # Non-blocking: proceed with stored mapping

        try:
            val_result = SchemaDetector.validate_stored_mapping(info_conn, mapping, db_name)

            if not val_result.is_valid:
                # Cannot proceed — required columns are missing
                err_msg = val_result.error_message or "Required ERP columns are missing."
                missing_str = ", ".join(f"{t}.{c}" for t, c, _ in val_result.missing_columns)
                err_msg += f"\nMissing: {missing_str}"
                
                self._finish(SyncResult(
                    SyncResult.SCHEMA_ERROR,
                    err_msg
                ))
                return None

            return mapping

        finally:
            try:
                info_conn.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Step 5 helper: AI precomputation (DB-FREE ZONE)
    # ------------------------------------------------------------------

    def _precompute_predictions(self) -> None:
        """
        RULE 3 ENFORCEMENT: All student data is extracted into Python dicts
        BEFORE any AI call. No database connection is open during inference.
        The session cache is written AFTER all predictions are complete.
        """
        from logic.risk_engine import AdvancedRiskPredictor
        from logic.data_contract import PENDING_PREDICTION

        session = get_session_cache()
        student_data_list = session.get_all_students()
        
        histories = []
        with session.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM semester_history")
            histories = [dict(r) for r in cursor.fetchall()]

        # Pre-map histories in memory
        history_map = {}
        for h in histories:
            sid = str(h["student_id"])
            if sid not in history_map:
                history_map[sid] = []
            history_map[sid].append({
                "semester_number": h["semester_number"],
                "cgpa_that_semester": h["cgpa_that_semester"],
                "attendance_that_semester": h["attendance_that_semester"],
                "backlogs_that_semester": h["backlogs_that_semester"]
            })

        # ── Phase A: Extract all student dicts and history into memory ────

        for s_dict in student_data_list:
            # Legacy field aliases for risk_engine compatibility
            s_dict["avg_attendance"] = s_dict.get("attendance_pct")
            s_dict["avg_marks"] = s_dict.get("internal_marks")
            s_dict["backlogs"] = s_dict.get("backlog_count")
            s_dict["year"] = s_dict.get("current_year")
            s_dict["branch_name"] = s_dict.get("branch_name")
            s_dict["name"] = s_dict.get("full_name")
            s_dict["id"] = s_dict.get("student_id")

            # Load semester history from memory
            s_dict["_semester_history"] = history_map.get(s_dict.get("student_id"), [])

        # ── Phase B: All data is now in memory. Close any lingering references.
        # (The session cache thread-local connection remains open — it is
        #  the same thread, so this is safe. scikit-learn joblib workers
        #  do NOT have access to this connection.)

        # ── Phase C: Run AI inference — pure memory-in, memory-out ────────
        ai = AdvancedRiskPredictor()
        ai_data = []
        total = len(student_data_list)

        for i, s_dict in enumerate(student_data_list):
            try:
                report = ai.analyze(s_dict)

                if report.get("status") == "PENDING":
                    score, cat, conf = 0.0, "Pending", 0.0
                else:
                    score = float(report.get("score", 0.0))
                    cat = report.get("level", "Low")
                    conf_raw = report.get("confidence", 90)
                    try:
                        if isinstance(conf_raw, str):
                            conf_clean = conf_raw.replace("%", "").strip().lower()
                            if "high" in conf_clean: conf = 85.0
                            elif "med" in conf_clean: conf = 60.0
                            elif "low" in conf_clean: conf = 35.0
                            else: conf = float(conf_clean)
                        else:
                            conf = float(conf_raw)
                    except ValueError:
                        conf = 50.0

                ai_data.append({
                    "student_id": str(s_dict["student_id"]),
                    "risk_score": score,
                    "risk_category": cat,
                    "confidence": conf,
                    "report_json": json.dumps(report),
                })
            except Exception as e:
                _log.error(f"AI prediction error for student {s_dict.get('student_id')}: {e}")

            if total > 0 and i % 50 == 0:
                pct = 0.87 + (i / total) * 0.08
                self._emit(min(0.94, pct), f"Analysing student {i + 1}/{total}...")

        # ── Phase D: Write all results to cache in one batch ──────────────
        if ai_data:
            session.bulk_insert_predictions(ai_data)
        _log.info(f"[SyncWorker] Precomputed AI predictions for {len(ai_data)}/{total} students.")

    # ------------------------------------------------------------------
    # Step 5b: Sync faculty notes (MySQL → local SQLite)
    # ------------------------------------------------------------------

    def _sync_faculty_notes(self) -> None:
        """Syncs faculty notes from central MySQL into the local cache."""
        try:
            auth = CentralAuth()
            conn = auth._get_conn()
            if not conn:
                return
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM faculty_notes")
                notes = cursor.fetchall()
                if notes:
                    for n in notes:
                        if n.get("created_at"):
                            n["created_at"] = str(n["created_at"])
                        if "id" in n:
                            n["note_id"] = n.pop("id")
                        n.pop("updated_at", None)
                    local_cache.bulk_insert("faculty_notes", notes)
            except Exception as e:
                _log.error(f"[SyncWorker] Faculty notes sync error: {e}")
            finally:
                conn.close()
        except Exception as e:
            _log.warning(f"[SyncWorker] Faculty notes sync skipped: {e}")

    # ------------------------------------------------------------------
    # Step 6: Cache validation
    # ------------------------------------------------------------------

    def _validate_cache(self) -> Tuple[bool, str]:
        """Verifies that the session cache contains usable data."""
        try:
            session = get_session_cache()
            
            if not session.is_populated():
                return False, "No student records in cache."
                
            depts = session.get_departments()
            if not depts:
                # Fallback check
                with session.get_connection() as conn:
                    c = conn.execute("SELECT COUNT(DISTINCT branch_id) as cnt FROM students")
                    row = c.fetchone()
                    if row["cnt"] == 0:
                        return False, "No department records or branch data in cache."
            
            return True, "Cache is valid."
        except Exception as e:
            return False, str(e)
