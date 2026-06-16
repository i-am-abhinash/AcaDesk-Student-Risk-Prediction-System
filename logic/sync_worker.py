import sys
import threading
from datetime import datetime
import traceback
from logic.db_handler import DBHandler
from logic.central_auth import CentralAuth
from logic.local_cache import cache

class SyncWorker:
    def __init__(self, erp_config, shared_data=None):
        self.erp_config = erp_config
        self.shared_data = shared_data or {}
        self.is_running = True
        self.progress_callback = None
        self.finished_callback = None

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def connect_progress(self, callback):
        self.progress_callback = callback

    def connect_finished(self, callback):
        self.finished_callback = callback

    def _emit_progress(self, val, msg):
        if self.progress_callback:
            self.progress_callback(val, msg)

    def _emit_finished(self, success, msg):
        if self.finished_callback:
            self.finished_callback(success, msg)

    def run(self):
        try:
            self._emit_progress(10, "Connecting to Master ERP...")
            
            # Connect to ERP with cache_mode=False strictly to pull fresh data
            erp_db = DBHandler(config_dict=self.erp_config)
            erp_db.cache_mode = False 
            
            if not erp_db.connected:
                self._emit_finished(False, "Failed to connect to ERP. Operating in Offline Mode.")
                return

            self._emit_progress(20, "Fetching Departments...")
            branches = erp_db.get_branch_map()
            dept_data = [{"dept_id": str(k), "dept_name": str(v)} for k, v in branches.items()]
            cache.bulk_insert("departments", dept_data)
            
            self._emit_progress(40, "Fetching Student Records (This may take a moment)...")
            students = erp_db.get_all_students()
            
            if not students:
                self._emit_finished(False, "No student data found in ERP.")
                return
                
            self._emit_progress(60, "Caching Students locally...")
            cache.bulk_insert("students_cache", students)
            
            self._emit_progress(70, "Fetching Faculty Notes...")
            central_auth = CentralAuth()
            conn = central_auth._get_conn()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT * FROM faculty_notes")
                    notes = cursor.fetchall()
                    if notes:
                        for n in notes:
                            if n.get("created_at"):
                                n["created_at"] = str(n["created_at"])
                            if 'id' in n:
                                n['note_id'] = n.pop('id')
                        cache.bulk_insert("faculty_notes", notes)
                except Exception as e:
                    print(f"Error syncing notes: {e}")
                finally:
                    conn.close()

            self._emit_progress(90, "Finalizing Database...")
            cache.update_metadata(datetime.now().isoformat(), len(students))

            self._emit_progress(100, "Synchronization Complete.")
            self._emit_finished(True, f"Successfully cached {len(students)} students.")
            
        except Exception as e:
            traceback.print_exc()
            self._emit_finished(False, f"Sync Error: {str(e)}")
            
    def stop(self):
        self.is_running = False
