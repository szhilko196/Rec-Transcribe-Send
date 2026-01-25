#!/usr/bin/env python3
"""
OpenWebUI API Client

Wrapper for OpenWebUI Knowledge Base API operations:
- Health checks
- File uploads with async processing
- Knowledge Base management
- Search functionality
"""

import requests
import time
from pathlib import Path
from typing import Optional, Dict, List


class OpenWebUIClient:
    """Client for interacting with OpenWebUI API"""

    def __init__(self, base_url: str = "http://localhost:3000", api_key: Optional[str] = None):
        """
        Initialize OpenWebUI client

        Args:
            base_url: OpenWebUI service URL (default: http://localhost:3000)
            api_key: API key for authentication (generate in UI: Settings > Account > API Keys)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {}

        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def health_check(self) -> bool:
        """
        Check if OpenWebUI API is accessible

        Returns:
            bool: True if API is responding, False otherwise
        """
        try:
            # Try to access files endpoint (requires auth but endpoint exists)
            response = requests.get(
                f"{self.base_url}/api/v1/files/",
                headers=self.headers,
                timeout=10
            )
            # 200 = success, 401 = needs auth but server is up
            return response.status_code in [200, 401]
        except Exception:
            return False

    def upload_file(self, file_path: Path) -> str:
        """
        Upload file to OpenWebUI

        Args:
            file_path: Path to file to upload

        Returns:
            str: File ID assigned by OpenWebUI

        Raises:
            FileNotFoundError: If file doesn't exist
            requests.HTTPError: If upload fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f)}
            response = requests.post(
                f"{self.base_url}/api/v1/files/",
                headers=self.headers,
                files=files
            )
            response.raise_for_status()

            data = response.json()
            file_id = data.get('id')

            if not file_id:
                raise Exception(f"No file ID in response: {data}")

            return file_id

    def wait_for_processing(self, file_id: str, timeout: int = 180) -> bool:
        """
        Wait for async file processing to complete

        OpenWebUI processes files asynchronously (embedding generation).
        This method polls the status endpoint until processing completes.

        Args:
            file_id: File ID to check
            timeout: Maximum wait time in seconds (default: 180)

        Returns:
            bool: True if processing completed successfully

        Raises:
            TimeoutError: If processing doesn't complete within timeout
            Exception: If processing fails
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"{self.base_url}/api/v1/files/{file_id}/process/status",
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 404:
                    # Status endpoint might not exist, assume processing is done
                    # OpenWebUI older versions might not have this endpoint
                    print("[INFO] Status endpoint not found, assuming processing complete")
                    return True

                response.raise_for_status()
                status_data = response.json()

                status = status_data.get('status')

                if status == 'completed':
                    return True
                elif status == 'failed':
                    error = status_data.get('error', 'Unknown error')
                    raise Exception(f"File processing failed: {error}")

                # Still processing, wait and retry
                time.sleep(5)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # Endpoint doesn't exist, assume complete
                    return True
                raise

        raise TimeoutError(f"File processing timeout after {timeout}s")

    def create_knowledge_base(self, name: str, description: str = "") -> str:
        """
        Create new Knowledge Base

        Args:
            name: Knowledge Base name
            description: Optional description

        Returns:
            str: Knowledge Base ID

        Raises:
            requests.HTTPError: If creation fails
        """
        response = requests.post(
            f"{self.base_url}/api/v1/knowledge/create",
            headers=self.headers,
            json={"name": name, "description": description}
        )
        response.raise_for_status()

        data = response.json()
        kb_id = data.get('id')

        if not kb_id:
            raise Exception(f"No knowledge base ID in response: {data}")

        return kb_id

    def get_knowledge_base(self, knowledge_id: str) -> Optional[Dict]:
        """
        Get Knowledge Base by ID

        Args:
            knowledge_id: Knowledge Base ID

        Returns:
            dict: Knowledge Base metadata including files, None if not found
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/knowledge/{knowledge_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_knowledge_base_by_name(self, name: str) -> Optional[Dict]:
        """
        Find Knowledge Base by name

        Args:
            name: Knowledge Base name to search for

        Returns:
            dict: Knowledge Base metadata if found, None otherwise
        """
        response = requests.get(
            f"{self.base_url}/api/v1/knowledge/",
            headers=self.headers
        )
        response.raise_for_status()

        knowledge_bases = response.json()

        # Response might be a list or a dict with 'items' or 'data' key
        if isinstance(knowledge_bases, dict):
            knowledge_bases = knowledge_bases.get('items', knowledge_bases.get('data', []))

        for kb in knowledge_bases:
            if kb.get('name') == name:
                return kb

        return None

    def add_file_to_knowledge_base(self, knowledge_id: str, file_id: str):
        """
        Add processed file to Knowledge Base

        CRITICAL: File must be fully processed before calling this.
        Use wait_for_processing() first.

        Args:
            knowledge_id: Knowledge Base ID
            file_id: File ID (from upload_file)

        Raises:
            requests.HTTPError: If adding file fails (e.g., file not processed yet)
        """
        response = requests.post(
            f"{self.base_url}/api/v1/knowledge/{knowledge_id}/file/add",
            headers=self.headers,
            json={"file_id": file_id}
        )
        if response.status_code >= 400:
            error_detail = response.text[:500] if response.text else "No error details"
            raise Exception(f"{response.status_code} Error: {error_detail}")
        response.raise_for_status()

    def delete_knowledge_base(self, knowledge_id: str) -> bool:
        """
        Delete a Knowledge Base

        Args:
            knowledge_id: Knowledge Base ID to delete

        Returns:
            bool: True if deleted successfully

        Raises:
            requests.HTTPError: If deletion fails
        """
        response = requests.delete(
            f"{self.base_url}/api/v1/knowledge/{knowledge_id}/delete",
            headers=self.headers
        )
        response.raise_for_status()
        return True

    def list_files(self) -> List[Dict]:
        """
        List all uploaded files

        Returns:
            list: List of file metadata dicts
        """
        response = requests.get(
            f"{self.base_url}/api/v1/files/",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_files_in_knowledge_base(self, knowledge_id: str) -> List[Dict]:
        """
        Get files associated with a Knowledge Base

        Args:
            knowledge_id: Knowledge Base ID

        Returns:
            list: List of files in the KB (by checking collection_name in file meta)
        """
        all_files = self.list_files()
        kb_files = []
        for f in all_files:
            collection = f.get('meta', {}).get('collection_name', '')
            if collection == knowledge_id:
                kb_files.append(f)
        return kb_files

    def search(
        self,
        query: str,
        knowledge_id: Optional[str] = None,
        top_k: int = 5,
        relevance_threshold: float = 0.3
    ) -> List[Dict]:
        """
        Search knowledge base (placeholder - implementation depends on OpenWebUI API)

        Args:
            query: Search query
            knowledge_id: Optional Knowledge Base ID to search in
            top_k: Number of results to return
            relevance_threshold: Minimum relevance score

        Returns:
            list: Search results

        Note:
            This is a placeholder. OpenWebUI's search API might differ.
            Actual implementation depends on available endpoints.
        """
        # TODO: Implement based on OpenWebUI's actual search API
        # May need to use native query_knowledge_bases tool via conversation API
        raise NotImplementedError(
            "Search API implementation depends on OpenWebUI version. "
            "Use UI (#Meetings syntax) or conversation API for now."
        )

    def list_knowledge_bases(self) -> List[Dict]:
        """
        List all Knowledge Bases

        Returns:
            list: List of Knowledge Base metadata dicts
        """
        response = requests.get(
            f"{self.base_url}/api/v1/knowledge/",
            headers=self.headers
        )
        response.raise_for_status()

        knowledge_bases = response.json()

        # Response might be a list or a dict with 'items' or 'data' key
        if isinstance(knowledge_bases, dict):
            knowledge_bases = knowledge_bases.get('items', knowledge_bases.get('data', []))

        return knowledge_bases

    def get_file_info(self, file_id: str) -> Dict:
        """
        Get file metadata

        Args:
            file_id: File ID

        Returns:
            dict: File metadata
        """
        response = requests.get(
            f"{self.base_url}/api/v1/files/{file_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    # Simple CLI for testing
    import sys
    import os

    api_key = os.getenv("OPENWEBUI_API_KEY")
    base_url = os.getenv("OPENWEBUI_URL", "http://localhost:3000")

    if not api_key:
        print("Error: OPENWEBUI_API_KEY environment variable not set")
        sys.exit(1)

    client = OpenWebUIClient(base_url, api_key)

    # Test health check
    print(f"Testing connection to {base_url}...")
    if client.health_check():
        print("✓ OpenWebUI API is accessible")
    else:
        print("✗ OpenWebUI API is not accessible")
        sys.exit(1)

    # List knowledge bases
    print("\nKnowledge Bases:")
    try:
        kbs = client.list_knowledge_bases()
        for kb in kbs:
            print(f"  - {kb.get('name')} (ID: {kb.get('id')})")
    except Exception as e:
        print(f"  Error: {e}")
