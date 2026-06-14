import mysql.connector
from logic.config_manager import load_config

class CentralDBHandler:
    def __init__(self):
        cfg = load_config().get("central", {})
        self.host = cfg.get("host", "localhost")
        self.user = cfg.get("user", "root")
        self.password = cfg.get("password", "")
        self.database = cfg.get("database", "acadesk_central")
        self.port = int(cfg.get("port", 3306))

    def _get_server_connection(self):
        """Connect to MySQL without specifying a database, used for creation."""
        if not self.password:
            print(f"❌ Critical: No password provided for user '{self.user}' on {self.host}")
            return None
        try:
            return mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                connect_timeout=5
            )
        except mysql.connector.Error as err:
            print(f"❌ MySQL Server Connection Error: {err.msg} (Error Code: {err.errno})")
            if err.errno == 1045:
                print(f"   Hint: Access denied for '{self.user}'@'{self.host}'. Check your password in db_config.json.")
            return None
        except Exception as e:
            print(f"❌ Unexpected Server Connection Error: {e}")
            return None

    def _get_connection(self):
        """Connect to the specific acadesk_central database."""
        if not self.password:
            print(f"❌ Critical: No password provided for user '{self.user}' on {self.host}")
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
            print(f"❌ MySQL DB Connection Error: {err.msg} (Error Code: {err.errno})")
            if err.errno == 1045:
                print(f"   Hint: Access denied for '{self.user}'@'{self.host}'. Check your password in db_config.json.")
            elif err.errno == 1049:
                print(f"   Hint: Database '{self.database}' does not exist.")
            return None
        except Exception as e:
            print(f"❌ Unexpected DB Connection Error: {e}")
            return None

    def initialize_tables(self):
        # 1. CREATE DATABASE IF NOT EXISTS
        server_conn = self._get_server_connection()
        if not server_conn: return False
        try:
            cursor = server_conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            server_conn.commit()
        except Exception as e:
            print(f"Create DB Error: {e}")
            return False
        finally:
            server_conn.close()

        # 2. CONNECT TO DATABASE AND CREATE TABLES
        conn = self._get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            
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
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS interventions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(100),
                intervention_type VARCHAR(100),
                details TEXT,
                status VARCHAR(50),
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            print(f"Table Init Error: {e}")
            return False
        finally:
            conn.close()

    def truncate_all(self):
        """Truncate all tables in the central database, removing all data while keeping table structures.
        Returns True on success, False on failure.
        """
        conn = self._get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            # Retrieve list of tables in the current database
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            for tbl in tables:
                try:
                    cursor.execute(f"TRUNCATE TABLE {tbl}")
                except Exception as te:
                    print(f"Failed to truncate {tbl}: {te}")
                    # Continue with other tables
            conn.commit()
            return True
        except Exception as e:
            print(f"Error truncating central DB: {e}")
            return False
        finally:
            conn.close()
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO faculty_notes (faculty_id, student_id, note) VALUES (%s, %s, %s)",
                (faculty_id, student_id, note)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving note: {e}")
            return False

    def get_faculty_notes(self, student_id):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT faculty_id, note, created_at FROM faculty_notes WHERE student_id = %s ORDER BY created_at DESC",
                (student_id,)
            )
            notes = cursor.fetchall()
            conn.close()
            return [{"faculty_id": n[0], "note": n[1], "created_at": n[2]} for n in notes]
        except Exception as e:
            print(f"Error fetching notes: {e}")
            return []

    def save_ai_recommendation(self, student_id, recommendation, status="Pending"):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO recommendations (student_id, recommendation, status) VALUES (%s, %s, %s)",
                (student_id, recommendation, status)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving recommendation: {e}")
            return False

    def update_recommendation_status(self, record_id, new_status):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE recommendations SET status = %s WHERE id = %s",
                (new_status, record_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating recommendation: {e}")
            return False

    def add_timeline_event(self, student_id, event_type, description):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO student_timelines (student_id, event_type, description) VALUES (%s, %s, %s)",
                (student_id, event_type, description)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding timeline event: {e}")
            return False

    def log_audit(self, user_id, action, details):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO audit_logs (user_id, action, details) VALUES (%s, %s, %s)",
                (user_id, action, details)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error logging audit: {e}")
            return False

    def log_parent_notification(self, student_id, message, sent_by="System"):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notification_logs (student_id, message, sent_by) VALUES (%s, %s, %s)",
                (student_id, message, sent_by)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error logging parent notification: {e}")
            return False
