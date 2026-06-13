import os
import sys
import time
import subprocess
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("❌ Watchdog is not installed. Run 'pip install watchdog' first.")
    sys.exit(1)

class RestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.last_restart = 0
        self.start_app()

    def start_app(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = subprocess.Popen([sys.executable, "main.py"])

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            # Debounce
            current_time = time.time()
            if current_time - self.last_restart > 1:
                print(f"\n🔄 [DEV] Change detected in {os.path.basename(event.src_path)}. Restarting...")
                self.last_restart = current_time
                self.start_app()

def main():
    print("🚀 [DEV] Starting robust Auto-Reloader with Watchdog...")
    print("Watching for changes in .py files. Press Ctrl+C to quit.\n")
    
    event_handler = RestartHandler()
    observer = Observer()
    
    observer.schedule(event_handler, path=".", recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 [DEV] Stopping Auto-Reloader.")
        observer.stop()
        if event_handler.process and event_handler.process.poll() is None:
            event_handler.process.terminate()
            
    observer.join()

if __name__ == "__main__":
    main()
