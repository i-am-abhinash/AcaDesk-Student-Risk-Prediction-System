import mysql.connector
from logic.encryption import hash_password, encrypt_text, decrypt_text

class CentralAuth:
    def __init__(self):
        self.config = {
            "host": "localhost",
            "user": "root",
            "password": "Abhinash@19",
            "database": "acadesk_central"
        }

    def _get_conn(self):
        try: return mysql.connector.connect(**self.config)
        except: return None

    def register_admin(self, college_name, username, password):
        conn = self._get_conn()
        if not conn: return False, "Server Offline"
        try:
            cursor = conn.cursor()
            
            # CHECK 1: Ensure the username is unique across the entire system
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            if cursor.fetchone(): 
                return False, "Username is already taken. Please choose another."

            # CHECK 2: Ensure only one Administrator can exist per college
            # We check if any user with the 'Admin' role is already linked to this college name
            cursor.execute("SELECT * FROM users WHERE college_name=%s AND role='Admin'", (college_name,))
            if cursor.fetchone(): 
                return False, f"Registration Blocked: An Administrator is already registered for '{college_name}'."

            # If both checks pass, proceed with registration
            hashed = hash_password(password)
            cursor.execute("INSERT INTO users (username, password_hash, role, college_name) VALUES (%s, %s, 'Admin', %s)", 
                           (username, hashed, college_name))
            conn.commit()
            return True, "Registration Successful"
        except Exception as e: 
            return False, str(e)
        finally:
            if conn: conn.close()

    def add_faculty(self, admin_username, faculty_user, faculty_pass, branch_id):
        conn = self._get_conn()
        if not conn: return False, "Server Offline"
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT college_name FROM users WHERE username=%s", (admin_username,))
            admin = cursor.fetchone()
            if not admin: return False, "Admin not found"
            
            hashed = hash_password(faculty_pass)
            cursor.execute("INSERT INTO users (username, password_hash, role, college_name, added_by, assigned_branch) VALUES (%s, %s, 'Faculty', %s, %s, %s)",
                           (faculty_user, hashed, admin['college_name'], admin_username, branch_id))
            conn.commit()
            return True, "Faculty Added"
        except Exception as e: return False, str(e)
        finally:
            if conn: conn.close()

    def get_faculty_list(self, college_name):
        conn = self._get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT username, assigned_branch FROM users WHERE college_name=%s AND role='Faculty'", (college_name,))
            return cursor.fetchall()
        except: return []
        finally:
            if conn: conn.close()

    def revoke_faculty(self, username, college_name):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username=%s AND college_name=%s AND role='Faculty'", (username, college_name))
            conn.commit()
            return True
        except: return False
        finally:
            if conn: conn.close()

    def login(self, username, password):
        conn = self._get_conn()
        if not conn: return None, "Server Offline"
        try:
            cursor = conn.cursor(dictionary=True)
            hashed = hash_password(password)
            
            cursor.execute("SELECT * FROM users WHERE username=%s AND password_hash=%s", (username, hashed))
            user = cursor.fetchone()
            if not user: return None, "Invalid Credentials"

            cursor.execute("SELECT * FROM erp_configs WHERE college_name=%s", (user['college_name'],))
            erp = cursor.fetchone()

            config = None
            if erp:
                # WE MUST MAP EVERY SINGLE MULTI-TABLE COLUMN HERE
                config = {
                    "db_type": erp['db_type'], "host": erp['db_host'], "port": erp['db_port'],
                    "user": erp['db_user'], "password": decrypt_text(erp['encrypted_pass']),
                    "database": erp['db_name'],
                    
                    "tbl_student": erp['tbl_student'], "tbl_academic": erp['tbl_academic'], 
                    "tbl_branch": erp['tbl_branch'],
                    "col_student_join": erp['col_student_join'], "col_branch_join": erp['col_branch_join'],
                    
                    "col_id": erp['col_id'], "col_name": erp['col_name'],
                    "col_branch_name": erp['col_branch_name'], "col_year": erp['col_year'],
                    "col_email": erp['col_email'], "col_att": erp['col_att'],
                    "col_marks": erp['col_marks'], "col_backlogs": erp['col_backlogs']
                }
            return {"user": user, "erp_config": config}, "Success"
        finally:
            conn.close()

    def save_erp_config(self, college, db_type, host, port, db_name, db_user, db_pass, m):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            enc_p = encrypt_text(db_pass)
            sql = """INSERT INTO erp_configs (college_name, db_type, db_host, db_port, db_name, db_user, encrypted_pass, 
                     tbl_student, tbl_academic, tbl_branch, col_student_join, col_branch_join, 
                     col_id, col_name, col_branch_name, col_year, col_email, col_att, col_marks, col_backlogs)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                     ON DUPLICATE KEY UPDATE db_type=VALUES(db_type), db_host=VALUES(db_host), encrypted_pass=VALUES(encrypted_pass),
                     tbl_branch=VALUES(tbl_branch), col_branch_name=VALUES(col_branch_name)"""
            cursor.execute(sql, (college, db_type, host, port, db_name, db_user, enc_p,
                                m['tbl_student'], m['tbl_academic'], m['tbl_branch'], 
                                m['col_student_join'], m['col_branch_join'],
                                m['col_id'], m['col_name'], m['col_branch_name'], m['col_year'],
                                m['col_email'], m['col_att'], m['col_marks'], m['col_backlogs']))
            conn.commit()
            return True
        finally:
            conn.close()