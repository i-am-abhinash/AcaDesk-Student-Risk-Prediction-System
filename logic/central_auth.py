import mysql.connector
from logic.encryption import hash_password, encrypt_text, decrypt_text
from logic.central_db_handler import CentralDBHandler
from logic.config_manager import load_config

class CentralAuth:
    def __init__(self):
        cfg = load_config().get("central", {})
        self.host = cfg.get("host", "localhost")
        self.user = cfg.get("user", "root")
        self.password = cfg.get("password", "")
        self.database = cfg.get("database", "acadesk_central")
        self.port = int(cfg.get("port", 3306))

    def _get_conn(self):
        try:
            return mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port
            )
        except:
            return None

    def initialize_tables(self):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE,
                password_hash VARCHAR(255),
                college_name VARCHAR(150),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS faculty_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE,
                password_hash VARCHAR(255),
                college_name VARCHAR(150),
                assigned_branch VARCHAR(100),
                added_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS hod_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE,
                password_hash VARCHAR(255),
                college_name VARCHAR(150),
                assigned_department VARCHAR(100),
                email VARCHAR(100),
                added_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS erp_configs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                college_name VARCHAR(150) UNIQUE,
                db_type VARCHAR(50),
                db_host VARCHAR(100),
                db_port INT,
                db_name VARCHAR(100),
                db_user VARCHAR(100),
                encrypted_pass VARCHAR(500),
                tbl_student VARCHAR(100),
                tbl_academic VARCHAR(100),
                tbl_branch VARCHAR(100),
                col_student_join VARCHAR(100),
                col_branch_join VARCHAR(100),
                col_id VARCHAR(100),
                col_name VARCHAR(100),
                col_branch_name VARCHAR(100),
                col_year VARCHAR(100),
                col_email VARCHAR(100),
                col_att VARCHAR(100),
                col_marks VARCHAR(100),
                col_backlogs VARCHAR(100)
            )""")
            conn.commit()
            return True
        except Exception as e:
            print("Auth Table Init Error:", e)
            return False
        finally:
            conn.close()

    def register_admin(self, college_name, username, password):
        conn = self._get_conn()
        if not conn: return False, "Server Offline"
        try:
            cursor = conn.cursor()
            # Ensure unique username globally across all three tables
            for tbl in ["admins", "faculty_accounts", "hod_accounts"]:
                cursor.execute(f"SELECT username FROM {tbl} WHERE username=%s", (username,))
                if cursor.fetchone():
                    return False, "Username is already taken. Please choose another."

            cursor.execute("SELECT * FROM admins WHERE college_name=%s", (college_name,))
            if cursor.fetchone(): 
                return False, "An Administrator already exists for this college. Only one Administrator account is permitted per college."

            hashed = hash_password(password)
            cursor.execute("INSERT INTO admins (username, password_hash, college_name) VALUES (%s, %s, %s)", 
                           (username, hashed, college_name))
            conn.commit()
            return True, "Registration Successful"
        except Exception as e: 
            return False, str(e)
        finally:
            if conn: conn.close()

    def check_admin_exists(self):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM admins")
            count = cursor.fetchone()[0]
            return count > 0
        except:
            return False
        finally:
            if conn: conn.close()

    def add_faculty(self, admin_username, faculty_user, faculty_pass, branch_id):
        conn = self._get_conn()
        if not conn: return False, "Server Offline"
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Check adder
            cursor.execute("SELECT college_name FROM admins WHERE username=%s", (admin_username,))
            adder = cursor.fetchone()
            adder_role = 'Admin'
            
            if not adder:
                cursor.execute("SELECT college_name, assigned_department FROM hod_accounts WHERE username=%s", (admin_username,))
                adder = cursor.fetchone()
                adder_role = 'HOD'
                
            if not adder:
                return False, "User not found or unauthorized to add faculty."

            if adder_role == 'HOD' and str(branch_id).lower() != str(adder['assigned_department']).lower():
                return False, "HOD can only add faculty to their assigned department."

            for tbl in ["admins", "faculty_accounts", "hod_accounts"]:
                cursor.execute(f"SELECT username FROM {tbl} WHERE username=%s", (faculty_user,))
                if cursor.fetchone():
                    return False, "Username is already taken."

            hashed = hash_password(faculty_pass)
            cursor.execute("""
                INSERT INTO faculty_accounts (username, password_hash, college_name, assigned_branch, added_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (faculty_user, hashed, adder['college_name'], branch_id, admin_username))
            conn.commit()

            CentralDBHandler().log_audit(admin_username, "Faculty Created", f"Added faculty {faculty_user} to branch {branch_id}.")
            return True, "Faculty Added"
        except Exception as e:
            return False, str(e)
        finally:
            if conn: conn.close()

    def get_faculty_list(self, college_name):
        conn = self._get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT username, assigned_branch FROM faculty_accounts WHERE college_name=%s", (college_name,))
            return cursor.fetchall()
        except: return []
        finally:
            if conn: conn.close()

    def add_hod(self, admin_username, hod_user, hod_pass, department, email=""):
        conn = self._get_conn()
        if not conn: return False, "Server Offline"
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT college_name FROM admins WHERE username=%s", (admin_username,))
            admin = cursor.fetchone()
            
            if not admin:
                return False, "Only Administrators can add HODs."
                
            for tbl in ["admins", "faculty_accounts", "hod_accounts"]:
                cursor.execute(f"SELECT username FROM {tbl} WHERE username=%s", (hod_user,))
                if cursor.fetchone():
                    return False, "Username is already taken."
                
            cursor.execute("SELECT * FROM hod_accounts WHERE college_name=%s AND assigned_department=%s", (admin['college_name'], department))
            if cursor.fetchone():
                return False, f"This department already has an assigned HOD."
                
            hashed = hash_password(hod_pass)
            cursor.execute("""
                INSERT INTO hod_accounts (username, password_hash, college_name, assigned_department, added_by, email)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (hod_user, hashed, admin['college_name'], department, admin_username, email))
            conn.commit()
            
            CentralDBHandler().log_audit(admin_username, "HOD Created", f"Added HOD {hod_user} for {department}")
            return True, "HOD Added Successfully"
        except Exception as e:
            return False, str(e)
        finally:
            if conn: conn.close()

    def get_hod_list(self, college_name):
        conn = self._get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT username, assigned_department, email FROM hod_accounts WHERE college_name=%s", (college_name,))
            return cursor.fetchall()
        except: return []
        finally:
            if conn: conn.close()

    def revoke_hod(self, username, college_name):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM hod_accounts WHERE username=%s AND college_name=%s", (username, college_name))
            conn.commit()
            CentralDBHandler().log_audit("System", "HOD Removed", f"Revoked HOD {username}")
            return True
        except: return False
        finally:
            if conn: conn.close()

    def revoke_faculty(self, username, college_name):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM faculty_accounts WHERE username=%s AND college_name=%s", (username, college_name))
            conn.commit()
            CentralDBHandler().log_audit("System", "Faculty Removed", f"Revoked faculty {username}")
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
            
            # Lookup in all 3 tables
            user = None
            role = None
            
            cursor.execute("SELECT username, college_name FROM admins WHERE username=%s AND password_hash=%s", (username, hashed))
            admin = cursor.fetchone()
            if admin:
                user = admin
                role = "Admin"
            else:
                cursor.execute("SELECT username, college_name, assigned_department FROM hod_accounts WHERE username=%s AND password_hash=%s", (username, hashed))
                hod = cursor.fetchone()
                if hod:
                    user = hod
                    role = "HOD"
                else:
                    cursor.execute("SELECT username, college_name, assigned_branch FROM faculty_accounts WHERE username=%s AND password_hash=%s", (username, hashed))
                    fac = cursor.fetchone()
                    if fac:
                        user = fac
                        role = "Faculty"
            
            if not user: return None, "Invalid Credentials"
            
            user['role'] = role

            cursor.execute("SELECT * FROM erp_configs WHERE college_name=%s", (user['college_name'],))
            erp = cursor.fetchone()

            config = None
            if erp:
                config = {
                    "db_type": erp['db_type'], "host": erp['db_host'], "port": erp['db_port'],
                    "user": erp['db_user'], "password": decrypt_text(erp['encrypted_pass']),
                    "database": erp['db_name']
                }
            return {"user": user, "erp_config": config}, "Success"
        finally:
            conn.close()

    def save_erp_config(self, college, db_type, host, port, db_name, db_user, db_pass):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            enc_p = encrypt_text(db_pass)

            sql = """
            INSERT INTO erp_configs (
                college_name, db_type, db_host, db_port, db_name, db_user, encrypted_pass
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                db_type=VALUES(db_type), db_host=VALUES(db_host), db_port=VALUES(db_port),
                db_name=VALUES(db_name), db_user=VALUES(db_user), encrypted_pass=VALUES(encrypted_pass)
            """

            cursor.execute(sql, (
                college, db_type, host, port, db_name, db_user, enc_p
            ))

            conn.commit()
            return True
        except Exception as e:
            print("SAVE ERP CONFIG ERROR:", e)
            return False
        finally:
            conn.close()