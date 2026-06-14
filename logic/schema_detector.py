import mysql.connector

class SchemaDetector:
    def __init__(self, host, port, db, user, pwd):
        self.host = host
        self.port = port
        self.db = db
        self.user = user
        self.pwd = pwd
        self.conn = None
        self.tables = []
        self.columns = {} # table_name -> [{column_name, data_type}]
        self.foreign_keys = [] # [{table, column, ref_table, ref_column}]

    def connect(self):
        try:
            self.conn = mysql.connector.connect(
                host=self.host, 
                port=self.port, 
                database=self.db, 
                user=self.user, 
                password=self.pwd,
                connect_timeout=10
            )
            return True, "Connected successfully"
        except mysql.connector.Error as err:
            return False, f"MySQL Error: {err.msg} (Code: {err.errno})"
        except Exception as e:
            return False, f"Unexpected Connection Error: {str(e)}"

    def scan_schema(self):
        if not self.conn: return False
        cursor = self.conn.cursor(dictionary=True)
        
        # 1. Get Tables
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s", (self.db,))
        self.tables = [row['TABLE_NAME'] for row in cursor.fetchall()]

        # 2. Get Columns
        for table in self.tables:
            cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", (self.db, table))
            self.columns[table] = cursor.fetchall()
            
        # 3. Get Foreign Keys
        fk_sql = """
            SELECT 
                TABLE_NAME as `table`, 
                COLUMN_NAME as `column`, 
                REFERENCED_TABLE_NAME as `ref_table`, 
                REFERENCED_COLUMN_NAME as `ref_column`
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_SCHEMA = %s AND TABLE_SCHEMA = %s
        """
        cursor.execute(fk_sql, (self.db, self.db))
        self.foreign_keys = cursor.fetchall()
        
        cursor.close()
        return True

    def detect_schema(self):
        result = {
            "tbl_student": {"name": None, "confidence": 0, "columns": {}},
            "tbl_academic": {"name": None, "confidence": 0, "columns": {}},
            "tbl_branch": {"name": None, "confidence": 0, "columns": {}}
        }
        
        # Dictionary of tokens
        dicts = {
            "student_tables": ["student", "students", "tbl_student", "student_master"],
            "academic_tables": ["academics", "results", "performance", "marks", "student_academics", "academic_records"],
            "branch_tables": ["branch", "branches", "department", "departments", "tbl_branch"],
            
            "col_student_id": ["student_id", "roll_no", "roll_number", "reg_no", "id"],
            "col_branch_id": ["branch_id", "department_id", "dept_id"],
            "col_name": ["name", "student_name", "full_name"],
            "col_attendance": ["attendance", "attendance_percentage", "attendance_percent", "avg_attendance"],
            "col_marks": ["marks", "cgpa", "internal_marks", "score", "avg_marks"],
            "col_backlogs": ["backlogs", "backlog_count", "failed_subjects"],
            "col_year": ["year", "academic_year", "current_year"],
            "col_email": ["email", "student_email", "mail"],
            
            "col_tenth": ["tenth", "tenth_percentage", "10th", "ssc"],
            "col_inter": ["inter", "intermediate_percentage", "12th", "hsc"],
            "col_diploma": ["diploma", "diploma_percentage"],
            "col_lab": ["lab", "lab_performance", "practical"],
            "col_mid": ["mid", "mid_exam", "mid_exam_score", "internal"],
            "col_cons_abs": ["consecutive_absences", "continuous_absent"],
            "col_leave": ["leave", "leave_frequency", "leaves"],
            "col_p_phone": ["parent_phone", "father_phone", "mother_phone", "guardian_phone", "parent_mobile"],
            "col_p_email": ["parent_email", "guardian_email"]
        }

        # Table matching helper
        def best_table_match(tokens):
            best_table = None
            best_score = 0
            for t in self.tables:
                t_lower = t.lower()
                for token in tokens:
                    if token == t_lower:
                        score = 95
                    elif token in t_lower:
                        score = 80
                    else:
                        continue
                        
                    if score > best_score:
                        best_score = score
                        best_table = t
            return best_table, best_score
            
        student_t, student_s = best_table_match(dicts["student_tables"])
        academic_t, academic_s = best_table_match(dicts["academic_tables"])
        branch_t, branch_s = best_table_match(dicts["branch_tables"])

        # Check FK relations for bonus score
        if student_t and academic_t:
            for fk in self.foreign_keys:
                if (fk["table"] == academic_t and fk["ref_table"] == student_t) or \
                   (fk["table"] == student_t and fk["ref_table"] == academic_t):
                    academic_s = min(100, academic_s + 10)
                    student_s = min(100, student_s + 10)
                    
        if student_t and branch_t:
            for fk in self.foreign_keys:
                if (fk["table"] == student_t and fk["ref_table"] == branch_t) or \
                   (fk["table"] == branch_t and fk["ref_table"] == student_t):
                    branch_s = min(100, branch_s + 10)
                    student_s = min(100, student_s + 10)

        result["tbl_student"] = {"name": student_t, "confidence": student_s, "columns": {}}
        result["tbl_academic"] = {"name": academic_t, "confidence": academic_s, "columns": {}}
        result["tbl_branch"] = {"name": branch_t, "confidence": branch_s, "columns": {}}

        # Column matching helper
        def match_columns(target_table, mapping_keys):
            if not target_table: return
            cols = [c["COLUMN_NAME"].lower() for c in self.columns.get(target_table, [])]
            for map_key in mapping_keys:
                tokens = dicts.get(map_key, [])
                best_col = ""
                best_col_score = 0
                for c in cols:
                    for t in tokens:
                        if t == c:
                            score = 95
                        elif t in c or c in t:
                            score = 75
                        else:
                            continue
                            
                        if score > best_col_score:
                            best_col_score = score
                            best_col = c
                
                # Check cross-table relationships for IDs
                if best_col_score < 50 and 'id' in map_key:
                    # Look at FKs
                    for fk in self.foreign_keys:
                        if fk["table"].lower() == target_table.lower():
                            if map_key == "col_student_id" and fk["ref_table"].lower() == str(student_t).lower():
                                best_col = fk["column"]
                                best_col_score = 90
                            if map_key == "col_branch_id" and fk["ref_table"].lower() == str(branch_t).lower():
                                best_col = fk["column"]
                                best_col_score = 90
                
                # Find which result dict to put it in
                for k, v in result.items():
                    if v["name"] == target_table:
                        v["columns"][map_key] = {"name": best_col, "confidence": best_col_score}

        # Expected mappings
        match_columns(student_t, ["col_student_id", "col_name", "col_branch_id", "col_year", "col_email", "col_p_phone", "col_p_email"])
        match_columns(academic_t, ["col_student_id", "col_attendance", "col_marks", "col_backlogs", "col_tenth", "col_inter", "col_diploma", "col_lab", "col_mid", "col_cons_abs", "col_leave"])
        match_columns(branch_t, ["col_branch_id", "col_name"])
        
        # Resolve 'col_name' conflict by context
        if result["tbl_student"]["name"]:
            result["tbl_student"]["columns"]["join_student"] = result["tbl_student"]["columns"].pop("col_student_id", {"name": "", "confidence": 0})
            result["tbl_student"]["columns"]["join_branch"] = result["tbl_student"]["columns"].pop("col_branch_id", {"name": "", "confidence": 0})
            
        if result["tbl_academic"]["name"]:
            result["tbl_academic"]["columns"]["join_student"] = result["tbl_academic"]["columns"].pop("col_student_id", {"name": "", "confidence": 0})
            
        if result["tbl_branch"]["name"]:
            result["tbl_branch"]["columns"]["col_branch_name"] = result["tbl_branch"]["columns"].pop("col_name", {"name": "", "confidence": 0})
            result["tbl_branch"]["columns"]["join_branch"] = result["tbl_branch"]["columns"].pop("col_branch_id", {"name": "", "confidence": 0})

        return result
