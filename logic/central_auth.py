import mysql.connector
from logic.encryption import hash_password, verify_password, encrypt_text, decrypt_text
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

    def _get_server_conn(self):
        if not self.password: return None
        try:
            return mysql.connector.connect(
                host=self.host, user=self.user, password=self.password, port=self.port, connect_timeout=5
            )
        except Exception as e:
            print(f"Exception caught: {e}")
            return None

    def _get_conn(self):
        if not self.password:
            print(f"❌ Auth Critical: No password for user '{self.user}' on {self.host}")
            return None
        try:
            return mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                connect_timeout=5
            )
        except mysql.connector.Error as err:
            print(f"❌ Auth Connection Error: {err.msg}")
            return None
        except Exception as e:
            print(f"❌ Auth Unexpected Error: {e}")
            return None

    def initialize_tables(self):
        server_conn = self._get_server_conn()
        if server_conn:
            try:
                sc = server_conn.cursor()
                sc.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                server_conn.commit()
            except Exception as e:
                print(f"Exception caught: {e}")
                pass
            finally: server_conn.close()

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
                col_backlogs VARCHAR(100),
                col_tenth VARCHAR(100),
                col_inter VARCHAR(100),
                col_diploma VARCHAR(100),
                col_lab_perf VARCHAR(100),
                col_mid_exam VARCHAR(100),
                col_cons_abs VARCHAR(100),
                col_leave_freq VARCHAR(100),
                col_parent_phone VARCHAR(100),
                col_parent_email VARCHAR(100)
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS interventions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                college_name VARCHAR(150),
                student_id VARCHAR(100),
                faculty_username VARCHAR(100),
                risk_level VARCHAR(50),
                dominant_factor VARCHAR(100),
                recommended_action VARCHAR(200),
                priority INT,
                status VARCHAR(50) DEFAULT 'Planned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS email_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                college_name VARCHAR(150),
                student_id VARCHAR(100),
                alert_type VARCHAR(100),
                semester VARCHAR(50),
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS faculty_notes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                faculty_id VARCHAR(100),
                student_id VARCHAR(100),
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS note_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                note_id INT,
                old_note TEXT,
                modified_by VARCHAR(100),
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS student_timelines (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(100),
                event_type VARCHAR(100),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS recommendations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(100),
                recommendation TEXT,
                status VARCHAR(50) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS notification_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(100),
                message TEXT,
                sent_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id VARCHAR(100),
                action VARCHAR(100),
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS system_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS user_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100),
                session_token VARCHAR(255),
                ip_address VARCHAR(50),
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
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
        except Exception as e:
            print(f"Exception caught: {e}")
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
        except Exception as e:
            print(f"Exception caught: {e}")
            return []
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
        except Exception as e:
            print(f"Exception caught: {e}")
            return []
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
        except Exception as e:
            print(f"Exception caught: {e}")
            return False
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
        except Exception as e:
            print(f"Exception caught: {e}")
            return False
        finally:
            if conn: conn.close()

    def login(self, username, password):
        conn = self._get_conn()
        if not conn: return None, "Server Offline"
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Fetch user without checking password_hash
            user = None
            role = None
            
            cursor.execute("SELECT username, college_name, password_hash FROM admins WHERE username=%s", (username,))
            admin = cursor.fetchone()
            if admin and verify_password(password, admin['password_hash']):
                user = admin
                role = "Admin"
                if not admin['password_hash'].startswith("$2"):
                    cursor.execute("UPDATE admins SET password_hash=%s WHERE username=%s", (hash_password(password), username))
                    conn.commit()
            else:
                cursor.execute("SELECT username, college_name, assigned_department, password_hash FROM hod_accounts WHERE username=%s", (username,))
                hod = cursor.fetchone()
                if hod and verify_password(password, hod['password_hash']):
                    user = hod
                    role = "HOD"
                    if not hod['password_hash'].startswith("$2"):
                        cursor.execute("UPDATE hod_accounts SET password_hash=%s WHERE username=%s", (hash_password(password), username))
                        conn.commit()
                else:
                    cursor.execute("SELECT username, college_name, assigned_branch, password_hash FROM faculty_accounts WHERE username=%s", (username,))
                    fac = cursor.fetchone()
                    if fac and verify_password(password, fac['password_hash']):
                        user = fac
                        role = "Faculty"
                        if not fac['password_hash'].startswith("$2"):
                            cursor.execute("UPDATE faculty_accounts SET password_hash=%s WHERE username=%s", (hash_password(password), username))
                            conn.commit()
            
            if not user: return None, "Invalid Credentials"
            
            del user['password_hash']
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
                # Load mapping
                for k, v in erp.items():
                    if k.startswith('tbl_') or k.startswith('col_'):
                        if v is not None:
                            config[k] = v
                            
            return {"user": user, "erp_config": config}, "Success"
        finally:
            conn.close()

    def update_password(self, username, user_type, current_password, new_password):
        conn = self._get_conn()
        if not conn: return False, "Database connection failed"
        
        from logic.encryption import hash_password, verify_password
        
        table = ""
        if user_type == "Admin": table = "admins"
        elif user_type == "HOD": table = "hod_accounts"
        elif user_type == "Faculty": table = "faculty_accounts"
        else: return False, "Invalid user type"
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"SELECT password_hash FROM {table} WHERE username=%s", (username,))
            row = cursor.fetchone()
            
            if not row or not verify_password(current_password, row['password_hash']):
                return False, "Incorrect current password"
                
            new_hashed = hash_password(new_password)
            cursor.execute(f"UPDATE {table} SET password_hash=%s WHERE username=%s", (new_hashed, username))
            conn.commit()
            return True, "Password updated successfully"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def save_erp_config(self, college, db_type, host, port, db_name, db_user, db_pass, mapping=None):
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
            
            if mapping:
                for k, v in mapping.items():
                    if k.startswith('tbl_') or k.startswith('col_'):
                        up_sql = f"UPDATE erp_configs SET {k}=%s WHERE college_name=%s"
                        cursor.execute(up_sql, (v, college))

            conn.commit()
            return True
        except Exception as e:
            print("SAVE ERP CONFIG ERROR:", e)
            return False
        finally:
            conn.close()

    def check_email_sent(self, college_name, student_id, alert_type, semester):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM email_logs WHERE college_name=%s AND student_id=%s AND alert_type=%s AND semester=%s",
                           (college_name, student_id, alert_type, semester))
            return cursor.fetchone() is not None
        except Exception as e:
            print("check_email_sent error:", e)
            return False
        finally:
            conn.close()

    def log_email_sent(self, college_name, student_id, alert_type, semester):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO email_logs (college_name, student_id, alert_type, semester) VALUES (%s, %s, %s, %s)",
                           (college_name, student_id, alert_type, semester))
            conn.commit()
            return True
        except Exception as e:
            print("log_email_sent error:", e)
            return False
        finally:
            conn.close()

    def save_faculty_note(self, student_id, faculty_username, department, note_text, note_status="ACTIVE"):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO faculty_notes (student_id, faculty_username, department, note_text, note_status) VALUES (%s, %s, %s, %s, %s)",
                           (student_id, faculty_username, department, note_text, note_status))
            conn.commit()
            
            # Write-through to SQLite Cache
            try:
                from logic.local_cache import cache
                from datetime import datetime
                note_data = [{
                    "student_id": str(student_id),
                    "faculty_username": str(faculty_username),
                    "department": str(department),
                    "note_text": str(note_text),
                    "note_status": str(note_status),
                    "created_at": datetime.now().isoformat()
                }]
                cache.bulk_insert("faculty_notes", note_data)
            except Exception as ce:
                print(f"Cache write-through error: {ce}")
                
            return True
        except Exception as e:
            print("save_faculty_note error:", e)
            return False
        finally:
            conn.close()

    def get_notes_for_student(self, student_id):
        try:
            from logic.local_cache import cache
            with cache.get_connection() as c_conn:
                c_cursor = c_conn.cursor()
                c_cursor.execute("SELECT * FROM faculty_notes WHERE student_id=? ORDER BY created_at DESC", (str(student_id),))
                res = c_cursor.fetchall()
                if res: return [dict(r) for r in res]
        except Exception as ce:
            print(f"Cache read error: {ce}")
        conn = self._get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM faculty_notes WHERE student_id=%s ORDER BY created_at DESC", (student_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Exception caught: {e}")
            return []
        finally:
            if conn: conn.close()
            
    def get_student_note_stats(self, department=None):
        conn = self._get_conn()
        if not conn: return {}
        try:
            cursor = conn.cursor(dictionary=True)
            if department:
                query = """
                    SELECT student_id, COUNT(*) as total_notes,
                           (SELECT note_status FROM faculty_notes f2 
                            WHERE f2.student_id = faculty_notes.student_id 
                            ORDER BY created_at DESC LIMIT 1) as latest_status,
                           (SELECT faculty_username FROM faculty_notes f2 
                            WHERE f2.student_id = faculty_notes.student_id 
                            ORDER BY created_at DESC LIMIT 1) as latest_faculty,
                           (SELECT note_text FROM faculty_notes f2 
                            WHERE f2.student_id = faculty_notes.student_id 
                            ORDER BY created_at DESC LIMIT 1) as latest_text,
                           (SELECT created_at FROM faculty_notes f2 
                            WHERE f2.student_id = faculty_notes.student_id 
                            ORDER BY created_at DESC LIMIT 1) as latest_date
                    FROM faculty_notes
                    WHERE department = %s
                    GROUP BY student_id
                """
                cursor.execute(query, (department,))
            else:
                query = """
                    SELECT student_id, COUNT(*) as total_notes,
                           (SELECT note_status FROM faculty_notes f2 
                            WHERE f2.student_id = faculty_notes.student_id 
                            ORDER BY created_at DESC LIMIT 1) as latest_status,
                           (SELECT faculty_username FROM faculty_notes f2 
                            WHERE f2.student_id = faculty_notes.student_id 
                            ORDER BY created_at DESC LIMIT 1) as latest_faculty,
                           (SELECT note_text FROM faculty_notes f2 
                            WHERE f2.student_id = faculty_notes.student_id 
                            ORDER BY created_at DESC LIMIT 1) as latest_text,
                           (SELECT created_at FROM faculty_notes f2 
                            WHERE f2.student_id = faculty_notes.student_id 
                            ORDER BY created_at DESC LIMIT 1) as latest_date
                    FROM faculty_notes
                    GROUP BY student_id
                """
                cursor.execute(query)
                
            results = cursor.fetchall()
            return {r['student_id']: r for r in results}
        except Exception as e: 
            print("get_student_note_stats error:", e)
            return {}
        finally:
            conn.close()
            
    def get_all_notes(self):
        conn = self._get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM faculty_notes ORDER BY created_at DESC")
            return cursor.fetchall()
        except Exception as e:
            print(f"Exception caught: {e}")
            return []
        finally:
            if conn: conn.close()
            
    def get_notes_by_department(self, department):
        conn = self._get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM faculty_notes WHERE department=%s ORDER BY created_at DESC", (department,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Exception caught: {e}")
            return []
        finally:
            if conn: conn.close()

    def update_faculty_note(self, note_id, new_text):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE faculty_notes SET note_text=%s WHERE id=%s", (new_text, note_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Exception caught: {e}")
            return False
        finally:
            conn.close()

    def delete_faculty_note(self, note_id):
        conn = self._get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM faculty_notes WHERE id=%s", (note_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Exception caught: {e}")
            return False
        finally:
            conn.close()