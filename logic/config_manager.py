"""
AcaDesk Configuration Manager
==============================
Loads database credentials using a secure priority chain:

  Priority order (highest → lowest):
  1. OS environment variables  (ACADESK_CENTRAL_PASSWORD, etc.)
  2. db_config.json            (project root — gitignored)
  3. .env file                 (project root — gitignored)
  4. Safe hardcoded defaults   (localhost, empty password)

Environment variables (set via OS, CI/CD, or Docker):
  ACADESK_CENTRAL_HOST, ACADESK_CENTRAL_USER, ACADESK_CENTRAL_PASSWORD,
  ACADESK_CENTRAL_DB, ACADESK_CENTRAL_PORT
  ACADESK_ANALYTICS_HOST, ACADESK_ANALYTICS_USER, ACADESK_ANALYTICS_PASSWORD,
  ACADESK_ANALYTICS_DB, ACADESK_ANALYTICS_PORT

Never log passwords. Never expose credentials in exception messages.
"""

import os
import json
import sys

from logic.logger import get_logger

_log = get_logger(__name__)


def get_project_root() -> str:
    """Get the absolute path to the project root directory."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PROJECT_ROOT = get_project_root()
CONFIG_FILE = os.path.join(PROJECT_ROOT, "db_config.json")


def _read_env_file() -> dict:
    """Parse .env file into a dict. Returns empty dict if not found."""
    env_vars: dict = {}
    for env_path in [os.path.join(PROJECT_ROOT, ".env"), os.path.join(os.getcwd(), ".env")]:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env_vars[k.strip()] = v.strip()
                break
            except Exception as e:
                _log.warning(f"Could not read .env file: {type(e).__name__}")
    return env_vars


def _build_section(section: str, json_cfg: dict, env_file: dict) -> dict:
    """
    Build a config section by merging OS env → JSON → .env → defaults.
    OS environment variables always win if present.
    """
    prefix = "ACADESK_CENTRAL" if section == "central" else "ACADESK_ANALYTICS"

    def _get(env_key: str, json_key: str, default: str) -> str:
        # 1. OS env var (highest priority)
        val = os.environ.get(f"{prefix}_{env_key}")
        if val:
            return val
        # 2. JSON config
        if json_key in json_cfg:
            return json_cfg[json_key]
        # 3. .env file
        file_key = f"{prefix}_{env_key}"
        if file_key in env_file:
            return env_file[file_key]
        # 4. Default
        return default

    db_default = "acadesk_central" if section == "central" else "acadesk_analytics"

    return {
        "host":     _get("HOST",     "host",     "localhost"),
        "user":     _get("USER",     "user",     "root"),
        "password": _get("PASSWORD", "password", ""),
        "database": _get("DB",       "database", db_default),
        "port":     int(_get("PORT", "port",     "3306")),
    }


def load_config() -> dict:
    """Load and return the full application configuration dict."""
    json_config: dict = {}

    # Load db_config.json if present
    search_paths = [CONFIG_FILE, os.path.join(os.getcwd(), "db_config.json")]
    for cfg_path in search_paths:
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    json_config = json.load(f)
                break
            except json.JSONDecodeError as je:
                _log.error(f"db_config.json is not valid JSON: {je}")
            except Exception as e:
                _log.error(f"Could not read db_config.json: {type(e).__name__}")
            break

    env_file = _read_env_file()

    config: dict = {}

    # Build each section, letting OS env vars override JSON values
    config["central"]   = _build_section("central",   json_config.get("central", {}),   env_file)
    config["analytics"] = _build_section("analytics", json_config.get("analytics", {}), env_file)

    # Preserve any extra top-level sections (e.g., "erp") from db_config.json unchanged
    for key, val in json_config.items():
        if key not in config:
            config[key] = val

    # Warn (but never reveal) if password is missing
    for section in ["central", "analytics"]:
        if not config[section].get("password"):
            _log.warning(
                f"No password found for '{section}' database. "
                f"Set ACADESK_{section.upper()}_PASSWORD env var or add it to db_config.json."
            )

    return config


def save_config(config_data: dict) -> bool:
    """Persist config to db_config.json (local only — gitignored)."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        _log.error(f"Failed to save config: {type(e).__name__}")
        return False
