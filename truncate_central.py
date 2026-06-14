import mysql.connector
from logic.config_manager import load_config
import os

print("Truncating Central Database...")

# Delete old SQLite file if it exists
sqlite_db = "acadesk_central.db"
if os.path.exists(sqlite_db):
    try:
        os.remove(sqlite_db)
        print("Removed old SQLite acadesk_central.db")
    except Exception as e:
        print(f"Could not remove old SQLite DB: {e}")

# Truncate MySQL Central DB
cfg = load_config().get("central")
if not cfg:
    print("MySQL Central DB is not configured yet. Nothing to truncate.")
else:
    try:
        conn = mysql.connector.connect(
            host=cfg.get("host", "localhost"),
            user=cfg.get("user", "root"),
            password=cfg.get("password", ""),
            database=cfg.get("database", "acadesk_central"),
            port=int(cfg.get("port", 3306))
        )
        cursor = conn.cursor()
        
        # Disable foreign key checks just in case
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            try:
                cursor.execute(f"TRUNCATE TABLE {table}")
                print(f"Truncated table: {table}")
            except Exception as e:
                print(f"Could not truncate {table}: {e}")
                
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        conn.close()
        print("MySQL Central DB truncation complete.")
    except Exception as e:
        print(f"Error truncating MySQL Central DB: {e}")
