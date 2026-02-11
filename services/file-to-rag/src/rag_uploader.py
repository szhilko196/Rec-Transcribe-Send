"""
RAG Uploader

Uploads markdown chunks to OpenWebUI Knowledge Base.
Supports parallel uploads for better GPU utilization.
"""

import logging
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

from .openwebui_client import OpenWebUIClient
from .markdown_chunker import Chunk

logger = logging.getLogger(__name__)


class RAGUploader:
    """Uploads chunks to OpenWebUI Knowledge Base"""

    def __init__(self, client: OpenWebUIClient, kb_name: str):
        """
        Initialize uploader

        Args:
            client: OpenWebUIClient instance
            kb_name: Knowledge Base name to upload to
        """
        self.client = client
        self.kb_name = kb_name
        self._kb_id: Optional[str] = None

    def ensure_knowledge_base(self) -> str:
        """
        Get or create Knowledge Base

        Returns:
            str: Knowledge Base ID
        """
        if self._kb_id:
            return self._kb_id

        # Try to find existing KB
        kb = self.client.get_knowledge_base_by_name(self.kb_name)
        if kb:
            self._kb_id = kb['id']
            logger.info(f"Found existing Knowledge Base '{self.kb_name}' (ID: {self._kb_id})")
            return self._kb_id

        # Create new KB
        logger.info(f"Creating Knowledge Base '{self.kb_name}'...")
        self._kb_id = self.client.create_knowledge_base(
            name=self.kb_name,
            description=f"Files uploaded by FileToRag service"
        )
        logger.info(f"Created Knowledge Base '{self.kb_name}' (ID: {self._kb_id})")
        return self._kb_id

    def upload_chunks(
        self,
        chunks: List[Chunk],
        source_file: str,
        parallel_workers: int = 4,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> List[str]:
        """
        Upload all chunks for a file to Knowledge Base (in parallel)

        Args:
            chunks: List of Chunk objects to upload
            source_file: Original source file name (for logging)
            parallel_workers: Number of parallel upload workers (default: 4)
            max_retries: Maximum retry attempts per chunk
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            List of uploaded file IDs
        """
        kb_id = self.ensure_knowledge_base()
        file_ids = []
        failed_chunks = []
        completed_count = 0
        total_chunks = len(chunks)

        logger.info(f"Uploading {total_chunks} chunks from '{source_file}' "
                    f"(using {parallel_workers} parallel workers)...")

        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            # Submit all chunks for parallel processing
            future_to_chunk = {
                executor.submit(
                    self._upload_chunk_with_retry,
                    chunk, kb_id, max_retries, retry_delay
                ): chunk
                for chunk in chunks
            }

            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                completed_count += 1

                try:
                    file_id = future.result()
                    if file_id:
                        file_ids.append(file_id)
                        logger.info(f"Progress: {completed_count}/{total_chunks} "
                                    f"- Chunk {chunk.index} uploaded")
                    else:
                        failed_chunks.append(chunk.index)
                        logger.error(f"Progress: {completed_count}/{total_chunks} "
                                     f"- Chunk {chunk.index} failed")
                except Exception as e:
                    failed_chunks.append(chunk.index)
                    logger.error(f"Progress: {completed_count}/{total_chunks} "
                                 f"- Chunk {chunk.index} error: {e}")

        if failed_chunks:
            logger.warning(f"Failed chunks: {sorted(failed_chunks)}")

        logger.info(f"Successfully uploaded {len(file_ids)}/{total_chunks} chunks from '{source_file}'")
        return file_ids

    def _upload_chunk_with_retry(
        self,
        chunk: Chunk,
        kb_id: str,
        max_retries: int,
        retry_delay: float
    ) -> Optional[str]:
        """
        Upload a single chunk with retry logic

        Args:
            chunk: Chunk to upload
            kb_id: Knowledge Base ID
            max_retries: Maximum retry attempts
            retry_delay: Initial delay between retries

        Returns:
            File ID if successful, None otherwise
        """
        delay = retry_delay

        for attempt in range(max_retries):
            try:
                return self._upload_chunk(chunk, kb_id)
            except Exception as e:
                logger.warning(
                    f"Upload attempt {attempt + 1}/{max_retries} failed for "
                    f"chunk {chunk.index}/{chunk.total}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

        return None

    def _upload_chunk(self, chunk: Chunk, kb_id: str) -> str:
        """
        Upload a single chunk to Knowledge Base

        Args:
            chunk: Chunk to upload
            kb_id: Knowledge Base ID

        Returns:
            File ID

        Raises:
            Exception: If upload fails
        """
        # Create temp file for chunk
        # Use source file name with chunk number for identification
        base_name = Path(chunk.source_file).stem
        chunk_filename = f"{base_name}_chunk{chunk.index:02d}.md"

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.md',
            prefix=f'{base_name}_',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(chunk.with_metadata())
            temp_path = Path(f.name)

        try:
            # Upload file
            logger.debug(f"Uploading chunk {chunk.index}/{chunk.total}: {chunk_filename}")
            file_id = self.client.upload_file(temp_path)

            # Wait for processing (embedding generation)
            logger.debug(f"Waiting for processing of {chunk_filename}...")
            self.client.wait_for_processing(file_id, timeout=120)

            # Add to Knowledge Base
            logger.debug(f"Adding {chunk_filename} to KB {kb_id}...")
            self.client.add_file_to_knowledge_base(kb_id, file_id)

            logger.info(f"Uploaded chunk {chunk.index}/{chunk.total} (ID: {file_id})")
            return file_id

        finally:
            # Clean up temp file
            try:
                temp_path.unlink()
            except Exception:
                pass
