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
        self.map = {
            "tbl_student": self.config.get("tbl_student", "student"),
            "tbl_academic": self.config.get("tbl_academic", "academics"),
            "tbl_history": self.config.get("tbl_history", "academic_history"),
            "tbl_branch": self.config.get("tbl_branch", "branch"),
            "join_student": self.config.get("col_student_join", "student_id"),
            "join_branch": self.config.get("col_branch_join", "branch_id"),
            "col_semester": self.config.get("col_semester", "semester"),
            "id": self.config.get("col_id", "roll_no"),
            "name": self.config.get("col_name", "name"),
            "branch_name": self.config.get("col_branch_name", "branch_name"),
            "year": self.config.get("col_year", "year"),
            "att": self.config.get("col_att", "attendance"),
            "marks": self.config.get("col_marks", "internal_marks"),
            "cgpa": self.config.get("col_cgpa", "cgpa"),
            "backlogs": self.config.get("col_backlogs", "backlogs"),
            "tenth": self.config.get("col_tenth", "tenth_percentage"),
            "inter": self.config.get("col_inter", "intermediate_percentage"),
            "diploma": self.config.get("col_diploma", "diploma_percentage"),
            "lab_perf": self.config.get("col_lab_perf", "lab_performance"),
            "mid_exam": self.config.get("col_mid_exam", "mid_exam_score"),
            "cons_abs": self.config.get("col_cons_abs", "consecutive_absences"),
            "leave_freq": self.config.get("col_leave_freq", "leave_frequency"),
            "assign_marks": self.config.get("col_assign_marks", "assignment_marks"),
            "parent_phone": self.config.get("col_parent_phone", "parent_phone"),
            "parent_email": self.config.get("col_p_email"),
            "email": self.config.get("col_email")
        }
        self.connect()

    def connect(self):
        host = self.config.get('host', 'localhost')
        user = self.config.get('user', 'root')
        password = self.config.get('password', '')
        database = self.config.get('database', 'engineering_college')
        port = int(self.config.get('port', 3306))

        if not password:
            print(f"❌ ERP Connection Warning: No password provided for user '{user}' on {host}")
            # We still try to connect because some local dev environments might not have a password
            # but we log it clearly.

        try:
            import mysql.connector
            self.conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port,
                connect_timeout=10
            )
            self.cursor = self.conn.cursor(dictionary=True)
            self.connected = True
        except mysql.connector.Error as err:
            print(f"❌ ERP Database Connection Failed: {err.msg} (Code: {err.errno})")
            if err.errno == 1045:
                print(f"   Hint: Access denied for '{user}'@'{host}'. Please verify ERP database credentials.")
            self.connected = False
        except Exception as e:
            print(f"❌ ERP Unexpected Connection Error: {e}")
            self.connected = False

    def close(self):
        if self.cursor:
            try: self.cursor.close()
            except: pass
        if self.conn:
            try: self.conn.close()
            except: pass
        self.connected = False

    def validate_tables(self):
        if not self.conn or not self.connected:
            return False, "Not connected to database."
        try:
            self.cursor.execute("SHOW TABLES")
            tables = [r[list(r.keys())[0]].lower() for r in self.cursor.fetchall()]
            
            missing = []
            if self.map['tbl_student'].lower() not in tables: missing.append(self.map['tbl_student'])
            if self.map['tbl_academic'].lower() not in tables: missing.append(self.map['tbl_academic'])
            if self.map['tbl_branch'].lower() not in tables: missing.append(self.map['tbl_branch'])
            
            if missing:
                return False, f"Missing configured tables: {', '.join(missing)}"
            return True, "Valid"
        except Exception as e:
            return False, f"Error validating tables: {e}"

    def get_branch_map(self):
        if not self.conn or not self.connected: return {}
        try:
            # Assumes the branch table's primary key is 'id' and the student table's foreign key is join_branch
            sql = f"SELECT id, {self.map['branch_name']} FROM {self.map['tbl_branch']}"
            self.cursor.execute(sql)
            return {str(r['id']): str(r[self.map['branch_name']]).upper() for r in self.cursor.fetchall()}
        except Exception as e:
            print(f"Branch Map Lookup Error: {e}")
            return {}

    def get_all_branches(self):
        return list(self.get_branch_map().keys())

    # Keep your existing get_students and get_all_students...

    def get_students(self, branch_id, year):
        if not self.conn: return []
        try:
            year_val = str(year)[0] if "Year" in str(year) else year
            sql_select = f"s.{self.map['id']} AS sid, s.{self.map['name']} AS sname, s.{self.map['year']} AS syear, a.{self.map['att']} AS satt, a.{self.map['marks']} AS smarks, a.{self.map['backlogs']} AS sbkl"
            if self.map['tenth']: sql_select += f", a.{self.map['tenth']} AS stenth"
            if self.map['inter']: sql_select += f", a.{self.map['inter']} AS sinter"
            if self.map['diploma']: sql_select += f", a.{self.map['diploma']} AS sdiploma"
            if self.map['lab_perf']: sql_select += f", a.{self.map['lab_perf']} AS slab"
            if self.map['mid_exam']: sql_select += f", a.{self.map['mid_exam']} AS smid"
            if self.map['cons_abs']: sql_select += f", a.{self.map['cons_abs']} AS scons_abs"
            if self.map['leave_freq']: sql_select += f", a.{self.map['leave_freq']} AS sleave_freq"
            sql_select += f", a.{self.map['cgpa']} AS scgpa, a.{self.map['assign_marks']} AS sassign"
            if self.map['parent_phone']: sql_select += f", s.{self.map['parent_phone']} AS sparent_phone"
            if self.map['parent_email']: sql_select += f", s.{self.map['parent_email']} AS sparent_email"
            if self.map.get('email'): sql_select += f", s.{self.map['email']} AS semail"

            # Robust Year Matching
            numeric_year = 0
            y_str = str(year_val).lower()
            if '1' in y_str or 'first' in y_str: numeric_year = 1
            elif '2' in y_str or 'second' in y_str: numeric_year = 2
            elif '3' in y_str or 'third' in y_str: numeric_year = 3
            elif '4' in y_str or 'fourth' in y_str: numeric_year = 4

            sql = f"""
                SELECT {sql_select}
                FROM {self.map['tbl_student']} s
                LEFT JOIN (
                    SELECT * FROM {self.map['tbl_academic']}
                    WHERE id IN (
                        SELECT MAX(id) FROM {self.map['tbl_academic']} GROUP BY {self.map['join_student']}
                    )
                ) a ON s.id = a.{self.map['join_student']}
                WHERE s.{self.map['join_branch']} = %s 
                  AND (s.{self.map['year']} = %s OR s.{self.map['year']} = %s OR s.{self.map['year']} = %s)
            """
            
            with open('debug_filter.txt', 'a', encoding='utf-8') as f:
                f.write(f"SQL: {sql}\nArgs: ({branch_id}, {year_val}, {numeric_year}, {str(numeric_year)})\n")
                
            self.cursor.execute(sql, (branch_id, year_val, numeric_year, str(numeric_year)))
            
            results = []
            for r in self.cursor.fetchall():
                student_data = {
                    "id": r['sid'], 
                    "name": r['sname'], 
                    "year": str(r['syear']),
                    "avg_attendance": float(r['satt']) if r['satt'] is not None else 0.0, 
                    "avg_marks": float(r['smarks']) if r['smarks'] is not None else 0.0, 
                    "backlogs": int(r['sbkl']) if r['sbkl'] is not None else 0
                }
                if 'stenth' in r: student_data['tenth'] = float(r['stenth']) if r['stenth'] is not None else None
                if 'sinter' in r: student_data['inter'] = float(r['sinter']) if r['sinter'] is not None else None
                if 'sdiploma' in r: student_data['diploma'] = float(r['sdiploma']) if r['sdiploma'] is not None else None
                
                if 'slab' in r: student_data['lab_performance'] = float(r['slab']) if r['slab'] is not None else None
                if 'smid' in r: student_data['mid_exam_score'] = float(r['smid']) if r['smid'] is not None else None
                if 'scons_abs' in r: student_data['consecutive_absences'] = int(r['scons_abs']) if r['scons_abs'] is not None else None
                if 'sleave_freq' in r: student_data['leave_frequency'] = int(r['sleave_freq']) if r['sleave_freq'] is not None else None
                if 'scgpa' in r: student_data['cgpa'] = float(r['scgpa']) if r['scgpa'] is not None else None
                if 'sassign' in r: student_data['assignment_marks'] = float(r['sassign']) if r['sassign'] is not None else None
                
                if 'sparent_phone' in r: student_data['parent_phone'] = r['sparent_phone']
                if 'sparent_email' in r: student_data['parent_email'] = r['sparent_email']
                if 'semail' in r: student_data['email'] = r['semail']
                
                results.append(student_data)
                
            return results
        except Exception as e:
            with open('debug_filter.txt', 'a', encoding='utf-8') as f:
                f.write(f"Fetch Students Error: {e}\n")
            print(f"Fetch Students Error: {e}")
            return []

    def get_all_students(self):
        if not self.conn: return []
        try:
            sql_select = f"s.{self.map['id']} AS sid, s.{self.map['join_branch']} AS bid, s.{self.map['year']} AS syear, a.{self.map['att']} AS att, a.{self.map['marks']} AS marks, a.{self.map['backlogs']} AS bkl"
            if self.map['tenth']: sql_select += f", a.{self.map['tenth']} AS stenth"
            if self.map['inter']: sql_select += f", a.{self.map['inter']} AS sinter"
            if self.map['diploma']: sql_select += f", a.{self.map['diploma']} AS sdiploma"
            if self.map['lab_perf']: sql_select += f", a.{self.map['lab_perf']} AS slab"
            if self.map['mid_exam']: sql_select += f", a.{self.map['mid_exam']} AS smid"
            if self.map['cons_abs']: sql_select += f", a.{self.map['cons_abs']} AS scons_abs"
            if self.map['leave_freq']: sql_select += f", a.{self.map['leave_freq']} AS sleave_freq"
            sql_select += f", a.{self.map['cgpa']} AS scgpa, a.{self.map['assign_marks']} AS sassign"
            if self.map['email']: sql_select += f", s.{self.map['email']} AS semail"
            if self.map['parent_email']: sql_select += f", s.{self.map['parent_email']} AS sparent_email"

            sql = f"""
                SELECT {sql_select}
                FROM {self.map['tbl_student']} s
                LEFT JOIN (
                    SELECT * FROM {self.map['tbl_academic']}
                    WHERE id IN (
                        SELECT MAX(id) FROM {self.map['tbl_academic']} GROUP BY {self.map['join_student']}
                    )
                ) a ON s.id = a.{self.map['join_student']}
            """
            self.cursor.execute(sql)
            
            results = []
            for r in self.cursor.fetchall():
                sd = {
                    "id": r.get('sid'),
                    "display_reg_no": r.get('sid'),
                    "registration_no": r.get('sid'),
                    "branch": str(r['bid']), 
                    "syear": str(r.get('syear', '')),
                    "year": str(r.get('syear', '')),
                    "avg_attendance": float(r['att']) if r['att'] is not None else 0.0, 
                    "avg_marks": float(r['marks']) if r['marks'] is not None else 0.0, 
                    "backlogs": int(r['bkl']) if r['bkl'] is not None else 0,
                    "tenth": float(r['stenth']) if r.get('stenth') is not None else 0.0,
                    "inter": float(r['sinter']) if r.get('sinter') is not None else 0.0,
                    "diploma": float(r['sdiploma']) if r.get('sdiploma') is not None else 0.0,
                    "lab_performance": float(r['slab']) if r.get('slab') is not None else 0.0,
                    "mid_exam_score": float(r['smid']) if r.get('smid') is not None else 0.0,
                    "consecutive_absences": int(r['scons_abs']) if r.get('scons_abs') is not None else 0,
                    "leave_frequency": int(r['sleave_freq']) if r.get('sleave_freq') is not None else 0,
                    "cgpa": float(r['scgpa']) if r.get('scgpa') is not None else 0.0,
                    "assignment_marks": float(r['sassign']) if r.get('sassign') is not None else 0.0
                }
                if 'semail' in r: sd['email'] = r['semail']
                if 'sparent_email' in r: sd['parent_email'] = r['sparent_email']
                results.append(sd)
            return results
        except Exception as e: 
            print(f"Fetch All Students Error: {e}")
            return []

    def get_training_data(self):
        if not self.conn: return []
        try:
            sql_select = f"a.{self.map['att']} AS att, a.{self.map['marks']} AS marks, a.{self.map['backlogs']} AS bkl"
            if self.map['tenth']: sql_select += f", a.{self.map['tenth']} AS stenth"
            if self.map['inter']: sql_select += f", a.{self.map['inter']} AS sinter"
            if self.map['diploma']: sql_select += f", a.{self.map['diploma']} AS sdiploma"
            if self.map['lab_perf']: sql_select += f", a.{self.map['lab_perf']} AS slab"
            if self.map['mid_exam']: sql_select += f", a.{self.map['mid_exam']} AS smid"
            if self.map['cons_abs']: sql_select += f", a.{self.map['cons_abs']} AS scons_abs"
            if self.map['leave_freq']: sql_select += f", a.{self.map['leave_freq']} AS sleave_freq"
            sql_select += f", a.{self.map['cgpa']} AS scgpa, a.{self.map['assign_marks']} AS sassign"

            sql = f"""
                SELECT {sql_select}
                FROM {self.map['tbl_academic']} a
                JOIN {self.map['tbl_student']} s ON s.id = a.{self.map['join_student']}
            """
            self.cursor.execute(sql)
            
            results = []
            for r in self.cursor.fetchall():
                sd = {
                    "avg_attendance": float(r['att']) if r['att'] is not None else 0.0, 
                    "avg_marks": float(r['marks']) if r['marks'] is not None else 0.0, 
                    "backlogs": int(r['bkl']) if r['bkl'] is not None else 0,
                    "tenth": float(r['stenth']) if r.get('stenth') is not None else 0.0,
                    "inter": float(r['sinter']) if r.get('sinter') is not None else 0.0,
                    "diploma": float(r['sdiploma']) if r.get('sdiploma') is not None else 0.0,
                    "lab_performance": float(r['slab']) if r.get('slab') is not None else 0.0,
                    "mid_exam_score": float(r['smid']) if r.get('smid') is not None else 0.0,
                    "consecutive_absences": int(r['scons_abs']) if r.get('scons_abs') is not None else 0,
                    "leave_frequency": int(r['sleave_freq']) if r.get('sleave_freq') is not None else 0,
                    "cgpa": float(r['scgpa']) if r.get('scgpa') is not None else 0.0,
                    "assignment_marks": float(r['sassign']) if r.get('sassign') is not None else 0.0
                }
                results.append(sd)
            return results
        except Exception as e: 
            print(f"Fetch Training Data Error: {e}")
            return []

    def get_student_history(self, student_id):
        if not self.conn: return []
        
        # Try fetching real data first
        try:
            sql = f"""
                SELECT a.semester,
                       a.cgpa,
                       a.attendance_percentage AS att,
                       a.backlog_count AS bkl
                FROM {self.map['tbl_academic']} a
                JOIN {self.map['tbl_student']} s ON a.{self.map['join_student']} = s.id
                WHERE s.{self.map['id']} = %s
                ORDER BY a.semester ASC
            """
            self.cursor.execute(sql, (student_id,))
            records = self.cursor.fetchall()
            if records:
                return [{"semester": int(r['semester']), "cgpa": float(r['cgpa']),
                         "attendance": float(r['att']), "backlogs": int(r['bkl'])} for r in records]
        except Exception as e:
            # Silently ignore the error since we expect the table to be missing in some ERPs
            print(f"Error fetching academic_records: {e}")
            pass
            
        return []

    def get_interventions(self, student_id):
        if not self.conn: return []
        try:
            sql = "SELECT id, recommendation_text, priority, status, reason, date_created FROM interventions WHERE student_id = %s ORDER BY priority ASC, date_created DESC"
            self.cursor.execute(sql, (student_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching interventions: {e}")
            return []

    def save_intervention(self, student_id, text, priority, status, reason):
        if not self.conn: return False
        try:
            sql = "INSERT INTO interventions (student_id, recommendation_text, priority, status, reason) VALUES (%s, %s, %s, %s, %s)"
            self.cursor.execute(sql, (student_id, text, priority, status, reason))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error saving intervention: {e}")
            return None

    def update_intervention_status(self, intervention_id, status):
        if not self.conn: return False
        try:
            sql = "UPDATE interventions SET status = %s WHERE id = %s"
            self.cursor.execute(sql, (status, intervention_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating intervention status: {e}")
            return False
    def save_monthly_snapshot(self, branch_id, month_str, health_score, att_avg, cgpa_avg, risk_dist):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monthly_trends (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    branch_id VARCHAR(50),
                    snapshot_month VARCHAR(20),
                    health_score FLOAT,
                    att_avg FLOAT,
                    cgpa_avg FLOAT,
                    high_risk INT,
                    med_risk INT,
                    low_risk INT,
                    UNIQUE KEY unique_snapshot (branch_id, snapshot_month)
                )
            """)
            self.conn.commit()
            
            cursor.execute("""
                INSERT INTO monthly_trends (branch_id, snapshot_month, health_score, att_avg, cgpa_avg, high_risk, med_risk, low_risk)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    health_score=VALUES(health_score), 
                    att_avg=VALUES(att_avg), 
                    cgpa_avg=VALUES(cgpa_avg),
                    high_risk=VALUES(high_risk),
                    med_risk=VALUES(med_risk),
                    low_risk=VALUES(low_risk)
            """, (branch_id, month_str, health_score, att_avg, cgpa_avg, risk_dist.get('High', 0), risk_dist.get('Medium', 0), risk_dist.get('Low', 0)))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving monthly snapshot: {e}")
            return False
            
    def get_monthly_trends(self, branch_id=None):
        try:
            cursor = self.conn.cursor(dictionary=True)
            if branch_id:
                cursor.execute("SELECT * FROM monthly_trends WHERE branch_id=%s ORDER BY snapshot_month ASC", (branch_id,))
            else:
                cursor.execute("SELECT * FROM monthly_trends ORDER BY snapshot_month ASC")
            return cursor.fetchall()
        except:
            return []

    def initialize_notes_table(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faculty_notes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id VARCHAR(50),
                    faculty_username VARCHAR(100),
                    department VARCHAR(50),
                    note_text TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'Active'
                )
            """)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error initializing faculty_notes: {e}")
            return False

    def create_note(self, student_id, faculty_username, department, note_text):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO faculty_notes (student_id, faculty_username, department, note_text)
                VALUES (%s, %s, %s, %s)
            """, (student_id, faculty_username, department, note_text))
            self.conn.commit()
            return True, "Note Saved Successfully"
        except Exception as e:
            return False, str(e)

    def update_note(self, note_id, note_text):
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE faculty_notes SET note_text=%s WHERE id=%s", (note_text, note_id))
            self.conn.commit()
            return True, "Note Updated"
        except Exception as e:
            return False, str(e)

    def delete_note(self, note_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM faculty_notes WHERE id=%s", (note_id,))
            self.conn.commit()
            return True, "Note Deleted"
        except Exception as e:
            return False, str(e)

    def get_student_notes(self, student_id):
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM faculty_notes WHERE student_id=%s ORDER BY created_at DESC", (student_id,))
            return cursor.fetchall()
        except:
            return []
            
    def get_all_notes_filtered(self, department=None):
        try:
            cursor = self.conn.cursor(dictionary=True)
            if department:
                cursor.execute("SELECT * FROM faculty_notes WHERE department=%s ORDER BY created_at DESC", (department,))
            else:
                cursor.execute("SELECT * FROM faculty_notes ORDER BY created_at DESC")
            return cursor.fetchall()
        except:
            return []
