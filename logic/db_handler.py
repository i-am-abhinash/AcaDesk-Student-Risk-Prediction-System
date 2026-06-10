import sys
import os

class DBHandler:
    def __init__(self, config_dict=None):
        self.config = config_dict or {}
        self.connected = False
        self.conn = None
        self.cursor = None

        if not self.config: return

        # SAFETY NET: Use .get(key, "default_name") to prevent 'none' errors
        # Initialize map with default names; will be overridden by schema discovery if possible
        self.map = {
            "tbl_student": "student",
            "tbl_academic": "academics",
            "tbl_department": "departments",
            "join_student": "student_id",
            "join_branch": "branch_id",
            "id": "roll_no",
            "name": "name",
            "branch_name": "branch_name",
            "year": "year",
            "marks": "marks"
        }
        # Column synonym definitions for dynamic mapping
        self.COLUMN_SYNONYMS = {
            "attendance": ["attendance", "attendance_percentage", "attendance_percent", "attendance_pct", "att"],
            "backlogs": ["backlog_count", "backlogs", "backlog", "arrears"],
            "marks": ["internal_marks", "marks", "total_marks", "score", "obtained_marks"],
            "cgpa": ["cgpa", "cumulative_gpa", "gpa"],
            "student_id": ["id", "student_id", "registration_no", "roll_no", "reg_no"],
            "registration_no": ["registration_no", "reg_no", "roll_no", "registration_number"],
            "name": ["name", "student_name", "full_name"]
        }
        # Required concept keys for validation
        self.REQUIRED_CONCEPTS = {"attendance", "backlogs", "marks", "cgpa", "student_id"}

        # Containers for discovered column names
        self.student_columns = set()
        self.academic_columns = set()
        # Expected logical column keys for diagnostics
        # Expected keys are now derived from synonyms; no hardcoded expected sets
        # Connect first, then discover schema using the live cursor
        self.connect()
        try:
            self._discover_schema()
            self._build_alias_map()
        except Exception as e:
            pass  # Keep defaults if discovery fails


    def connect(self):
        try:
            import mysql.connector
            from mysql.connector import errorcode
            self.conn = mysql.connector.connect(
                host=self.config.get('host', 'localhost'),
                user=self.config.get('user', 'root'),
                password=self.config.get('password', ''),
                database=self.config.get('database', 'engineering_college'),
                port=int(self.config.get('port', 3306)),
                connection_timeout=3
            )
            self.cursor = self.conn.cursor(dictionary=True, buffered=True)
            self.connected = True
            
            # Read-Only Validation Check
            try:
                self.cursor.execute("SELECT 1")
                self.cursor.fetchall() # Consume the result completely
                # We can't safely test INSERT without altering ERP, so we trust the DB user privileges
                # Ideally, we verify GRANTS here, but checking connection is the first step.
            except Exception as e:
                return False, "ERP connection established but Read-Only enforcement validation failed."
                
            return True, "Connection Successful"
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                return False, "Authentication failed.\nInvalid database username or incorrect password."
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                return False, "Specified database does not exist."
            else:
                return False, f"Database server unreachable.\nCheck network connectivity.\n{err.msg}"
        except Exception as e:
            msg = str(e).lower()
            if "unknown mysql server host" in msg:
                return False, "Unable to reach database server.\nVerify host address."
            elif "connection refused" in msg or "port" in msg:
                return False, "Database server found but specified port is unreachable."
            return False, f"Network Failure: {e}"

    # Enhanced schema discovery – map tables and collect column info
    def _discover_schema(self):
        """Detect ERP schema, update table mappings, and discover column sets.
        It queries information_schema for tables and columns, then populates
        self.student_columns and self.academic_columns.
        """
        try:
            # Ensure we have a connection first
            if not self.conn:
                self.connect()
            if not self.conn:
                return
            db_name = self.config.get('database')
            # ---- Table discovery ----
            self.cursor.execute(
                "SELECT TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA = %s",
                (db_name,)
            )
            tables = [row['TABLE_NAME'] for row in self.cursor.fetchall()]
            for tbl in tables:
                lowered = tbl.lower()
                if 'student' in lowered:
                    self.map['tbl_student'] = tbl
                if 'academic' in lowered:
                    self.map['tbl_academic'] = tbl
                if 'branch' in lowered:
                    self.map['tbl_branch'] = tbl
                if 'department' in lowered or 'dept' in lowered:
                    self.map['tbl_department'] = tbl
            # ---- Column discovery for student table ----
            student_tbl = self.map.get('tbl_student')
            if student_tbl:
                self.cursor.execute(
                    "SELECT COLUMN_NAME FROM information_schema.columns WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                    (db_name, student_tbl)
                )
                self.student_columns = {row['COLUMN_NAME'] for row in self.cursor.fetchall()}
                # Update primary key and foreign key mappings based on discovered columns
                if 'id' in self.student_columns:
                    self.map['id'] = 'id'
                if 'department_id' in self.student_columns:
                    self.map['join_branch'] = 'department_id'
                if 'year_id' in self.student_columns:
                    self.map['year'] = 'year_id'
                # Optionally map name column if different
                if 'name' in self.student_columns:
                    self.map['name'] = 'name'
            # ---- Column discovery for academic table ----
            academic_tbl = self.map.get('tbl_academic')
            if academic_tbl:
                self.cursor.execute(
                    "SELECT COLUMN_NAME FROM information_schema.columns WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                    (db_name, academic_tbl)
                )
                self.academic_columns = {row['COLUMN_NAME'] for row in self.cursor.fetchall()}
        except Exception as e:
            print(f"Schema discovery error: {e}")
    def validate_tables(self):
        """Validate ERP connection and discover tables dynamically.
        Returns (bool, str) where the message includes discovered table counts.
        Validation succeeds if the connection is alive and at least one student-related table exists.
        """
        if not self.conn:
            return False, "No connection"
        try:
            # Retrieve all tables in the configured database
            self.cursor.execute(
                "SELECT TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA = %s",
                (self.config.get('database'),)
            )
            tables = [row['TABLE_NAME'] for row in self.cursor.fetchall()]
            total_tables = len(tables)
            # Identify categories by name heuristics
            student_tables = [t for t in tables if 'student' in t.lower()]
            academic_tables = [t for t in tables if 'academic' in t.lower()]
            department_tables = [t for t in tables if 'department' in t.lower() or 'dept' in t.lower()]
            # Build summary
            summary = (
                f"Discovered Tables: total={total_tables}, "
                f"student={len(student_tables)}, academic={len(academic_tables)}, department={len(department_tables)}"
            )
            # Validation logic: must have at least one student table and some data
            if not student_tables:
                return False, f"{summary} – No student tables found"
            # Check that the first discovered student table has rows
            self.cursor.execute(f"SELECT COUNT(*) as c FROM {student_tables[0]}")
            count = self.cursor.fetchone()['c']
            if count == 0:
                return False, f"{summary} – Student table exists but contains no data"
            return True, summary
        except Exception as e:
            return False, f"Validation error: {e}"
            err_str = str(e).lower()
            if "unread result found" in err_str:
                return False, "Internal Validation Query Error: Unread result found. A previous validation query did not consume its results."
            return False, str(e)

    def _safe_execute(self, sql, params=None):
        """
        Failsafe to ensure the ERP Database is strictly Read-Only.
        Blocks any query attempting to modify data.
        """
        forbidden = ['INSERT', 'UPDATE', 'DELETE', 'ALTER', 'DROP', 'TRUNCATE', 'CREATE']
        query_upper = sql.upper()
        if any(keyword in query_upper for keyword in forbidden):
            raise PermissionError("AcaDesk Governance Violation: Attempted a forbidden write operation on the Read-Only ERP Database.")
        
        if params:
            self.cursor.execute(sql, params)
        else:
            self.cursor.execute(sql)

    def _build_alias_map(self):
        """Map logical concept keys to actual column names using discovered columns and synonyms.

        Populates self.map entries for concepts defined in COLUMN_SYNONYMS (e.g., attendance, backlogs, marks, cgpa, student_id).
        """
        # Iterate over each concept and its possible synonym names
        STUDENT_CONCEPTS = {"student_id", "registration_no", "name"}
        for concept, synonyms in self.COLUMN_SYNONYMS.items():
            # Choose appropriate column set based on concept type
            column_set = self.student_columns if concept in STUDENT_CONCEPTS else self.academic_columns
            for synonym in synonyms:
                if synonym in column_set:
                    self.map[concept] = synonym
                    break

    def get_branch_map(self):
        if not self.conn or not self.connected: return {}
        try:
            # Discover department table and name column dynamically
            dept_table = self.map.get('tbl_department')
            if not dept_table:
                return {}
            # Assume department name column is 'name' or contains 'name'
            self.cursor.execute(
                "SELECT COLUMN_NAME FROM information_schema.columns WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                (self.config.get('database'), dept_table)
            )
            cols = [row['COLUMN_NAME'] for row in self.cursor.fetchall()]
            name_col = next((c for c in cols if 'name' in c.lower()), 'name')
            # Assuming branch_id is the standard link
            id_col = next((c for c in cols if 'id' in c.lower()), 'id')
            sql = f"SELECT {id_col}, {name_col} FROM {dept_table}"
            self._safe_execute(sql)
            return {str(r[id_col]): str(r[name_col]).upper() for r in self.cursor.fetchall()}
        except Exception as e:
            print(f"Branch Map Lookup Error: {e}")
            return {}

    def get_all_branches(self):
        return list(self.get_branch_map().keys())

    # Keep your existing get_students and get_all_students...
    def get_all_students(self):
        if not self.conn:
            return []
        try:
            select_parts = []

            # --- Branch ID ---
            join_branch_col = self.map.get('join_branch')
            if join_branch_col and join_branch_col in self.student_columns:
                select_parts.append(f"s.{join_branch_col} AS bid")

            # --- Registration Number (resolved by _build_alias_map) ---
            reg_col = self.map.get('registration_no')
            if reg_col and reg_col in self.student_columns:
                select_parts.append(f"s.{reg_col} AS display_reg_no")

            # --- Student Name (resolved by _build_alias_map) ---
            name_col = self.map.get('name')
            if name_col and name_col in self.student_columns:
                select_parts.append(f"s.{name_col} AS display_name")

            # --- Attendance (resolved by _build_alias_map) ---
            att_col = self.map.get('attendance')
            if att_col and att_col in self.academic_columns:
                select_parts.append(f"a.{att_col} AS att")

            # --- Marks (resolved by _build_alias_map) ---
            marks_col = self.map.get('marks')
            if marks_col and marks_col in self.academic_columns:
                select_parts.append(f"a.{marks_col} AS marks")

            # --- Backlogs (resolved by _build_alias_map) ---
            bkl_col = self.map.get('backlogs')
            if bkl_col and bkl_col in self.academic_columns:
                select_parts.append(f"a.{bkl_col} AS bkl")

            if not select_parts:
                return []

            # Resolve the student_id join column in the academic table
            stu_id_col = self.map.get('join_student', 'student_id')

            select_clause = ", ".join(select_parts)
            sql = f"""
                SELECT {select_clause}
                FROM {self.map['tbl_student']} s
                JOIN (
                    SELECT {stu_id_col}, MAX(semester) AS latest_sem
                    FROM {self.map['tbl_academic']}
                    GROUP BY {stu_id_col}
                ) latest ON s.{self.map['id']} = latest.{stu_id_col}
                JOIN {self.map['tbl_academic']} a ON a.{stu_id_col} = latest.{stu_id_col} AND a.semester = latest.latest_sem
            """
            self._safe_execute(sql)
            rows = []
            for r in self.cursor.fetchall():
                mapped = {
                    "branch": str(r.get('bid')),
                    "avg_attendance": float(r.get('att') or 0.0),
                    "avg_marks": float(r.get('marks') or 0.0),
                    "backlogs": int(r.get('bkl') or 0),
                    "display_reg_no": r.get('display_reg_no'),
                    "display_name": r.get('display_name')
                }
                rows.append(mapped)
            return rows
        except Exception as e:
            print(f"All Students fetch error: {e}")
            return []



    def get_students(self, branch_id, year):
        if not self.conn:
            return []
        try:
            year_val = str(year)[0] if "Year" in str(year) else year

            # Resolve columns via alias map
            join_branch_col = self.map.get('join_branch', 'department_id')
            year_col = self.map.get('year', 'year_id')
            id_col = self.map.get('id', 'id')
            stu_id_col = self.map.get('join_student', 'student_id')
            reg_col = self.map.get('registration_no')
            name_col = self.map.get('name')
            att_col = self.map.get('attendance')
            marks_col = self.map.get('marks')
            bkl_col = self.map.get('backlogs')

            select_parts = []
            if join_branch_col and join_branch_col in self.student_columns:
                select_parts.append(f"s.{join_branch_col} AS bid")
            if reg_col and reg_col in self.student_columns:
                select_parts.append(f"s.{reg_col} AS display_reg_no")
            if name_col and name_col in self.student_columns:
                select_parts.append(f"s.{name_col} AS display_name")
            if att_col and att_col in self.academic_columns:
                select_parts.append(f"a.{att_col} AS satt")
            if marks_col and marks_col in self.academic_columns:
                select_parts.append(f"a.{marks_col} AS smarks")
            if bkl_col and bkl_col in self.academic_columns:
                select_parts.append(f"a.{bkl_col} AS sbkl")

            if not select_parts:
                return []

            select_clause = ", ".join(select_parts)
            sql = f"""
                SELECT {select_clause}
                FROM {self.map['tbl_student']} s
                JOIN (
                    SELECT {stu_id_col}, MAX(semester) AS latest_sem
                    FROM {self.map['tbl_academic']}
                    GROUP BY {stu_id_col}
                ) latest ON s.{id_col} = latest.{stu_id_col}
                JOIN {self.map['tbl_academic']} a ON a.{stu_id_col} = latest.{stu_id_col} AND a.semester = latest.latest_sem
                WHERE s.{join_branch_col} = %s AND s.{year_col} = %s
            """
            self._safe_execute(sql, (branch_id, year_val))
            rows = []
            for r in self.cursor.fetchall():
                rows.append({
                    "display_reg_no": r.get('display_reg_no'),
                    "display_name": r.get('display_name'),
                    "avg_attendance": float(r.get('satt') or 0.0),
                    "avg_marks": float(r.get('smarks') or 0.0),
                    "backlogs": int(r.get('sbkl') or 0)
                })
            return rows
        except Exception as e:
            print(f"Fetch Students Error: {e}")
            return []


    def get_students_full(self, branch_id, year):
        """
        Fetch ALL discovered academic columns for every student in a branch/year.
        Used by the AdvancedRiskPredictor to access the complete feature set.
        Returns a list of raw row dicts with actual ERP column names.
        """
        if not self.conn:
            return []
        try:
            year_val = str(year)[0] if "Year" in str(year) else year

            join_branch_col = self.map.get('join_branch', 'department_id')
            year_col        = self.map.get('year', 'year_id')
            id_col          = self.map.get('id', 'id')
            stu_id_col      = self.map.get('join_student', 'student_id')
            reg_col         = self.map.get('registration_no')
            name_col        = self.map.get('name')

            # Identity columns from student table
            student_select = []
            if join_branch_col and join_branch_col in self.student_columns:
                student_select.append(f"s.{join_branch_col}")
            if reg_col and reg_col in self.student_columns:
                student_select.append(f"s.{reg_col} AS display_reg_no")
            if name_col and name_col in self.student_columns:
                student_select.append(f"s.{name_col} AS display_name")

            # ALL discovered academic columns
            academic_select = [
                f"a.{col}" for col in sorted(self.academic_columns)
                if col not in (stu_id_col, 'semester', 'id')
            ]

            all_select = student_select + academic_select
            if not all_select:
                return []

            select_clause = ", ".join(all_select)
            sql = f"""
                SELECT {select_clause}
                FROM {self.map['tbl_student']} s
                JOIN (
                    SELECT {stu_id_col}, MAX(semester) AS latest_sem
                    FROM {self.map['tbl_academic']}
                    GROUP BY {stu_id_col}
                ) latest ON s.{id_col} = latest.{stu_id_col}
                JOIN {self.map['tbl_academic']} a
                    ON a.{stu_id_col} = latest.{stu_id_col}
                    AND a.semester = latest.latest_sem
                WHERE s.{join_branch_col} = %s AND s.{year_col} = %s
            """
            self._safe_execute(sql, (branch_id, year_val))
            return list(self.cursor.fetchall())
        except Exception:
            return []


class BranchTranslator:
    # Mapping of full department names to abbreviated UI labels
    ABBR_MAP = {
        "Artificial Intelligence and Data Science": "AI_DS",
        "Artificial Intelligence and Machine Learning": "AI_ML",
        "Computer Science and Engineering": "CSE",
        "Cyber Security": "CYBER",
        "Electronics and Communication Engineering": "ECE",
        "Electrical and Electronics Engineering": "EEE",
        "Mechanical Engineering": "MECH",
        "Civil Engineering": "CIVIL",
        "Computer Science and Mathematics": "CSM",
        "Internet of Things": "IOT",
        "Information Technology": "IT",
    }
    def __init__(self, db_handler):
        self.map = {}
        if db_handler:
            self.map = db_handler.get_branch_map()
    def get_name(self, branch_id):
        bid_str = str(branch_id).strip()
        full_name = self.map.get(bid_str, f"Dept {branch_id}")
        return self.ABBR_MAP.get(full_name, full_name)

    def get_sample_data(self):
        """Retrieve sample data for preview.
        Returns a dict with student count, branch count, and up to 3 sample student rows.
        """
        if not self.conn:
            return None
        try:
            # Student count
            self.cursor.execute(f"SELECT COUNT(*) as c FROM {self.map['tbl_student']}")
            student_count = self.cursor.fetchone()['c']
            # Department (branch) count using dynamic department table
            dept_table = self.map.get('tbl_department')
            if not dept_table:
                branch_count = 0
            else:
                self.cursor.execute(f"SELECT COUNT(*) as c FROM {dept_table}")
                branch_count = self.cursor.fetchone()['c']
            # Sample students (first 3) – select ID and name if available
            select_cols = []
            if self.map.get('student_id') in self.student_columns:
                select_cols.append(self.map['student_id'])
            if self.map.get('name') in self.student_columns:
                select_cols.append(self.map['name'])
            if not select_cols:
                return None
            cols_clause = ", ".join(select_cols)
            self.cursor.execute(f"SELECT {cols_clause} FROM {self.map['tbl_student']} LIMIT 3")
            samples = self.cursor.fetchall()
            return {
                "student_count": student_count,
                "branch_count": branch_count,
                "samples": samples
            }
        except Exception as e:
            print(f"Sample Data Error: {e}")
            return None