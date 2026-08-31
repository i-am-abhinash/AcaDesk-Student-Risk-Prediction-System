import mysql.connector
from logic.config_manager import load_config
from logic.logger import get_logger

_log = get_logger(__name__)
class AnalyticsDBHandler:
    def __init__(self):
        cfg = load_config().get("analytics", {})
        self.host = cfg.get("host", "localhost")
        self.user = cfg.get("user", "root")
        self.password = cfg.get("password", "")
        self.database = cfg.get("database", "acadesk_analytics")
        self.port = int(cfg.get("port", 3306))

    def _get_server_connection(self):
        if not self.password:
            _log.warning(f"Warning: Connecting to {self.host} with user '{self.user}' without a password.")
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
            print(f"❌ Analytics Server Connection Error: {err.msg} (Error Code: {err.errno})")
            return None
        except Exception as e:
            print(f"❌ Unexpected Analytics Server Error: {e}")
            return None

    def _get_connection(self):
        if not self.password:
            _log.warning(f"Warning: Connecting to {self.host} with user '{self.user}' without a password.")
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
            print(f"❌ Analytics DB Connection Error: {err.msg} (Error Code: {err.errno})")
            return None
        except Exception as e:
            print(f"❌ Unexpected Analytics DB Error: {e}")
            return None

    def initialize_tables(self):
        # 1. CREATE DATABASE
        server_conn = self._get_server_connection()
        if not server_conn: return False
        try:
            cursor = server_conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            server_conn.commit()
        except Exception as e:
            print(f"Create Analytics DB Error: {e}")
            return False
        finally:
            server_conn.close()

        # 2. CREATE TABLES
        conn = self._get_connection()
        if not conn: return False
        try:
            cursor = conn.cursor()
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS risk_snapshots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                college_name VARCHAR(150),
                snapshot_date DATE,
                high_risk_count INT,
                medium_risk_count INT,
                low_risk_count INT
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS department_health (
                id INT AUTO_INCREMENT PRIMARY KEY,
                department_id VARCHAR(100),
                health_score FLOAT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS institution_health (
                id INT AUTO_INCREMENT PRIMARY KEY,
                college_name VARCHAR(150),
                health_score FLOAT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS prediction_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(100),
                predicted_risk VARCHAR(50),
                confidence VARCHAR(50),
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS semester_trends (
                id INT AUTO_INCREMENT PRIMARY KEY,
                college_name VARCHAR(150),
                semester VARCHAR(50),
                trend_data JSON,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS recommendation_effectiveness (
                id INT AUTO_INCREMENT PRIMARY KEY,
                recommendation_id INT,
                outcome_status VARCHAR(100),
                effectiveness_score FLOAT,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS monthly_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                report_month VARCHAR(20),
                report_data JSON,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS model_evaluation (
                id INT AUTO_INCREMENT PRIMARY KEY,
                model_version VARCHAR(50),
                accuracy FLOAT,
                precision_score FLOAT,
                recall_score FLOAT,
                f1_score FLOAT,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS analytics_metadata (
                id INT AUTO_INCREMENT PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE,
                config_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )""")
            
            conn.commit()
            return True
        except Exception as e:
            print("Analytics Table Init Error:", e)
            return False
        finally:
            conn.close()
