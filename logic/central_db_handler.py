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

