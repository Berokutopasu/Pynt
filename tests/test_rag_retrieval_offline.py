"""
Offline tests for RAG retrieval behavior.

These tests validate indexing and retrieval quality without any external LLM/API call.
"""

import sys
from pathlib import Path

import pytest


server_path = Path(__file__).parent.parent / "server"
sys.path.insert(0, str(server_path))

from service.rag_service import RAGService


pytestmark = [pytest.mark.integration, pytest.mark.rag_offline]


@pytest.fixture(scope="module")
def rag_service():
    """Initialize RAGService over the server codebase for deterministic offline checks."""
    service = RAGService()
    project_path = str(Path(__file__).parent.parent / "server")
    service.ingest_project(project_path, language="python")
    return service


def test_vector_store_initialized(rag_service):
    """RAG vector store should be available after ingest_project."""
    assert rag_service.vector_store is not None


def test_similarity_search_returns_documents(rag_service):
    """Direct FAISS similarity search should return chunks for a relevant query."""
    query = "how security analysis and semgrep are executed"
    docs = rag_service.vector_store.similarity_search(query, k=3)

    assert len(docs) > 0, "No documents retrieved from FAISS"
    assert len(docs) <= 3, "Retrieved more documents than requested"

    combined_text = " ".join(doc.page_content.lower() for doc in docs)
    relevance_keywords = ["security", "semgrep", "analysis", "agent"]
    matches = sum(1 for kw in relevance_keywords if kw in combined_text)

    assert matches >= 1, "Retrieved chunks do not look relevant to the query"


def test_retrieve_context_returns_non_empty_string(rag_service):
    """High-level retrieve_context should return a non-empty context string."""
    query = "How does the backend expose analysis endpoints?"
    context = rag_service.retrieve_context(query, k=3)

    assert isinstance(context, str)
    assert context.strip(), "retrieve_context returned an empty string"
