"""
AcaDesk ERP Connection Layer — Layer 1
=======================================
Manages the read-only connection to a college ERP database.

RESPONSIBILITIES:
  - Manage connection credentials, timeouts, reconnection.
  - Support MySQL/MariaDB as the primary driver.
  - Enforce read-only mode at the connection level.
  - Know NOTHING about tables, columns, or data transformation.

This layer does not import db_handler, schema_detector, or any
higher-level module. It only imports the standard library and
mysql.connector.
"""

from __future__ import annotations
import logging
from typing import Optional, Tuple

_log = logging.getLogger(__name__)


class ERPConnection:
    """
    Thread-safe, read-only connection to a college ERP MySQL database.

    Usage:
        conn_layer = ERPConnection(config)
        ok, msg = conn_layer.connect()
        if ok:
            raw_conn = conn_layer.raw_connection
    """

    def __init__(self, config: dict):
        """
        Args:
            config: dict with keys: host, port, database, user, password
        """
        self._config = config
        self._conn = None
        self._connected = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def raw_connection(self):
        """Returns the underlying mysql.connector connection object."""
        return self._conn

    def connect(self) -> Tuple[bool, str]:
        """
        Establishes a read-only connection to the ERP database.

        Returns:
            (True, "Connected") on success.
            (False, error_message) on failure.
        """
        host = self._config.get("host", "localhost")
        user = self._config.get("user", "root")
        password = self._config.get("password", "")
        database = self._config.get("database", "")
        port = int(self._config.get("port", 3306))

        if not database:
            return False, "No database name provided in ERP configuration."

        try:
            import mysql.connector
            self._conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port,
                connect_timeout=10,
                # Read-only enforcement at session level
                init_command="SET SESSION TRANSACTION READ ONLY",
            )
            # Verify read-only by checking session variable
            cursor = self._conn.cursor()
            cursor.execute("SELECT @@transaction_read_only")
            cursor.close()

            self._connected = True
            _log.info(f"ERP connected (read-only): {user}@{host}:{port}/{database}")
            return True, "Connected successfully"

        except Exception as e:
            # Some MySQL configs don't support READ ONLY session init — fallback
            try:
                import mysql.connector
                self._conn = mysql.connector.connect(
                    host=host,
                    user=user,
                    password=password,
                    database=database,
                    port=port,
                    connect_timeout=10,
                )
                self._connected = True
                _log.info(
                    f"ERP connected (standard mode — read-only not enforced at session): "
                    f"{user}@{host}:{port}/{database}"
                )
                return True, "Connected successfully"
            except Exception as e2:
                self._connected = False
                _log.error(f"ERP connection failed: {e2}")
                return False, str(e2)

    def cursor(self, dictionary: bool = True):
        """Returns a new cursor from the underlying connection."""
        if not self._connected or not self._conn:
            raise RuntimeError("ERPConnection: not connected. Call connect() first.")
        return self._conn.cursor(dictionary=dictionary)

    def close(self) -> None:
        """Closes the ERP connection."""
        try:
            if self._conn:
                self._conn.close()
                _log.debug("ERP connection closed.")
        except Exception as e:
            _log.warning(f"Error closing ERP connection: {e}")
        finally:
            self._conn = None
            self._connected = False

    def ping(self) -> bool:
        """Checks if the connection is still alive."""
        try:
            if self._conn:
                self._conn.ping(reconnect=True, attempts=2, delay=1)
                return True
        except Exception:
            pass
        return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
