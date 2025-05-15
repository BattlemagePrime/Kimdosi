import os
import shutil
import time
import logging
from pathlib import Path
from typing import List, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileCollector(FileSystemEventHandler):
    def __init__(self, watch_paths: List[str], output_dir: Path):
        self.watch_paths = watch_paths
        self.output_dir = output_dir
        self.seen_files: Set[str] = set()
        self.start_time = time.time()
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for file collection events"""
        log_file = self.output_dir / "file_collector.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def on_created(self, event):
        if event.is_directory:
            return
            
        src_path = Path(event.src_path)
        if src_path.is_file() and str(src_path) not in self.seen_files:
            self.seen_files.add(str(src_path))
            try:
                # Create timestamped directory for this file
                timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time()))
                dest_dir = self.output_dir / timestamp
                dest_dir.mkdir(exist_ok=True)
                
                # Copy the file with metadata
                dest_path = dest_dir / src_path.name
                shutil.copy2(src_path, dest_path)
                
                logging.info(f"Collected new file: {src_path.name}")
                logging.info(f"Saved to: {dest_path}")
                
                # Log file metadata
                stats = src_path.stat()
                logging.info(f"File size: {stats.st_size} bytes")
                logging.info(f"Created: {time.ctime(stats.st_ctime)}")
                logging.info(f"Modified: {time.ctime(stats.st_mtime)}")
                
            except Exception as e:
                logging.error(f"Error collecting file {src_path.name}: {str(e)}")

    def start_monitoring(self, duration: int = None):
        """Start monitoring directories for new files"""
        logging.info("Starting file collection monitoring")
        logging.info(f"Watching paths: {', '.join(self.watch_paths)}")
        
        observer = Observer()
        for path in self.watch_paths:
            if os.path.exists(path):
                observer.schedule(self, path, recursive=True)
                logging.info(f"Monitoring directory: {path}")
            else:
                logging.warning(f"Path does not exist: {path}")
        
        observer.start()
        try:
            if duration:
                logging.info(f"Monitoring for {duration} seconds")
                time.sleep(duration)
            else:
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")
        finally:
            observer.stop()
            observer.join()
            logging.info("File collection monitoring complete")