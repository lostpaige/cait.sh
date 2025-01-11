import os
import time
import threading
from typing import Callable, Dict, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

class HotReloader(FileSystemEventHandler):
    def __init__(self, reload_callback: Callable, watch_paths: List[str], patterns: List[str]):
        self.last_reload = time.time()
        self.reload_callback = reload_callback
        self.watch_paths = watch_paths
        self.patterns = patterns
        self.file_times: Dict[str, float] = {}
        self.observer = Observer()
        
        # Initialize file modification times
        for path in self.watch_paths:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if any(file.endswith(pattern) for pattern in patterns):
                            full_path = os.path.join(root, file)
                            self.file_times[full_path] = os.path.getmtime(full_path)
            elif os.path.isfile(path):
                self.file_times[path] = os.path.getmtime(path)

    def on_modified(self, event):
        if event.is_directory:
            return
        
        if not any(event.src_path.endswith(pattern) for pattern in self.patterns):
            return

        # Prevent duplicate reloads
        current_time = time.time()
        if current_time - self.last_reload < 1:  # Debounce for 1 second
            return
        
        self.last_reload = current_time
        print(f"🔄 Detected change in {event.src_path}, reloading...")
        
        if event.src_path.endswith('.env'):
            load_dotenv(override=True)
            
        self.reload_callback()

    def start(self):
        for path in self.watch_paths:
            self.observer.schedule(self, path, recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join() 