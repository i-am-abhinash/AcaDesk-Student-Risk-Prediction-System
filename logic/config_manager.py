import os
import json
import sys

def get_project_root():
    """Get the absolute path to the project root directory."""
    if getattr(sys, 'frozen', False):
        # Running as a bundled executable
        return os.path.dirname(sys.executable)
    
    # Running from source
    # This file is in logic/config_manager.py, so root is two levels up
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT_ROOT = get_project_root()
CONFIG_FILE = os.path.join(PROJECT_ROOT, "db_config.json")

def load_config():
    config = {}
    
    # 1. Try to load from db_config.json
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            # print(f"DEBUG: Loaded config from {CONFIG_FILE}")
        except json.JSONDecodeError as je:
            print(f"❌ Error: {CONFIG_FILE} is not a valid JSON file. {je}")
        except Exception as e:
            print(f"❌ Error loading {CONFIG_FILE}: {e}")
    else:
        # Also check current working directory just in case
        alt_config = os.path.join(os.getcwd(), "db_config.json")
        if alt_config != CONFIG_FILE and os.path.exists(alt_config):
            try:
                with open(alt_config, "r") as f:
                    config = json.load(f)
            except Exception as e:
                print(f"Exception caught: {e}")
                pass

    # 2. Fallback to .env for central/analytics if missing
    env_locations = [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    
    env_vars = {}
    for env_path in env_locations:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env_vars[k.strip()] = v.strip()
                break # Stop at first .env found
            except Exception as e:
                print(f"❌ Error reading {env_path}: {e}")

    # Merge .env into config if sections are missing
    if "central" not in config:
        config["central"] = {
            "host": env_vars.get("CENTRAL_DB_HOST", "localhost"),
            "user": env_vars.get("CENTRAL_DB_USER", "root"),
            "password": env_vars.get("CENTRAL_DB_PASSWORD", ""),
            "database": env_vars.get("CENTRAL_DB_NAME", "acadesk_central"),
            "port": int(env_vars.get("CENTRAL_DB_PORT", 3306))
        }
    
    if "analytics" not in config:
        config["analytics"] = {
            "host": env_vars.get("CENTRAL_DB_HOST", "localhost"),
            "user": env_vars.get("CENTRAL_DB_USER", "root"),
            "password": env_vars.get("CENTRAL_DB_PASSWORD", ""),
            "database": "acadesk_analytics",
            "port": int(env_vars.get("CENTRAL_DB_PORT", 3306))
        }

    # Final Validation & logging
    for section in ["central", "analytics"]:
        if section in config:
            cfg = config[section]
            if not cfg.get("password"):
                print(f"⚠️ Warning: No password found for '{section}' database configuration.")
            if not cfg.get("host"):
                cfg["host"] = "localhost" # Ensure host exists

    return config

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
