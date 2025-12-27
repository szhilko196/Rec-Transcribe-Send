"""
RAGFlow API Client
Wrapper for RAGFlow REST API operations
"""

import os
import requests
from typing import Dict, List, Optional
from pathlib import Path
import json


class RAGFlowClient:
    """Client for interacting with RAGFlow API"""

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None
    ):
        """
        Initialize RAGFlow client

        Args:
            base_url: RAGFlow API base URL (default: http://localhost:9381)
            api_key: RAGFlow API key (from environment or UI)
        """
        self.base_url = base_url or os.getenv("RAGFLOW_URL", "http://localhost:9381")
        self.api_key = api_key or os.getenv("RAGFLOW_API_KEY")

        if not self.api_key:
            raise ValueError("RAGFLOW_API_KEY not set in environment")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_dataset(
        self,
        name: str,
        description: str = "",
        embedding_model: str = "BAAI/bge-m3",
        chunk_method: str = "knowledge_graph",
        parser_config: Dict = None
    ) -> str:
        """
        Create a new dataset in RAGFlow

        Args:
            name: Dataset name (meeting folder name)
            description: Dataset description
            embedding_model: Embedding model to use
            chunk_method: Chunking method
            parser_config: Parser configuration

        Returns:
            dataset_id: ID of created dataset
        """
        endpoint = f"{self.base_url}/api/v1/datasets"

        payload = {
            "name": name,
            "description": description,
            "embedding_model": embedding_model,
            "chunk_method": chunk_method,
            "parser_config": parser_config or {}
        }

        response = requests.post(
            endpoint,
            headers=self.headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        dataset_id = data.get("data", {}).get("dataset_id") or data.get("id")

        print(f"[RAGFlow] Created dataset: {name} (ID: {dataset_id})")
        return dataset_id

    def upload_document(
        self,
        dataset_id: str,
        file_path: Path,
        filename: str = None
    ) -> str:
        """
        Upload a document to a dataset

        Args:
            dataset_id: Dataset ID
            file_path: Path to file to upload
            filename: Custom filename (optional)

        Returns:
            document_id: ID of uploaded document
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        endpoint = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents"

        # Prepare file upload
        files = {
            "file": (
                filename or file_path.name,
                open(file_path, 'rb'),
                "text/plain"
            )
        }

        # Remove Content-Type from headers for multipart/form-data
        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = requests.post(
            endpoint,
            headers=headers,
            files=files,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        document_id = data.get("data", {}).get("document_id") or data.get("id")

        print(f"[RAGFlow] Uploaded document: {file_path.name} (ID: {document_id})")
        return document_id

    def parse_documents(
        self,
        dataset_id: str,
        document_ids: List[str] = None
    ) -> bool:
        """
        Trigger parsing and chunking for documents

        Args:
            dataset_id: Dataset ID
            document_ids: List of document IDs (if None, parse all)

        Returns:
            success: True if parsing started successfully
        """
        endpoint = f"{self.base_url}/api/v1/datasets/{dataset_id}/parse"

        payload = {
            "document_ids": document_ids or []
        }

        response = requests.post(
            endpoint,
            headers=self.headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        print(f"[RAGFlow] Triggered parsing for dataset {dataset_id}")
        return True

    def wait_for_parsing(
        self,
        dataset_id: str,
        document_id: str,
        timeout: int = 300,
        check_interval: int = 5
    ) -> bool:
        """
        Wait for document parsing to complete

        Args:
            dataset_id: Dataset ID
            document_id: Document ID
            timeout: Max wait time in seconds
            check_interval: Check interval in seconds

        Returns:
            success: True if parsing completed successfully
        """
        import time

        endpoint = f"{self.base_url}/api/v1/datasets/{dataset_id}/documents/{document_id}"

        start_time = time.time()

        while time.time() - start_time < timeout:
            response = requests.get(
                endpoint,
                headers=self.headers,
                timeout=10
            )

            response.raise_for_status()
            data = response.json()

            status = data.get("data", {}).get("status") or data.get("status")

            if status == "completed":
                print(f"[RAGFlow] Document {document_id} parsing completed")
                return True
            elif status == "failed":
                print(f"[RAGFlow] Document {document_id} parsing failed")
                return False

            time.sleep(check_interval)

        print(f"[RAGFlow] Document {document_id} parsing timeout")
        return False

    def search(
        self,
        dataset_id: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Search within a dataset

        Args:
            dataset_id: Dataset ID
            query: Search query
            top_k: Number of results
            similarity_threshold: Minimum similarity score

        Returns:
            results: List of search results
        """
        endpoint = f"{self.base_url}/api/v1/datasets/{dataset_id}/retrieval"

        payload = {
            "question": query,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold
        }

        response = requests.post(
            endpoint,
            headers=self.headers,
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        results = data.get("data", {}).get("chunks") or data.get("chunks", [])

        return results

    def chat(
        self,
        question: str,
        dataset_ids: List[str] = None,
        top_k: int = 5,
        stream: bool = False
    ) -> str:
        """
        Chat with datasets (retrieval + generation)

        Args:
            question: User question
            dataset_ids: List of dataset IDs to search (or ["all"])
            top_k: Number of retrieved chunks
            stream: Stream response

        Returns:
            answer: Generated answer
        """
        endpoint = f"{self.base_url}/api/v1/chat"

        payload = {
            "question": question,
            "dataset_ids": dataset_ids or ["all"],
            "top_k": top_k,
            "stream": stream
        }

        response = requests.post(
            endpoint,
            headers=self.headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()

        answer = data.get("data", {}).get("answer") or data.get("answer", "")

        return answer

    def list_datasets(self) -> List[Dict]:
        """
        List all datasets

        Returns:
            datasets: List of dataset metadata
        """
        endpoint = f"{self.base_url}/api/v1/datasets"

        response = requests.get(
            endpoint,
            headers=self.headers,
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        datasets = data.get("data", {}).get("datasets") or data.get("datasets", [])

        return datasets

    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a dataset

        Args:
            dataset_id: Dataset ID to delete

        Returns:
            success: True if deleted successfully
        """
        endpoint = f"{self.base_url}/api/v1/datasets/{dataset_id}"

        response = requests.delete(
            endpoint,
            headers=self.headers,
            timeout=30
        )

        response.raise_for_status()

        print(f"[RAGFlow] Deleted dataset: {dataset_id}")
        return True

    def health_check(self) -> bool:
        """
        Check if RAGFlow API is accessible

        Returns:
            healthy: True if API is responding
        """
        try:
            endpoint = f"{self.base_url}/api/v1/health"
            response = requests.get(endpoint, timeout=10)
            return response.status_code == 200
        except:
            return False


# CLI for testing
if __name__ == "__main__":
    import sys

    # Test RAGFlow connection
    client = RAGFlowClient()

    if not client.health_check():
        print("ERROR: RAGFlow API is not accessible")
        print(f"  URL: {client.base_url}")
        print("  Make sure RAGFlow is running:")
        print("  cd services/RAG-search && docker-compose -f docker-compose.ragflow.yml up -d")
        sys.exit(1)

    print("✓ RAGFlow API is accessible")

    # List datasets
    datasets = client.list_datasets()
    print(f"✓ Found {len(datasets)} datasets")

    for dataset in datasets[:5]:
        print(f"  - {dataset.get('name')} (ID: {dataset.get('id')})")
