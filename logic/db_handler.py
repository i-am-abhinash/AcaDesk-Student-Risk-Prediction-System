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
            "tbl_branch": self.config.get("tbl_branch", "branch"),
            "join_student": self.config.get("col_student_join", "student_id"),
            "join_branch": self.config.get("col_branch_join", "branch_id"),
            "id": self.config.get("col_id", "roll_no"),
            "name": self.config.get("col_name", "name"),
            "branch_name": self.config.get("col_branch_name", "branch_name"),
            "year": self.config.get("col_year", "year"),
            "att": self.config.get("col_att", "attendance"),
            "marks": self.config.get("col_marks", "internal_marks"),
            "backlogs": self.config.get("col_backlogs", "backlogs")
        }
        self.connect()

    def connect(self):
        try:
            import mysql.connector
            self.conn = mysql.connector.connect(
                host=self.config.get('host', 'localhost'),
                user=self.config.get('user', 'root'),
                password=self.config.get('password', ''),
                database=self.config.get('database', 'engineering_college'),
                port=int(self.config.get('port', 3306))
            )
            self.cursor = self.conn.cursor(dictionary=True)
            self.connected = True
        except Exception as e:
            print(f"❌ Connection Failed: {e}")

    def get_branch_map(self):
        if not self.conn or not self.connected: return {}
        try:
            # This query was failing because tbl_branch was "none"
            sql = f"SELECT {self.map['join_branch']}, {self.map['branch_name']} FROM {self.map['tbl_branch']}"
            self.cursor.execute(sql)
            return {str(r[self.map['join_branch']]): str(r[self.map['branch_name']]).upper() for r in self.cursor.fetchall()}
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
            sql = f"""
                SELECT s.{self.map['id']} AS sid, s.{self.map['name']} AS sname, 
                       a.{self.map['att']} AS satt, a.{self.map['marks']} AS smarks, a.{self.map['backlogs']} AS sbkl
                FROM {self.map['tbl_student']} s
                JOIN {self.map['tbl_academic']} a ON s.{self.map['join_student']} = a.{self.map['join_student']}
                WHERE s.{self.map['join_branch']} = %s AND s.{self.map['year']} = %s
            """
            self.cursor.execute(sql, (branch_id, year_val))
            return [{
                "id": r['sid'], "name": r['sname'], 
                "avg_attendance": float(r['satt']), "avg_marks": float(r['smarks']), 
                "backlogs": int(r['sbkl'])
            } for r in self.cursor.fetchall()]
        except Exception as e:
            print(f"Fetch Students Error: {e}")
            return []

    def get_all_students(self):
        if not self.conn: return []
        try:
            sql = f"""
                SELECT s.{self.map['join_branch']} AS bid, a.{self.map['att']} AS att, 
                       a.{self.map['marks']} AS marks, a.{self.map['backlogs']} AS bkl
                FROM {self.map['tbl_student']} s
                JOIN {self.map['tbl_academic']} a ON s.{self.map['join_student']} = a.{self.map['join_student']}
            """
            self.cursor.execute(sql)
            return [{"branch": str(r['bid']), "avg_attendance": float(r['att']), 
                     "avg_marks": float(r['marks']), "backlogs": int(r['bkl'])} for r in self.cursor.fetchall()]
        except: return []