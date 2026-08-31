import logging
from typing import Dict, List, Tuple

_log = logging.getLogger(__name__)

class IntelligentDetector:
    def __init__(self, host: str, port: int, db: str, user: str, pwd: str):
        self.host = host
        self.port = int(port)
        self.db = db
        self.user = user
        self.pwd = pwd
        self.conn = None
        self.schema_graph = {"tables": {}, "fk_pairs": set()}

    def connect(self) -> Tuple[bool, str]:
        try:
            import mysql.connector
            self.conn = mysql.connector.connect(
                host=self.host, port=self.port, database=self.db,
                user=self.user, password=self.pwd, connect_timeout=10
            )
            return True, "Connected successfully"
        except Exception as e:
            _log.error(f"Connect failed: {e}")
            return False, str(e)

    def disconnect(self):
        if self.conn:
            try:
                self.conn.close()
            except: pass
            self.conn = None

    def lightweight_scan(self) -> dict:
        """
        Extracts metadata and scores tables for Student, Academic, Attendance, Dept.
        Returns:
            {
                "tables": [list of all tables],
                "suggestions": {
                    "tbl_student": "student_master",
                    "tbl_academic": "results",
                    "tbl_attendance": "attendance",
                    "tbl_branch": "departments"
                }
            }
        """
        if not self.conn: return {}
        cursor = self.conn.cursor(dictionary=True)
        
        # 1. Fetch tables
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_ROWS
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
        """, (self.db,))
        for row in cursor.fetchall():
            tname = row["TABLE_NAME"]
            self.schema_graph["tables"][tname] = {
                "rows": row["TABLE_ROWS"] or 0,
                "columns": {}, "primary_keys": [], "foreign_keys": []
            }
            
        # 2. Fetch columns
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
        """, (self.db,))
        for row in cursor.fetchall():
            tname = row["TABLE_NAME"]
            if tname in self.schema_graph["tables"]:
                cname = row["COLUMN_NAME"]
                self.schema_graph["tables"][tname]["columns"][cname.lower()] = {
                    "name": cname, "data_type": row["DATA_TYPE"], "key": row["COLUMN_KEY"]
                }
        cursor.close()

        # Score tables
        role_scores = {"tbl_student": [], "tbl_academic": [], "tbl_attendance": [], "tbl_branch": []}
        
        for tname, tdata in self.schema_graph["tables"].items():
            t_lower = tname.lower()
            cols = set(tdata["columns"].keys())
            
            # Score student
            s_score = 0
            if "student" in t_lower or "profile" in t_lower or "master" in t_lower: s_score += 20
            if any(c in cols for c in ["student_id", "roll_no", "reg_no", "enrollment_no"]): s_score += 30
            if any(c in cols for c in ["name", "first_name", "full_name"]): s_score += 20
            if s_score > 0: role_scores["tbl_student"].append((s_score, tname))
            
            # Score academic
            a_score = 0
            if "result" in t_lower or "academic" in t_lower or "mark" in t_lower or "exam" in t_lower: a_score += 20
            if any(c in cols for c in ["cgpa", "sgpa", "gpa", "marks", "grade", "percentage", "backlogs"]): a_score += 30
            if a_score > 0: role_scores["tbl_academic"].append((a_score, tname))
                
            # Score attendance
            att_score = 0
            if "attend" in t_lower or "absence" in t_lower: att_score += 30
            if any(c in cols for c in ["present", "absent", "total_class", "attendance_pct", "status"]): att_score += 30
            if att_score > 0: role_scores["tbl_attendance"].append((att_score, tname))
                
            # Score branch
            b_score = 0
            if "branch" in t_lower or "dept" in t_lower or "department" in t_lower or "program" in t_lower: b_score += 30
            if any(c in cols for c in ["branch_name", "dept_name", "program_name", "course_name"]): b_score += 30
            if b_score > 0: role_scores["tbl_branch"].append((b_score, tname))
                
        suggestions = {}
        for role, scores in role_scores.items():
            if scores:
                scores.sort(key=lambda x: x[0], reverse=True)
                suggestions[role] = scores[0][1]
            else:
                suggestions[role] = ""
                
        return {
            "tables": sorted(list(self.schema_graph["tables"].keys())),
            "suggestions": suggestions
        }

    def deep_discover(self, confirmed_tables: dict) -> dict:
        """
        Discovers PK/FK relationships and maps columns for the confirmed tables.
        Returns the flat mapping expected by central_auth and data_retrieval.
        """
        if not self.conn: return {}
        cursor = self.conn.cursor(dictionary=True)
        
        # 1. Fetch explicit Foreign Keys across selected tables
        cursor.execute("""
            SELECT TABLE_NAME as child_table, COLUMN_NAME as child_column,
                   REFERENCED_TABLE_NAME as parent_table, REFERENCED_COLUMN_NAME as parent_column
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL
        """, (self.db,))
        for row in cursor.fetchall():
            ctable = row["child_table"]
            if ctable in self.schema_graph["tables"]:
                self.schema_graph["tables"][ctable]["foreign_keys"].append(row)
        cursor.close()

        tbl_student = confirmed_tables.get("tbl_student", "")
        tbl_academic = confirmed_tables.get("tbl_academic", "")
        tbl_branch = confirmed_tables.get("tbl_branch", "")
        tbl_attendance = confirmed_tables.get("tbl_attendance", "")

        mapping = {
            "strategy": "INTELLIGENT_ADAPTER",
            "tbl_student": tbl_student,
            "tbl_academic": tbl_academic,
            "tbl_branch": tbl_branch,
            "tbl_attendance": tbl_attendance,
            "mapping_extensions": {},
            "extended_features": []
        }

        # Helper to find column by synonyms
        def find_col(table, synonyms):
            if not table or table not in self.schema_graph["tables"]: return ""
            tcols = self.schema_graph["tables"][table]["columns"]
            for syn in synonyms:
                if syn in tcols: return tcols[syn]["name"]
            return ""

        # Map Core Columns for Student
        mapping["col_id"] = find_col(tbl_student, ["student_id", "roll_no", "reg_no", "id", "usn"])
        mapping["col_name"] = find_col(tbl_student, ["name", "full_name", "first_name", "student_name"])
        mapping["col_email"] = find_col(tbl_student, ["email", "email_id", "student_email"])
        mapping["col_parent_phone"] = find_col(tbl_student, ["parent_phone", "father_phone", "guardian_phone"])
        mapping["col_parent_email"] = find_col(tbl_student, ["parent_email", "father_email", "guardian_email"])
        mapping["col_year"] = find_col(tbl_student, ["current_year", "year", "academic_year", "semester"])

        # Map Branch Columns
        mapping["col_branch_pk"] = find_col(tbl_branch, ["branch_id", "dept_id", "department_id", "program_id", "id"])
        mapping["col_branch_name"] = find_col(tbl_branch, ["branch_name", "name", "dept_name", "department_name", "program_name"])

        # Map Academic Columns
        mapping["col_cgpa"] = find_col(tbl_academic, ["cgpa", "gpa", "overall_cgpa"])
        mapping["col_marks"] = find_col(tbl_academic, ["internal_marks", "marks", "total_marks", "score"])
        mapping["col_backlogs"] = find_col(tbl_academic, ["backlogs", "arrears", "failed_subjects"])
        mapping["col_tenth"] = find_col(tbl_academic, ["tenth_marks", "ssc_marks", "tenth_pct"])
        mapping["col_inter"] = find_col(tbl_academic, ["inter_marks", "hsc_marks", "twelfth_pct"])
        mapping["col_diploma"] = find_col(tbl_academic, ["diploma_marks", "diploma_pct"])
        mapping["col_lab_perf"] = find_col(tbl_academic, ["lab_performance", "lab_marks"])
        mapping["col_mid_exam"] = find_col(tbl_academic, ["mid_exam", "mid_marks"])
        mapping["col_assign_marks"] = find_col(tbl_academic, ["assignment_marks", "assignments"])

        # Map Attendance Columns
        mapping["col_att"] = find_col(tbl_attendance, ["attendance_pct", "attendance", "percentage"])
        mapping["col_cons_abs"] = find_col(tbl_attendance, ["consecutive_absences", "continuous_absent"])
        mapping["col_leave_freq"] = find_col(tbl_attendance, ["leave_frequency", "leaves"])

        # Find Joins (Heuristic + Explicit)
        def find_join(child_tbl, parent_tbl):
            if not child_tbl or not parent_tbl: return ""
            # Check explicit FK
            for fk in self.schema_graph["tables"][child_tbl]["foreign_keys"]:
                if fk["parent_table"] == parent_tbl:
                    return fk["child_column"]
            # Check Heuristic
            p_cols = self.schema_graph["tables"][parent_tbl]["columns"]
            c_cols = self.schema_graph["tables"][child_tbl]["columns"]
            
            common_keys = ["student_id", "roll_no", "reg_no"]
            if parent_tbl == tbl_branch: common_keys = ["branch_id", "dept_id", "department_id", "program_id"]
            
            for k in common_keys:
                if k in c_cols and (k in p_cols or "id" in p_cols):
                    return c_cols[k]["name"]
            
            # Additional heuristic: maybe the child table has a column exactly matching parent table name + "_id"
            pid_name = f"{parent_tbl}_id"
            if pid_name in c_cols: return c_cols[pid_name]["name"]
            
            return ""

        mapping["col_academic_join"] = find_join(tbl_academic, tbl_student)
        mapping["col_branch_join"] = find_join(tbl_student, tbl_branch)
        mapping["col_attendance_join"] = find_join(tbl_attendance, tbl_student)

        # Map join column in Central configs (backward compatibility)
        mapping["col_student_join"] = mapping["col_academic_join"]

        # Extended Features (Any numeric column not mapped)
        known_mapped = set([mapping[k].lower() for k in mapping if k.startswith("col_") and mapping[k]])
        
        for tbl in [tbl_student, tbl_academic, tbl_attendance]:
            if not tbl or tbl not in self.schema_graph["tables"]: continue
            for c_lower, c_info in self.schema_graph["tables"][tbl]["columns"].items():
                if c_lower not in known_mapped and "id" not in c_lower and "date" not in c_lower and "time" not in c_lower:
                    dt = c_info["data_type"].lower()
                    if "int" in dt or "float" in dt or "decimal" in dt or "double" in dt:
                        mapping["extended_features"].append({
                            "table": tbl,
                            "column": c_info["name"],
                            "type": dt
                        })

        return mapping
