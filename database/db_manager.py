from sqlalchemy import create_engine, text
import sqlite3
import os

class DBManager:
    def __init__(self):
        self.engine = None
        self.central_db = "acadesk_central.db"
        self.init_central_db()

    def init_central_db(self):
        """Creates the AcaDesk Central Database (SQLite)"""
        conn = sqlite3.connect(self.central_db)
        cursor = conn.cursor()
        
        # Application Configuration and Users
        cursor.execute('''CREATE TABLE IF NOT EXISTS admins (username TEXT, password TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS faculty (username TEXT, password TEXT, is_temp INT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS app_config (erp_connection_string TEXT, is_setup INT)''')
        
        # Central Intelligence & Intervention Data
        cursor.execute('''CREATE TABLE IF NOT EXISTS faculty_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, faculty_id TEXT, student_id TEXT, note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ai_recommendations (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, recommendation TEXT, status TEXT, generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS student_timeline (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, event_type TEXT, description TEXT, event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, details TEXT, log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS parent_notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, message TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Create Default Admin
        cursor.execute("SELECT * FROM admins")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO admins VALUES ('admin', 'admin')")
        
        conn.commit()
        conn.close()

    def get_erp_engine(self):
        """Fetches the ERP connection string and creates a Read-Only engine"""
        conn = sqlite3.connect(self.central_db)
        cursor = conn.cursor()
        cursor.execute("SELECT erp_connection_string FROM app_config WHERE is_setup=1")
        result = cursor.fetchone()
        conn.close()

        if result:
            try:
                self.engine = create_engine(result[0])
                return self.engine
            except Exception as e:
                print(f"ERP Connection Error: {e}")
                return None
        return None

    def get_central_connection(self):
        """Returns connection to the Read/Write AcaDesk Central Database"""
        return sqlite3.connect(self.central_db)

    def save_erp_config(self, db_type, host, port, user, password, dbname):
        """Saves the connection string based on user input"""
        if db_type == "SQLite":
            conn_str = f"sqlite:///{dbname}"
        elif db_type == "MySQL":
            conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"
        elif db_type == "PostgreSQL":
            conn_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        else:
            conn_str = f"sqlite:///{dbname}"

        conn = sqlite3.connect(self.central_db)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM app_config")
        cursor.execute("INSERT INTO app_config VALUES (?, 1)", (conn_str,))
        conn.commit()
        conn.close()
        return True