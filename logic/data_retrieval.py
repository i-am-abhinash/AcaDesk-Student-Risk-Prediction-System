"""
AcaDesk Data Retrieval Layer — Layer 3
========================================
Executes data retrieval from a college ERP and produces NormalizedStudent
records conforming to AcaDesk's Internal Data Contract.

Two strategies are implemented behind one interface:

  VIEW STRATEGY  — When vw_acadesk_student/academic/branch views exist.
                   Simple SELECT, fast and predictable.

  ADAPTER STRATEGY — General case. Generates JOIN queries dynamically
                     using the stored column mapping from erp_configs.
                     All table/column names come EXCLUSIVELY from the
                     validated mapping, never from runtime user input.

CRITICAL CONTRACT: Both strategies produce identical output —
  List[NormalizedStudent] + List[SemesterRecord].
No code above this layer may ever see raw ERP data or know which
strategy was used.
"""

from __future__ import annotations
import logging
import math
import mysql.connector
from typing import List, Optional, Tuple, Dict, Any

from logic.data_contract import NormalizedStudent, SemesterRecord

_log = logging.getLogger(__name__)

# Names of the standard AcaDesk views (if they exist in the ERP)
VIEW_STUDENT = "vw_acadesk_student"
VIEW_ACADEMIC = "vw_acadesk_academic"
VIEW_BRANCH = "vw_acadesk_branch"


def _safe_float(val, default=None):
    if val is None: return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def _safe_int(val, default=None):
    if val is None: return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _parse_year(year_val) -> int:
    """Converts any year representation to an integer 1-4."""
    import re as _re
    if year_val is None:
        return 1
    name = str(year_val).lower().strip()
    # Ordinal word forms
    if 'first' in name or '1st' in name:   return 1
    if 'second' in name or '2nd' in name:  return 2
    if 'third' in name or '3rd' in name:   return 3
    if 'fourth' in name or '4th' in name:  return 4
    if 'fifth' in name or '5th' in name:   return 4
    # Pure digit / stripped forms
    stripped = name.replace('year', '').replace('yr', '').replace(' ', '').strip()
    if stripped.isdigit():
        val = int(stripped)
        if 1 <= val <= 4:
            return val
        if val > 4:
            return 4
    # Roman numerals
    roman_map = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4}
    if stripped in roman_map:
        return roman_map[stripped]
    # Extract first digit found anywhere
    digits = _re.findall(r'\d+', name)
    if digits:
        val = int(digits[0])
        return min(4, max(1, val))
    _log.warning("_parse_year: unrecognised year string '%s', defaulting to 1", year_val)
    return 1


class DataRetrieval:
    """
    Layer 3: unified ERP data retrieval interface.

    Both ViewStrategy and AdapterStrategy implement the same interface.
    After construction, call:
        students, histories, depts = retrieval.fetch_all()
    """

    def __init__(self, erp_connection, mapping: dict, strategy: str = "ADAPTER"):
        """
        Args:
            erp_connection: ERPConnection instance (already connected).
            mapping: validated column mapping dict from erp_configs.
            strategy: "VIEW" or "ADAPTER"
        """
        self._conn = erp_connection
        self._mapping = mapping
        self._strategy = strategy.upper()

        if self._strategy == "VIEW":
            self._impl = _ViewStrategy(erp_connection, mapping)
        elif self._strategy == "INTELLIGENT_ADAPTER":
            self._impl = _IntelligentAdapterStrategy(erp_connection, mapping)
        else:
            self._impl = _AdapterStrategy(erp_connection, mapping)

    def fetch_all(self) -> Tuple[List[NormalizedStudent], List[SemesterRecord], List[dict]]:
        """
        Fetches all students, their semester histories, and departments.

        Returns:
            (students, semester_histories, dept_list)
        """
        _log.info(f"DataRetrieval: fetching using strategy={self._strategy}")
        return self._impl.fetch_all()

    def fetch_batches(self, batch_size=500) -> Generator[Tuple[List[NormalizedStudent], List[SemesterRecord], List[dict]], None, None]:
        """
        Yields batches of students, histories, and departments.
        """
        if hasattr(self._impl, "fetch_batches"):
            yield from self._impl.fetch_batches(batch_size)
        else:
            # Fallback for VIEW strategy
            s, h, d = self._impl.fetch_all()
            for i in range(0, len(s), batch_size):
                yield s[i:i+batch_size], h[i:i+batch_size], d if i == 0 else []

    def fetch_branch_map(self) -> Dict[str, str]:
        """Returns {branch_id: branch_name}."""
        return self._impl.fetch_branch_map()


# ---------------------------------------------------------------------------
# STRATEGY 1: VIEW STRATEGY
# ---------------------------------------------------------------------------

class _ViewStrategy:
    """
    Fast path: reads from standardized AcaDesk-compatible SQL views.
    Expected view schemas:
      vw_acadesk_student  → student_id, full_name, branch_id, year, semester, ...
      vw_acadesk_academic → student_id, attendance_pct, internal_marks, cgpa, ...
      vw_acadesk_branch   → branch_id, branch_name
    """

    def __init__(self, erp_connection, mapping: dict):
        self._conn = erp_connection
        self._mapping = mapping

    def fetch_all(self) -> Tuple[List[NormalizedStudent], List[SemesterRecord], List[dict]]:
        students = []
        histories = []
        depts = self.fetch_branch_map()
        dept_lookup = depts  # branch_id → name

        try:
            cursor = self._conn.cursor(dictionary=True)
            cursor.execute(f"SELECT * FROM {VIEW_STUDENT}")
            s_rows = cursor.fetchall()

            cursor.execute(f"SELECT * FROM {VIEW_ACADEMIC}")
            a_rows = cursor.fetchall()
            cursor.close()
        except Exception as e:
            _log.error(f"VIEW STRATEGY fetch failed: {e}")
            return [], [], list(depts.items())

        # Build academic lookup by student_id
        academic_lookup: dict[str, dict] = {}
        for a in a_rows:
            sid = str(a.get("student_id", ""))
            academic_lookup[sid] = a

        for row in s_rows:
            sid = str(row.get("student_id", ""))
            a = academic_lookup.get(sid, {})
            branch_id = str(row.get("branch_id", ""))

            student = NormalizedStudent(
                student_id=sid,
                full_name=str(row.get("full_name", "")),
                display_name=str(row.get("full_name", "")),
                display_reg_no=sid,
                registration_no=sid,
                branch_id=branch_id,
                branch_name=dept_lookup.get(branch_id, branch_id),
                current_year=_parse_year(row.get("year", row.get("current_year", 1))),
                current_semester=_safe_int(row.get("current_semester", 1), 1),
                total_semesters_completed=_safe_int(row.get("total_semesters_completed", 0)),
                admission_type=row.get("admission_type"),
                entrance_rank=_safe_int(row.get("entrance_rank")) or None,
                attendance_pct=_safe_float(a.get("attendance_pct")),
                internal_marks=_safe_float(a.get("internal_marks")),
                mid_exam_score=_safe_float(a.get("mid_exam_score")),
                assignment_marks=_safe_float(a.get("assignment_marks")),
                lab_performance=_safe_float(a.get("lab_performance")),
                cgpa=_safe_float(a.get("cgpa")),
                backlog_count=_safe_int(a.get("backlog_count")),
                consecutive_absences=_safe_int(a.get("consecutive_absences")),
                leave_frequency=_safe_int(a.get("leave_frequency")),
                tenth_percentage=_safe_float(row.get("tenth_percentage")) or None,
                inter_percentage=_safe_float(row.get("inter_percentage")) or None,
                diploma_percentage=_safe_float(row.get("diploma_percentage")) or None,
                email=row.get("email"),
                parent_email=row.get("parent_email"),
                parent_phone=row.get("parent_phone"),
            )
            students.append(student)

        dept_list = [{"dept_id": k, "dept_name": v} for k, v in dept_lookup.items()]
        return students, histories, dept_list

    def fetch_branch_map(self) -> Dict[str, str]:
        try:
            cursor = self._conn.cursor(dictionary=True)
            cursor.execute(f"SELECT branch_id, branch_name FROM {VIEW_BRANCH}")
            rows = cursor.fetchall()
            cursor.close()
            return {str(r["branch_id"]): str(r["branch_name"]) for r in rows}
        except Exception as e:
            _log.error(f"VIEW STRATEGY fetch_branch_map failed: {e}")
            return {}


# ---------------------------------------------------------------------------
# STRATEGY 2: ADAPTER STRATEGY
# ---------------------------------------------------------------------------

class _AdapterStrategy:
    def __init__(self, erp_connection, mapping: dict):
        self._conn = erp_connection
        self._m = mapping

    def _col(self, *keys: str) -> Optional[str]:
        for k in keys:
            val = self._m.get(k, "")
            if val:
                return val
        return None

    def _tbl(self, key: str) -> str:
        return self._m.get(key, "")

    def fetch_branch_map(self) -> Dict[str, str]:
        """Returns {branch_id: branch_name}."""
        b_tbl = self._tbl("tbl_branch")
        b_id = self._col("col_branch_pk", "branch_pk_in_branch_table", "col_branch_pk") or "id"
        b_name = self._col("col_branch_name", "branch_name_column", "col_branch_name") or "name"
        
        if not b_tbl:
            return {}
        try:
            cursor = self._conn.cursor(dictionary=True)
            cursor.execute(f"SELECT {b_id} AS bid, {b_name} AS bname FROM {b_tbl}")
            rows = cursor.fetchall()
            cursor.close()
            return {str(r["bid"]): str(r["bname"]) for r in rows}
        except Exception as e:
            _log.error(f"ADAPTER fetch_branch_map failed: {e}")
            raise e

    def fetch_all(self) -> Tuple[List[NormalizedStudent], List[SemesterRecord], List[dict]]:
        students = []
        histories = []
        dept_list = []
        
        for s_batch, h_batch, d_list in self.fetch_batches(batch_size=9999999): # Fallback for old callers
            students.extend(s_batch)
            histories.extend(h_batch)
            if d_list:
                dept_list = d_list
                
        return students, histories, dept_list

    def _build_extension_subquery(self, ext_key: str, ext_info: dict, s_tbl: str, s_id: str) -> str:
        """
        Builds a correlated subquery for a mapping extension.
        """
        t = ext_info.get("type", "")
        rtbl = ext_info.get("resolved_table", "")
        rcol = ext_info.get("resolved_column", "")
        if not rtbl or not rcol:
            return "NULL"
            
        fk_col = self._col("col_student_join", "col_academic_join") or "student_id"
        
        if t == "DERIVED_AGGREGATE":
            agg = ext_info.get("recipe", {}).get("aggregation_function", "MAX")
            return f"(SELECT {agg}({rcol}) FROM {rtbl} _ext WHERE _ext.{fk_col} = s.{s_id})"
            
        elif t == "STUDENT_LINKED_TABLE":
            return f"(SELECT {rcol} FROM {rtbl} _ext WHERE _ext.{fk_col} = s.{s_id} LIMIT 1)"
            
        return "NULL"

    def fetch_batches(self, batch_size=500) -> Generator[Tuple[List[NormalizedStudent], List[SemesterRecord], List[dict]], None, None]:
        depts = self.fetch_branch_map()
        dept_list = [{"dept_id": k, "dept_name": v} for k, v in depts.items()]
        
        s_tbl = self._tbl("tbl_student")
        a_tbl = self._tbl("tbl_academic")
        ext = self._m.get("mapping_extensions", {})
        if not s_tbl or not a_tbl:
            _log.error("ADAPTER: tbl_student or tbl_academic not configured.")
            yield [], [], dept_list
            return

        s_id = self._col("col_student_id", "col_id") or "id"
        s_name = self._col("col_student_name", "col_name") or "name"
        s_year = self._col("col_student_year", "col_year") or "year"
        s_branch_fk = self._col("col_branch_fk", "col_branch_join", "branch_fk_in_student") or "branch_id"
        a_join = self._col("col_academic_join", "col_student_join") or "student_id"

        select_parts = [
            f"s.{s_id} AS sid",
            f"s.{s_name} AS sname"
        ]
        joins = []

        # Branch Join — always resolve to human-readable name if lookup table available
        branch_type = self._col("col_branch_type", "branch_type") or "DIRECT"
        b_tbl = self._tbl("tbl_branch")
        b_pk = self._col("col_branch_pk", "branch_pk_in_branch_table") or "id"
        b_name_col = self._col("col_branch_name", "branch_name_column") or "name"
        if branch_type == "FK_LOOKUP" or (b_tbl and b_pk and b_name_col):
            select_parts.append(f"s.{s_branch_fk} AS sbranch")
            select_parts.append(f"COALESCE(b.{b_name_col}, 'Unknown Department') AS dname")
            joins.append(f"LEFT JOIN {b_tbl} b ON s.{s_branch_fk} = b.{b_pk}")
        else:
            select_parts.append(f"s.{s_branch_fk} AS sbranch")
            select_parts.append(f"s.{s_branch_fk} AS dname")

        # Year Join
        if "current_year" in ext:
            sq = self._build_extension_subquery("current_year", ext["current_year"], s_tbl, s_id)
            select_parts.append(f"{sq} AS syear")
        else:
            year_type = self._col("col_year_type", "year_field_type") or "DIRECT"
            if year_type == "FK_LOOKUP":
                y_tbl = self._col("col_year_lookup_table", "year_lookup_table")
                y_pk = self._col("col_year_lookup_pk", "year_lookup_pk")
                y_val = self._col("col_year_lookup_value", "year_lookup_value")
                select_parts.append(f"y.{y_val} AS syear")
                joins.append(f"LEFT JOIN {y_tbl} y ON s.{s_year} = y.{y_pk}")
            else:
                select_parts.append(f"s.{s_year} AS syear")

        # Parent Contacts Table
        if "parent_email" in ext:
            sq = self._build_extension_subquery("parent_email", ext["parent_email"], s_tbl, s_id)
            select_parts.append(f"{sq} AS parent_email")
        elif self._col("col_parent_email", "col_parent_email"):
            s_p_email = self._col("col_parent_email", "col_parent_email")
            select_parts.append(f"s.{s_p_email} AS parent_email")
            
        if "parent_phone" in ext:
            sq = self._build_extension_subquery("parent_phone", ext["parent_phone"], s_tbl, s_id)
            select_parts.append(f"{sq} AS parent_phone")
        elif self._col("col_parent_phone", "col_parent_phone"):
            s_p_phone = self._col("col_parent_phone", "col_parent_phone")
            select_parts.append(f"s.{s_p_phone} AS parent_phone")

        if not ("parent_email" in ext or "parent_phone" in ext):
            p_tbl = self._tbl("tbl_parent_contacts")
            p_join = self._col("col_parent_join", "col_parent_student_join")
            if p_tbl and p_join:
                p_email = self._col("col_parent_email_in_tbl", "col_parent_email_in_tbl")
                p_phone = self._col("col_parent_phone_in_tbl", "col_parent_phone_in_tbl")
                joins.append(f"LEFT JOIN {p_tbl} pc ON pc.{p_join} = s.{s_id}")
                if p_email: select_parts.append(f"pc.{p_email} AS parent_email")
                if p_phone: select_parts.append(f"pc.{p_phone} AS parent_phone")

        s_email = self._col("col_email", "col_email")
        if s_email: select_parts.append(f"s.{s_email} AS email")
        
        s_adm_type = self._col("col_admission_type", "col_admission_type")
        if s_adm_type: select_parts.append(f"s.{s_adm_type} AS admission_type")

        # Academic Fields
        optional_a_cols = {
            "att": self._col("col_attendance", "col_att"),
            "marks": self._col("col_internal_marks", "col_marks"),
            "backlogs": self._col("col_backlogs", "col_backlogs"),
            "cgpa": self._col("col_cgpa", "col_cgpa"),
            "tenth": self._col("col_tenth", "col_tenth"),
            "inter": self._col("col_inter", "col_inter"),
            "diploma": self._col("col_diploma", "col_diploma"),
            "lab": self._col("col_lab_perf", "col_lab_perf"),
            "mid": self._col("col_mid_exam", "col_mid_exam"),
            "cons_abs": self._col("col_cons_abs", "col_cons_abs"),
            "leave_freq": self._col("col_leave_freq", "col_leave_freq"),
            "assign": self._col("col_assign_marks", "col_assign_marks"),
            "semester": self._col("col_semester", "col_semester") or "semester"
        }
        
        for alias, col in optional_a_cols.items():
            ext_key = f"{alias}_pct" if alias == "att" else alias # specific mapped key adjustment
            if alias == "att": ext_key = "attendance_pct"
            if alias == "backlogs": ext_key = "backlog_count"
            if ext_key in ext:
                sq = self._build_extension_subquery(ext_key, ext[ext_key], s_tbl, s_id)
                select_parts.append(f"({sq}) AS {alias}")
            elif col: 
                select_parts.append(f"ar.{col} AS {alias}")

        a_sem_col = optional_a_cols.get("semester", "semester")
        joins.append(f"""
            LEFT JOIN (
                SELECT {a_join}, MAX({a_sem_col}) as max_sem
                FROM {a_tbl}
                GROUP BY {a_join}
            ) latest ON latest.{a_join} = s.{s_id}
            LEFT JOIN {a_tbl} ar ON ar.{a_join} = s.{s_id} AND ar.{a_sem_col} = latest.max_sem
        """)

        base_sql = f"SELECT {', '.join(select_parts)} FROM {s_tbl} s " + " ".join(joins)
        
        offset = 0
        while True:
            sql = f"{base_sql} LIMIT {batch_size} OFFSET {offset}"
            try:
                cursor = self._conn.cursor(dictionary=True)
                cursor.execute(sql)
                rows = cursor.fetchall()
                cursor.close()
            except mysql.connector.Error as err:
                _log.error("MySQL connection error: %s", err)
                raise
            except (NameError, AttributeError, TypeError) as e:
                _log.critical(
                    "Programming error in data retrieval "
                    "(not a database error): %s", 
                    e, exc_info=True
                )
                raise
            except Exception as e:
                _log.error("Unexpected error in data retrieval: %s", e)
                raise

            if not rows:
                break

            # First pass: collect basic info to fetch histories
            raw_students = []
            sids = []
            for row in rows:
                sid = str(row.get("sid", ""))
                raw_students.append((sid, row))
                if sid:
                    sids.append(sid)

            _log.info(f"ADAPTER: fetched batch of {len(raw_students)} students (offset {offset}).")
            
            # Fetch histories first to determine total semesters completed
            h_tbl = self._tbl("tbl_history") or self._tbl("tbl_academic")
            histories_batch = []
            student_history_count = {}
            if h_tbl:
                h_join = self._col("col_student_join", "col_academic_join") or "student_id"
                h_sem = self._col("col_semester") or "semester"
                
                if sids:
                    placeholders = ", ".join(["%s"] * len(sids))
                    h_sql = f"SELECT * FROM {h_tbl} WHERE {h_join} IN ({placeholders}) ORDER BY {h_join}, {h_sem} ASC"
                    try:
                        h_cursor = self._conn.cursor(dictionary=True)
                        h_cursor.execute(h_sql, sids)
                        h_rows = h_cursor.fetchall()
                        h_cursor.close()
                        
                        for h_row in h_rows:
                            hsid = str(h_row.get(h_join, ""))
                            student_history_count[hsid] = student_history_count.get(hsid, 0) + 1
                            histories_batch.append(SemesterRecord(
                                student_id=hsid,
                                semester_number=_safe_int(h_row.get(h_sem, 0)),
                                cgpa_that_semester=_safe_float(h_row.get("cgpa", h_row.get("sgpa", 0.0))),
                                attendance_that_semester=_safe_float(h_row.get("attendance_percentage", h_row.get("attendance", h_row.get("attendance_pct", 0.0)))),
                                backlogs_that_semester=_safe_int(h_row.get("backlog_count", h_row.get("backlogs", 0))),
                            ))
                    except Exception as e:
                        _log.debug(f"ADAPTER history fetch failed: {e}")

            # Now build the normalized students
            students_batch = []
            for sid, row in raw_students:
                branch_id = str(row.get("sbranch", ""))
                year = _parse_year(row.get("syear"))
                adm_type = str(row.get("admission_type", "")) if row.get("admission_type") else None
                is_lateral = "lateral" in adm_type.lower() if adm_type else False
                completed = student_history_count.get(sid, 0)
                
                student = NormalizedStudent(
                    student_id=sid,
                    full_name=str(row.get("sname", "")),
                    display_name=str(row.get("sname", "")),
                    display_reg_no=sid,
                    registration_no=sid,
                    branch_id=branch_id,
                    branch_name=(
                        lambda _raw=row.get("dname"):
                        str(_raw) if (_raw and str(_raw) != branch_id)
                        else (depts.get(branch_id) or "Unknown Department")
                    )(),
                    current_year=year,
                    current_semester=completed + 1,
                    total_semesters_completed=completed,
                    admission_type=adm_type,
                    is_lateral=is_lateral,
                    attendance_pct=_safe_float(row.get("att")),
                    internal_marks=_safe_float(row.get("marks")),
                    mid_exam_score=_safe_float(row.get("mid")),
                    assignment_marks=_safe_float(row.get("assign")),
                    lab_performance=_safe_float(row.get("lab")),
                    cgpa=_safe_float(row.get("cgpa")),
                    backlog_count=_safe_int(row.get("backlogs")),
                    consecutive_absences=_safe_int(row.get("cons_abs")),
                    leave_frequency=_safe_int(row.get("leave_freq")),
                    tenth_percentage=_safe_float(row.get("tenth")) or None,
                    inter_percentage=_safe_float(row.get("inter")) or None,
                    diploma_percentage=_safe_float(row.get("diploma")) or None,
                    email=row.get("email"),
                    parent_email=row.get("parent_email"),
                    parent_phone=row.get("parent_phone"),
                )
                students_batch.append(student)

            yield students_batch, histories_batch, dept_list if offset == 0 else []
            offset += batch_size

# ---------------------------------------------------------------------------
def parse_year_to_int(val) -> int:
    if not val: return 1
    v = str(val).lower().strip()
    if '1' in v or 'first' in v or v == 'i': return 1
    if '2' in v or 'second' in v or v == 'ii': return 2
    if '3' in v or 'third' in v or v == 'iii': return 3
    if '4' in v or 'fourth' in v or v == 'iv': return 4
    try:
        return int(float(v))
    except:
        return 1

class _IntelligentAdapterStrategy:
    def __init__(self, erp_connection, mapping: dict):
        self._conn = erp_connection
        self._m = mapping

    def fetch_all(self) -> Tuple[List[NormalizedStudent], List[SemesterRecord], List[dict]]:
        students = []
        histories = []
        dept_list = []
        for s_batch, h_batch, d_list in self.fetch_batches(batch_size=9999999):
            students.extend(s_batch)
            histories.extend(h_batch)
            if d_list: dept_list = d_list
        return students, histories, dept_list

    def fetch_batches(self, batch_size=500):
        m = self._m
        s_tbl = m.get("tbl_student")
        if not s_tbl:
            _log.error("INTELLIGENT ADAPTER: tbl_student is missing.")
            yield [], [], []
            return

        s_pk = m.get("col_student_pk")
        s_name = m.get("col_student_name")
        
        selects = [f"s.{s_pk} AS student_id", f"s.{s_name} AS full_name"]
        joins = []
        
        # Branch
        b_type = m.get("col_branch_type")
        if b_type == "FK_LOOKUP":
            selects.append(f"s.{m.get('col_branch_fk')} AS branch_id_raw")
            selects.append(f"br.{m.get('col_branch_name')} AS branch_name")
            joins.append(f"LEFT JOIN {m.get('tbl_branch')} br ON s.{m.get('col_branch_fk')} = br.{m.get('col_branch_pk')}")
        elif b_type == "DIRECT":
            selects.append(f"s.{m.get('col_branch_name')} AS branch_id_raw")
            selects.append(f"s.{m.get('col_branch_name')} AS branch_name")
            
        # Year
        y_type = m.get("col_year_type")
        if y_type == "FK_LOOKUP":
            selects.append(f"yr.{m.get('col_year_lookup_val')} AS year_name_raw")
            joins.append(f"LEFT JOIN {m.get('col_year_lookup_table')} yr ON s.{m.get('col_student_year')} = yr.{m.get('col_year_lookup_pk')}")
        elif y_type == "DIRECT":
            selects.append(f"s.{m.get('col_student_year')} AS year_name_raw")
        elif y_type == "DERIVED_AGGREGATE" or y_type == "DERIVED":
            # For simplicity, assuming semester-based year derivation was mapped directly if possible,
            # or we just rely on current_semester fallback.
            pass
            
        # Simple Direct fields
        direct_fields = {
            "col_email": "email",
            "col_internal_marks": "internal_marks",
            "col_cgpa": "cgpa",
            "col_semester": "semester",
            "col_backlogs": "backlog_count",
            "col_mid_exam": "mid_exam_score",
            "col_lab_perf": "lab_performance",
            "col_assignments": "assignment_marks",
            "col_tenth": "tenth_percentage",
            "col_inter": "inter_percentage",
            "col_diploma": "diploma_percentage",
            "col_cons_abs": "consecutive_absences",
            "col_leave_freq": "leave_frequency",
            "col_parent_email": "parent_email",
            "col_parent_phone": "parent_phone"
        }
        
        # Only add to selects if DIRECT method was stored. But we flattened the mappings.
        # We can just check if they are populated and we join appropriately.
        # Note: the new mapping sets col_X_type = "DIRECT" or similar, OR we just use the flattened col_name 
        # and assume it belongs to the target table.
        # The prompt specifies: [academic columns if DIRECT]
        
        import json
        ac_join_path = None
        if m.get("join_path_academic"):
            try:
                ac_join_path = json.loads(m["join_path_academic"])
            except: pass
            
        if ac_join_path and ac_join_path.get("direct_fk"):
            a_tbl = m.get("tbl_academic")
            a_join_col = m.get("col_academic_join")
            joins.append(f"LEFT JOIN (SELECT * FROM {a_tbl} WHERE id IN (SELECT MAX(id) FROM {a_tbl} GROUP BY {a_join_col})) ar ON ar.{a_join_col} = s.{s_pk}")
            
            # Map academic direct cols to ar.X
            # Let's assume all academic cols are on `ar` if they are defined
            for k, v in direct_fields.items():
                col_name = m.get(k)
                if col_name and k not in ["col_email", "col_parent_email", "col_parent_phone"]:
                    selects.append(f"ar.{col_name} AS {v}")
                    
        # Parent / Linked (Simplification: just direct on student for now unless STUDENT_LINKED is implemented via joins)
        for k in ["col_email", "col_parent_email", "col_parent_phone"]:
            col_name = m.get(k)
            if col_name:
                selects.append(f"s.{col_name} AS {direct_fields[k]}")
                
        # Attendance Derived
        if m.get("col_att_type") == "DERIVED_AGGREGATE":
            att_join = m.get("col_attendance_join")
            att_status = m.get("col_attendance_status")
            vals_str = m.get("col_attendance_present_vals")
            att_tbl = m.get("tbl_attendance")
            if vals_str:
                joins.append(f"LEFT JOIN (SELECT {att_join} AS sid, SUM(CASE WHEN {att_status} IN ({vals_str}) THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS att_pct_computed FROM {att_tbl} GROUP BY {att_join}) att_agg ON att_agg.sid = s.{s_pk}")
                selects.append("att_agg.att_pct_computed AS attendance_pct")
        elif m.get("col_att_pct"):
             # Direct
             selects.append(f"ar.{m.get('col_att_pct')} AS attendance_pct")
             
        # Build SQL
        base_sql = f"SELECT {', '.join(selects)} FROM {s_tbl} s " + " ".join(joins)
        
        offset = 0
        while True:
            sql = f"{base_sql} LIMIT {batch_size} OFFSET {offset}"
            try:
                cursor = self._conn.cursor(dictionary=True)
                cursor.execute(sql)
                rows = cursor.fetchall()
                cursor.close()
            except Exception as e:
                _log.error(f"INTELLIGENT ADAPTER Error: {e}")
                break
                
            if not rows: break
            
            students_batch = []
            dept_list_map = {}
            for row in rows:
                sid = str(row.get("student_id", ""))
                bid = str(row.get("branch_id_raw", ""))
                bname = str(row.get("branch_name", bid))
                dept_list_map[bid] = bname
                
                students_batch.append(NormalizedStudent(
                    student_id=sid,
                    full_name=str(row.get("full_name", "")),
                    display_name=str(row.get("full_name", "")),
                    display_reg_no=sid,
                    registration_no=sid,
                    branch_id=bid,
                    branch_name=bname,
                    current_year=parse_year_to_int(row.get("year_name_raw")),
                    attendance_pct=_safe_float(row.get("attendance_pct")),
                    internal_marks=_safe_float(row.get("internal_marks")),
                    mid_exam_score=_safe_float(row.get("mid_exam_score")),
                    assignment_marks=_safe_float(row.get("assignment_marks")),
                    lab_performance=_safe_float(row.get("lab_performance")),
                    cgpa=_safe_float(row.get("cgpa")),
                    backlog_count=_safe_int(row.get("backlog_count")),
                    consecutive_absences=_safe_int(row.get("consecutive_absences")),
                    leave_frequency=_safe_int(row.get("leave_frequency")),
                    tenth_percentage=_safe_float(row.get("tenth_percentage")) or None,
                    inter_percentage=_safe_float(row.get("inter_percentage")) or None,
                    diploma_percentage=_safe_float(row.get("diploma_percentage")) or None,
                    email=row.get("email"),
                    parent_email=row.get("parent_email"),
                    parent_phone=row.get("parent_phone"),
                ))
            
            dlist = [{"dept_id": k, "dept_name": v} for k, v in dept_list_map.items()]
            yield students_batch, [], dlist if offset == 0 else []
            offset += batch_size
