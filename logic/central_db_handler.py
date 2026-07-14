"""
CentralDBHandler
================
Provides low-level utility operations against the acadesk_central MySQL database.
- Audit logging
- Full table truncation (admin utility only)

Connection logic is intentionally kept here (rather than delegating to CentralAuth)
because this module is imported by CentralAuth itself, and circular imports must be avoided.

NOTE: The duplicate _get_server_connection() and _get_connection() methods that
formerly existed in this class have been removed (Phase 3 dead code cleanup).
CentralAuth provides the authoritative _get_conn() / _get_server_conn() methods
for all business logic.
"""

import mysql.connector
from logic.config_manager import load_config
from logic.logger import get_logger

_log = get_logger(__name__)


class CentralDBHandler:
    def __init__(self):
        cfg = load_config().get("central", {})
        self.host = cfg.get("host", "localhost")
        self.user = cfg.get("user", "root")
        self.password = cfg.get("password", "")
        self.database = cfg.get("database", "acadesk_central")
        self.port = int(cfg.get("port", 3306))

    def _get_connection(self):
        """Internal connection helper — used only by truncate_all and log_audit."""
        if not self.password:
            _log.error("CentralDBHandler: No password configured. Check db_config.json or env vars.")
            return None
        try:
            return mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                connect_timeout=5,
            )
        except mysql.connector.Error as err:
            _log.error(f"CentralDBHandler connection error (code {err.errno}): {err.msg}")
            return None
        except Exception as e:
            _log.error(f"CentralDBHandler unexpected connection error: {type(e).__name__}")
            return None

    def truncate_all(self):
        """
        Truncate all tables in the central database.
        DESTRUCTIVE — admin utility only. Returns True on success, False on failure.
        """
        conn = self._get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            for tbl in tables:
                try:
                    cursor.execute(f"TRUNCATE TABLE `{tbl}`")
                except Exception as te:
                    _log.warning(f"Failed to truncate table '{tbl}': {te}")
            conn.commit()
            return True
        except Exception as e:
            _log.error(f"Error during truncate_all: {e}")
            return False
        finally:
            conn.close()

    def log_audit(self, user_id, action, details):
        """Write an entry to the audit_logs table."""
        conn = self._get_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO audit_logs (user_id, action, details) VALUES (%s, %s, %s)",
                (user_id, action, str(details)),
            )
            conn.commit()
            return True
        except Exception as e:
            _log.error(f"Audit log write failed: {type(e).__name__}")
            return False
        finally:
            conn.close()
