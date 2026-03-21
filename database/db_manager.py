from sqlalchemy import create_engine, text
import sqlite3

class DBManager:
    def __init__(self):
        self.engine = None
        self.conn_string = "sqlite:///risk_system.db"  # Default to local DB
        self.init_local_db()

    def init_local_db(self):
        """Creates the local settings database (SQLite)"""
        # We use raw sqlite3 for the local config to ensure it always works
        conn = sqlite3.connect("risk_system.db")
        cursor = conn.cursor()
        # Admin Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS admins (username TEXT, password TEXT)''')
        # Faculty Table
        cursor.execute('''CREATE TABLE IF NOT EXISTS faculty (username TEXT, password TEXT, is_temp INT)''')
        # Config Table (Stores the connection string for the College ERP)
        cursor.execute('''CREATE TABLE IF NOT EXISTS app_config (erp_connection_string TEXT, is_setup INT)''')
        
        # Create Default Admin (user: admin, pass: admin)
        cursor.execute("SELECT * FROM admins")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO admins VALUES ('admin', 'admin')")
        
        conn.commit()
        conn.close()

    def get_erp_engine(self):
        """Fetches the ERP connection string from local DB and creates an engine"""
        conn = sqlite3.connect("risk_system.db")
        cursor = conn.cursor()
        cursor.execute("SELECT erp_connection_string FROM app_config WHERE is_setup=1")
        result = cursor.fetchone()
        conn.close()

        if result:
            try:
                # result[0] contains the connection string (e.g., mysql://...)
                self.engine = create_engine(result[0])
                return self.engine
            except Exception as e:
                print(f"ERP Connection Error: {e}")
                return None
        return None

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

        conn = sqlite3.connect("risk_system.db")
        cursor = conn.cursor()
        # clear old config
        cursor.execute("DELETE FROM app_config")
        # insert new
        cursor.execute("INSERT INTO app_config VALUES (?, 1)", (conn_str,))
        conn.commit()
        conn.close()
        return True