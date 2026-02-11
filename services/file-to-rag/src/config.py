"""
Configuration for FileToRag Service

Loads settings from environment variables with defaults.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """FileToRag service configuration"""

    # OpenWebUI connection
    openwebui_url: str
    openwebui_api_key: str

    # Knowledge Base
    kb_name: str

    # Watch folder
    watch_folder: Path

    # Chunking settings
    chunk_by_headers: bool
    chunk_size_lines: int

    # Parallel upload settings
    parallel_uploads: int

    # Logging
    log_level: str

    # Paths
    root_dir: Path
    data_dir: Path

    @classmethod
    def from_env(cls, root_dir: Optional[Path] = None) -> 'Config':
        """
        Load configuration from environment variables

        Args:
            root_dir: Project root directory (auto-detected if not provided)

        Returns:
            Config instance
        """
        if root_dir is None:
            # Go up from src/ to file-to-rag/ to services/ to project root
            root_dir = Path(__file__).parent.parent.parent.parent

        # OpenWebUI connection
        openwebui_url = os.getenv('OPENWEBUI_URL', 'http://localhost:3000')
        openwebui_api_key = os.getenv('OPENWEBUI_API_KEY', '')

        # Knowledge Base name
        kb_name = os.getenv('FILETORAG_KB_NAME', 'MyFiles')

        # Watch folder (relative to project root or absolute)
        watch_folder_str = os.getenv('FILETORAG_WATCH_FOLDER', 'data/FileToRag')
        watch_folder = Path(watch_folder_str)
        if not watch_folder.is_absolute():
            watch_folder = root_dir / watch_folder

        # Chunking settings
        chunk_by_headers_str = os.getenv('FILETORAG_CHUNK_BY_HEADERS', 'true').lower()
        chunk_by_headers = chunk_by_headers_str in ('true', '1', 'yes')

        chunk_size_lines = int(os.getenv('FILETORAG_CHUNK_SIZE_LINES', '150'))

        # Parallel upload settings
        parallel_uploads = int(os.getenv('FILETORAG_PARALLEL_UPLOADS', '4'))

        # Logging
        log_level = os.getenv('FILETORAG_LOG_LEVEL', 'INFO').upper()

        # Data directory for this service
        data_dir = Path(__file__).parent.parent / 'data'

        return cls(
            openwebui_url=openwebui_url,
            openwebui_api_key=openwebui_api_key,
            kb_name=kb_name,
            watch_folder=watch_folder,
            chunk_by_headers=chunk_by_headers,
            chunk_size_lines=chunk_size_lines,
            parallel_uploads=parallel_uploads,
            log_level=log_level,
            root_dir=root_dir,
            data_dir=data_dir
        )

    def validate(self) -> list:
        """
        Validate configuration

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not self.openwebui_api_key or self.openwebui_api_key == 'your-api-key-here':
            errors.append("OPENWEBUI_API_KEY is not set. Get it from OpenWebUI: Settings > Account > API Keys")

        if not self.openwebui_url:
            errors.append("OPENWEBUI_URL is not set")

        if not self.kb_name:
            errors.append("FILETORAG_KB_NAME is not set")

        if self.chunk_size_lines < 10:
            errors.append("FILETORAG_CHUNK_SIZE_LINES must be at least 10")

        return errors
