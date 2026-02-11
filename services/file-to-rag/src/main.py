"""
FileToRag Service - Main Entry Point

Monitors a folder for markdown files and uploads them to OpenWebUI Knowledge Base.
"""

import hashlib
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

from dotenv import load_dotenv

# Load environment variables from .env file in service directory and project root
SERVICE_DIR = Path(__file__).parent.parent
ROOT_DIR = SERVICE_DIR.parent.parent

# Load service .env first, then root .env (root overrides if same key)
if (SERVICE_DIR / '.env').exists():
    load_dotenv(SERVICE_DIR / '.env')
if (ROOT_DIR / '.env').exists():
    load_dotenv(ROOT_DIR / '.env', override=True)

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
except ImportError:
    print("ERROR: watchdog is not installed. Install it: pip install watchdog")
    sys.exit(1)

from .config import Config
from .markdown_chunker import MarkdownChunker
from .openwebui_client import OpenWebUIClient
from .rag_uploader import RAGUploader


class ProcessedFilesDB:
    """Database of processed files (tracks by hash to avoid duplicates)"""

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
                logging.error(f"Error loading database: {e}")
                return {}
        return {}

    def _save(self):
        """Save database to file"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving database: {e}")

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA256 hash of file content"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logging.error(f"Error calculating hash for {file_path}: {e}")
            return ""

    def is_processed(self, file_path: Path) -> bool:
        """Check if file has been successfully processed (by hash)"""
        if not file_path.exists():
            return False

        file_hash = self._calculate_file_hash(file_path)
        if not file_hash:
            return False

        # Check by hash
        for record in self.data.values():
            if record.get('file_hash') == file_hash and record.get('status') == 'success':
                return True

        return False

    def mark_processed(
        self,
        file_path: Path,
        status: str = "success",
        file_ids: Optional[list] = None,
        error: Optional[str] = None
    ):
        """Mark file as processed"""
        file_hash = self._calculate_file_hash(file_path)

        record = {
            "file_name": file_path.name,
            "file_path": str(file_path.absolute()),
            "file_hash": file_hash,
            "processed_at": datetime.now().isoformat(),
            "status": status,
            "file_ids": file_ids or [],
            "error": error
        }

        # Use hash as key (or file name if hash is empty)
        key = file_hash if file_hash else file_path.name
        self.data[key] = record
        self._save()

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

    def get_failed_files(self) -> list:
        """Get list of failed files for reprocessing"""
        return [
            record for record in self.data.values()
            if record.get('status') == 'failed'
        ]


class MarkdownFileHandler(FileSystemEventHandler):
    """File system event handler for markdown files"""

    def __init__(
        self,
        db: ProcessedFilesDB,
        chunker: MarkdownChunker,
        uploader: RAGUploader,
        logger: logging.Logger,
        parallel_uploads: int = 4
    ):
        self.db = db
        self.chunker = chunker
        self.uploader = uploader
        self.logger = logger
        self.parallel_uploads = parallel_uploads
        self.processing_files: Set[str] = set()

    def on_created(self, event: FileCreatedEvent):
        """Handle file creation event"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process .md files
        if file_path.suffix.lower() != '.md':
            return

        self.logger.info(f"Detected new file: {file_path.name}")

        # Avoid duplicate processing
        if str(file_path) in self.processing_files:
            self.logger.info(f"File {file_path.name} already being processed, skipping")
            return

        # Wait for file to stabilize (copying may take time)
        self._wait_for_stable_file(file_path)

        # Check that file still exists after waiting
        if not file_path.exists():
            self.logger.warning(f"File {file_path.name} disappeared, skipping")
            return

        # Check if already processed
        if self.db.is_processed(file_path):
            self.logger.info(f"File {file_path.name} already processed, skipping")
            return

        # Process the file
        self._process_file(file_path)

    def _wait_for_stable_file(self, file_path: Path, timeout: int = 30):
        """Wait until file stops changing (copying complete)"""
        self.logger.debug(f"Waiting for file stabilization: {file_path.name}")

        start_time = time.time()
        last_size = -1
        stable_count = 0

        while time.time() - start_time < timeout:
            try:
                if not file_path.exists():
                    time.sleep(1)
                    continue

                current_size = file_path.stat().st_size

                if current_size == last_size and current_size > 0:
                    stable_count += 1
                    if stable_count >= 2:  # Stable for 2 seconds
                        self.logger.debug(f"File {file_path.name} stabilized ({current_size} bytes)")
                        return
                else:
                    stable_count = 0

                last_size = current_size
                time.sleep(1)

            except Exception as e:
                self.logger.warning(f"Error checking file {file_path.name}: {e}")
                time.sleep(1)

        self.logger.warning(f"File {file_path.name} did not stabilize within {timeout}s")

    def _process_file(self, file_path: Path):
        """Process a markdown file"""
        self.processing_files.add(str(file_path))

        try:
            self.logger.info(f"Processing: {file_path.name}")

            # Chunk the file
            chunks = self.chunker.chunk_file(file_path)
            self.logger.info(f"Split into {len(chunks)} chunks")

            # Upload chunks (in parallel)
            file_ids = self.uploader.upload_chunks(
                chunks, file_path.name,
                parallel_workers=self.parallel_uploads
            )

            if file_ids:
                self.db.mark_processed(file_path, status="success", file_ids=file_ids)
                self.logger.info(f"Successfully processed {file_path.name}")
            else:
                self.db.mark_processed(file_path, status="failed", error="No chunks uploaded")
                self.logger.error(f"Failed to upload any chunks for {file_path.name}")

        except Exception as e:
            self.logger.error(f"Error processing {file_path.name}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            self.db.mark_processed(file_path, status="failed", error=str(e))

        finally:
            self.processing_files.discard(str(file_path))

    def process_existing_file(self, file_path: Path):
        """Process an existing file (called during startup scan)"""
        self._process_file(file_path)


def scan_existing_files(
    watch_folder: Path,
    db: ProcessedFilesDB,
    handler: MarkdownFileHandler,
    logger: logging.Logger
):
    """Scan and process existing files on startup"""
    logger.info("Scanning existing files...")

    if not watch_folder.exists():
        logger.warning(f"Watch folder does not exist: {watch_folder}")
        return

    md_files = list(watch_folder.glob("*.md"))
    logger.info(f"Found {len(md_files)} markdown files")

    for file_path in md_files:
        if not file_path.exists():
            continue

        if db.is_processed(file_path):
            logger.info(f"Already processed: {file_path.name}")
        else:
            logger.info(f"Unprocessed file: {file_path.name}")
            handler.process_existing_file(file_path)


def setup_logging(log_level: str) -> logging.Logger:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('filetorag')


def main():
    """Main entry point"""
    # Load configuration
    config = Config.from_env()

    # Setup logging
    logger = setup_logging(config.log_level)

    logger.info("=" * 60)
    logger.info("FileToRag Service")
    logger.info("=" * 60)

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        sys.exit(1)

    # Create watch folder if needed
    config.watch_folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"Watch folder: {config.watch_folder}")

    # Create data folder if needed
    config.data_dir.mkdir(parents=True, exist_ok=True)

    # Initialize components
    logger.info(f"Connecting to OpenWebUI at {config.openwebui_url}...")
    client = OpenWebUIClient(config.openwebui_url, config.openwebui_api_key)

    if not client.health_check():
        logger.error("Cannot connect to OpenWebUI. Is it running?")
        sys.exit(1)

    logger.info("OpenWebUI connection OK")

    uploader = RAGUploader(client, config.kb_name)
    logger.info(f"Knowledge Base: {config.kb_name}")

    chunker = MarkdownChunker(
        chunk_by_headers=config.chunk_by_headers,
        chunk_size_lines=config.chunk_size_lines
    )
    logger.info(f"Chunking: {'by headers' if config.chunk_by_headers else 'by lines'} "
                f"(max {config.chunk_size_lines} lines)")
    logger.info(f"Parallel uploads: {config.parallel_uploads} workers")

    db = ProcessedFilesDB(config.data_dir / 'processed_files.json')
    stats = db.get_stats()
    logger.info(f"Processed files: {stats}")

    # Create file handler
    handler = MarkdownFileHandler(
        db, chunker, uploader, logger,
        parallel_uploads=config.parallel_uploads
    )

    # Scan existing files
    scan_existing_files(config.watch_folder, db, handler, logger)

    # Setup watchdog observer
    observer = Observer()
    observer.schedule(handler, str(config.watch_folder), recursive=False)
    observer.start()

    logger.info(f"Monitoring: {config.watch_folder.absolute()}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")
        observer.stop()

    observer.join()

    # Final stats
    stats = db.get_stats()
    logger.info(f"Final stats: {stats}")
    logger.info("Service stopped")


if __name__ == "__main__":
    main()
