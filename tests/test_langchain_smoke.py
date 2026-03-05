"""
LangChain smoke tests for Pynt.

Usage:
- RAG smoke test runs by default.
- LLM smoke test is opt-in to avoid flaky CI/network failures:
  set RUN_LANGCHAIN_LLM_SMOKE=1
"""

from __future__ import annotations

import os
import sys
import asyncio
from pathlib import Path

import pytest

# Import server modules from workspace layout
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "server"
sys.path.insert(0, str(SERVER_ROOT))

from service.rag_service import RAGService
from agents.security_agent import PythonSecurityAgent


@pytest.mark.integration
@pytest.mark.slow
def test_langchain_rag_smoke() -> None:
    """RAG should ingest project files and return non-empty context."""
    rag = RAGService()
    rag.ingest_project(str(SERVER_ROOT), language="python")

    context = rag.retrieve_context("sql injection sanitization", k=1)

    assert isinstance(context, str)
    assert context.strip(), "RAG context is empty after ingestion"


@pytest.mark.integration
@pytest.mark.slow
def test_langchain_llm_smoke() -> None:
    """ChatGroq call through LangChain should succeed when explicitly enabled."""
    if os.getenv("RUN_LANGCHAIN_LLM_SMOKE", "0") != "1":
        pytest.skip("Set RUN_LANGCHAIN_LLM_SMOKE=1 to run live Groq smoke test")

    agent = PythonSecurityAgent()
    if not agent.groq_keys or all(k == "dummy_key" for k in agent.groq_keys):
        pytest.skip("No valid GROQ_API_KEYS configured")

    response = asyncio.run(agent.llm.ainvoke("Rispondi con solo: OK"))
    content = str(getattr(response, "content", response)).strip()

    assert content
