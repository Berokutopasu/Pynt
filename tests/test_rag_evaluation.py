"""
Compatibility shim.

RAG tests have been split into:
- tests/test_rag_retrieval_offline.py
- tests/test_rag_evaluation_online.py
"""

import pytest

pytest.skip(
    "Use tests/test_rag_retrieval_offline.py (offline) or tests/test_rag_evaluation_online.py (online)",
    allow_module_level=True,
)
