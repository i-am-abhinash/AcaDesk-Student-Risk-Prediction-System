import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db_config.json")

def load_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        except:
            pass

    # Fallback to .env for central/analytics if missing
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.readlines()
            env_vars = {}
            for line in lines:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    env_vars[k.strip()] = v.strip()
            
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
    
    return config

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
