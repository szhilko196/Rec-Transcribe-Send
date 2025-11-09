"""
Automatic monitoring of input folder for processing new videos

This script:
1. Monitors for new video files in data/input/
2. Automatically launches orchestrator.py for processing
3. Maintains database of processed files (to avoid duplicate processing)
4. Logs all operations
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Set, Dict
import hashlib
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
except ImportError:
    print("ERROR: watchdog is not installed. Install it: pip install watchdog")
    sys.exit(1)

# Path configuration
DATA_DIR = Path(os.getenv('DATA_PATH', 'data'))
INPUT_DIR = DATA_DIR / "input"
PROCESSED_DB_PATH = DATA_DIR / "processed_videos.json"

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DATA_DIR / 'video_processor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Processing configuration
SUPPORTED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
ORCHESTRATOR_SCRIPT = Path("scripts/orchestrator.py")

# File stabilization timeout (seconds) - wait until file is fully copied
FILE_STABLE_TIMEOUT = 5


class ProcessedVideosDB:
    """Database of processed video files"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.data: Dict[str, Dict] = self._load()

    def _load(self) -> Dict[str, Dict]:
        """Load database from file"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading database: {e}")
                return {}
        return {}

    def _save(self):
        """Save database to file"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving database: {e}")

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA256 hash of file (first 1MB for speed)"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read first 1MB for fast hashing
                chunk = f.read(1024 * 1024)
                sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""

    def is_processed(self, file_path: Path) -> bool:
        """Check if file has been successfully processed"""
        # Check file existence
        if not file_path.exists():
            logger.warning(f"File {file_path.name} does not exist, skipping check")
            return False

        file_hash = self._calculate_file_hash(file_path)
        if not file_hash:
            return False

        # Check by hash (primary criterion)
        for record in self.data.values():
            if record.get('file_hash') == file_hash and record.get('status') == 'success':
                logger.info(f"File {file_path.name} already processed (duplicate found by hash)")
                return True

        return False

    def mark_processed(self, file_path: Path, result_folder: str, status: str = "success",
                      error: str = None):
        """Mark file as processed"""
        file_hash = self._calculate_file_hash(file_path)

        # Get file size if file still exists
        file_size = 0
        if file_path.exists():
            try:
                file_size = file_path.stat().st_size
            except Exception as e:
                logger.warning(f"Failed to get file size for {file_path.name}: {e}")

        record = {
            "file_name": file_path.name,
            "file_path": str(file_path.absolute()),
            "file_hash": file_hash,
            "file_size": file_size,
            "processed_at": datetime.now().isoformat(),
            "status": status,
            "result_folder": result_folder,
            "error": error
        }

        # Use hash as key (or file name if hash is empty)
        key = file_hash if file_hash else file_path.name
        self.data[key] = record
        self._save()
        logger.info(f"File {file_path.name} marked as {status}")

    def get_stats(self) -> Dict:
        """Get processing statistics"""
        total = len(self.data)
        success = sum(1 for r in self.data.values() if r.get('status') == 'success')
        failed = sum(1 for r in self.data.values() if r.get('status') == 'failed')

        return {
            "total_processed": total,
            "success": success,
            "failed": failed
        }


class VideoFileHandler(FileSystemEventHandler):
    """File system event handler for video files"""

    def __init__(self, db: ProcessedVideosDB):
        self.db = db
        self.processing_files: Set[str] = set()

    def on_created(self, event: FileCreatedEvent):
        """Handle file creation event"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check extension
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        # Ignore Yandex.Disk temporary files with UUID prefixes
        # Pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_originalname.ext
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_'
        if re.match(uuid_pattern, file_path.name, re.IGNORECASE):
            logger.info(f"Ignoring Yandex.Disk temporary file: {file_path.name}")
            return

        logger.info(f"Detected new video file: {file_path.name}")

        # Avoid duplicate processing
        if str(file_path) in self.processing_files:
            logger.info(f"File {file_path.name} already being processed, skipping")
            return

        # Wait for file stabilization (copying may take time)
        self._wait_for_stable_file(file_path)

        # Check that file exists after waiting
        if not file_path.exists():
            logger.warning(f"File {file_path.name} disappeared after stabilization wait, skipping processing")
            return

        # Check if file has already been processed
        if self.db.is_processed(file_path):
            logger.info(f"File {file_path.name} was already successfully processed, skipping")
            return

        # Start processing
        self._process_video(file_path)

    def _wait_for_stable_file(self, file_path: Path, timeout: int = 60):
        """
        Wait until file stabilizes (copying completes)

        Args:
            file_path: File path
            timeout: Maximum wait time in seconds
        """
        logger.info(f"Waiting for file stabilization {file_path.name}...")

        start_time = time.time()
        last_size = -1

        while time.time() - start_time < timeout:
            try:
                # Check that file exists
                if not file_path.exists():
                    logger.warning(f"File {file_path.name} disappeared during stabilization wait")
                    time.sleep(2)
                    continue

                current_size = file_path.stat().st_size

                if current_size == last_size and current_size > 0:
                    # Size unchanged, file is stable
                    time.sleep(FILE_STABLE_TIMEOUT)

                    # Check again (file may disappear)
                    if file_path.exists() and file_path.stat().st_size == current_size:
                        logger.info(f"File {file_path.name} stabilized ({current_size} bytes)")
                        return

                last_size = current_size
                time.sleep(2)

            except Exception as e:
                logger.warning(f"Error checking file {file_path.name}: {e}")
                time.sleep(2)

        logger.warning(f"File {file_path.name} did not stabilize within {timeout}s, continuing")

    def _process_video(self, file_path: Path):
        """
        Launch video processing through orchestrator

        Args:
            file_path: Video file path
        """
        self.processing_files.add(str(file_path))

        try:
            # Check that file exists before processing
            if not file_path.exists():
                logger.error(f"File {file_path.name} not found, processing impossible")
                self.db.mark_processed(file_path, "", status="failed",
                                      error="File disappeared before processing started")
                return

            logger.info(f"Starting processing: {file_path.name}")

            # Get file size with error handling
            try:
                file_size_mb = file_path.stat().st_size / (1024*1024)
                logger.info(f"File size: {file_size_mb:.2f} MB")
            except Exception as e:
                logger.warning(f"Failed to get file size: {e}")

            # Launch orchestrator
            cmd = [sys.executable, str(ORCHESTRATOR_SCRIPT), str(file_path)]

            logger.info(f"Launching command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=18000  # 5 hours maximum
            )

            if result.returncode == 0:
                # Successful processing
                logger.info(f"[SUCCESS] File {file_path.name} successfully processed!")

                # Parse result to get result folder
                try:
                    # Look for line with result_folder in output
                    for line in result.stdout.split('\n'):
                        if 'result_folder' in line or 'Results folder' in line:
                            logger.info(f"Result: {line}")

                    # Try to find JSON at end of output
                    json_match = re.search(r'\{[^{}]*"result_folder"[^{}]*\}', result.stdout, re.DOTALL)
                    if json_match:
                        result_data = json.loads(json_match.group(0))
                        result_folder = result_data.get('result_folder', 'unknown')
                    else:
                        result_folder = 'unknown'

                except Exception as e:
                    logger.warning(f"Failed to parse result: {e}")
                    result_folder = 'unknown'

                # Mark as successfully processed
                self.db.mark_processed(file_path, result_folder, status="success")

            else:
                # Processing error
                logger.error(f"[FAILED] Error processing {file_path.name}")
                logger.error(f"Return code: {result.returncode}")
                logger.error(f"STDOUT: {result.stdout[-500:]}")  # Last 500 characters
                logger.error(f"STDERR: {result.stderr[-500:]}")

                # Mark as failed attempt
                error_msg = result.stderr[-200:] if result.stderr else "Unknown error"
                self.db.mark_processed(file_path, "", status="failed", error=error_msg)

        except subprocess.TimeoutExpired:
            logger.error(f"[TIMEOUT] Processing {file_path.name} exceeded time limit (5 hours)")
            self.db.mark_processed(file_path, "", status="failed", error="Timeout")

        except Exception as e:
            logger.error(f"[ERROR] Unhandled error processing {file_path.name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.db.mark_processed(file_path, "", status="failed", error=str(e))

        finally:
            self.processing_files.discard(str(file_path))


def scan_existing_files(db: ProcessedVideosDB, handler: VideoFileHandler):
    """
    Check existing files in input folder on startup

    Args:
        db: Database of processed files
        handler: File handler
    """
    logger.info("Scanning existing files in input folder...")

    if not INPUT_DIR.exists():
        logger.warning(f"Folder {INPUT_DIR} does not exist")
        return

    video_files = []
    for ext in SUPPORTED_EXTENSIONS:
        video_files.extend(INPUT_DIR.glob(f"*{ext}"))

    logger.info(f"Found video files: {len(video_files)}")

    for file_path in video_files:
        # Check that file exists (may disappear during scanning)
        if not file_path.exists():
            logger.warning(f"File {file_path.name} disappeared during scanning, skipping")
            continue

        if not db.is_processed(file_path):
            logger.info(f"Unprocessed file: {file_path.name}, starting processing...")
            handler._process_video(file_path)
        else:
            logger.info(f"File {file_path.name} already processed, skipping")


def main():
    """Main monitoring function"""
    logger.info("=" * 80)
    logger.info("AUTOMATIC INPUT FOLDER MONITORING")
    logger.info("=" * 80)

    # Check orchestrator presence
    if not ORCHESTRATOR_SCRIPT.exists():
        logger.error(f"Orchestrator not found: {ORCHESTRATOR_SCRIPT}")
        sys.exit(1)

    # Create input folder if it doesn't exist
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize database
    db = ProcessedVideosDB(PROCESSED_DB_PATH)
    stats = db.get_stats()
    logger.info(f"Loaded processed files database: {stats}")

    # Create handler
    handler = VideoFileHandler(db)

    # Scan existing files
    scan_existing_files(db, handler)

    # Configure watchdog observer
    observer = Observer()
    observer.schedule(handler, str(INPUT_DIR), recursive=False)
    observer.start()

    logger.info(f"Monitoring folder: {INPUT_DIR.absolute()}")
    logger.info(f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 80)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stop signal received...")
        observer.stop()

    observer.join()
    logger.info("Monitoring stopped")

    # Final statistics
    stats = db.get_stats()
    logger.info(f"Final statistics: {stats}")


if __name__ == "__main__":
    main()
