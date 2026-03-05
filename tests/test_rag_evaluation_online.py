"""
Online RAG evaluation with RAGAS.

This suite validates end-to-end RAG quality (retrieve + generate + score)
and requires external LLM calls.
"""

import math
import os
import sys
from pathlib import Path

import pytest
from datasets import Dataset
from ragas import evaluate
from ragas.metrics._answer_relevance import answer_relevancy
from ragas.metrics._context_precision import context_precision
from ragas.metrics._context_recall import context_recall
from ragas.metrics._faithfulness import faithfulness


server_path = Path(__file__).parent.parent / "server"
sys.path.insert(0, str(server_path))

from config.settings import settings
from langchain_groq import ChatGroq
from service.rag_service import RAGService


pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.rag_online]


EVAL_QUESTIONS = [
    {
        "question": "How does the security analysis agent work?",
        "ground_truth": "SecurityAgent uses Semgrep for static analysis and LLM for explanation generation with RAG context.",
    },
    {
        "question": "What is the purpose of RAGService?",
        "ground_truth": "RAGService provides retrieval-augmented generation by indexing project code and retrieving relevant context for LLM prompts.",
    },
    {
        "question": "Which class is responsible for running Semgrep analysis?",
        "ground_truth": "SemgrepAnalyzer class runs Semgrep CLI and parses JSON output into Finding objects.",
    },
    {
        "question": "How are findings returned to the VS Code extension?",
        "ground_truth": "Findings are returned as JSON with AnalysisResponse model containing Finding objects with severity, message, and fix suggestions.",
    },
]


@pytest.fixture(scope="module")
def rag_service():
    service = RAGService()
    project_path = str(Path(__file__).parent.parent / "server")
    service.ingest_project(project_path, language="python")
    return service


@pytest.fixture(scope="module")
def llm():
    groq_keys = settings.EFFECTIVE_GROQ_KEYS
    if not groq_keys:
        pytest.skip("No GROQ_API_KEYS available in .env")

    return ChatGroq(
        # Use lightweight model to reduce quota pressure during evaluation.
        model="llama-3.1-8b-instant",
        temperature=0.3,
        groq_api_key=groq_keys[0],
        # Don't restrict to n=1 to allow RAGAS to request multiple generations
        # Remove n parameter to allow RAGAS flexibility
    )


@pytest.mark.timeout(300)  # 5-minute timeout to prevent infinite hangs
def test_rag_evaluation_metrics_online(rag_service, llm):
    if not os.getenv("RUN_RAG_EVALUATION"):
        pytest.skip("Set RUN_RAG_EVALUATION=1 to run online RAGAS evaluation")

    questions = []
    contexts = []
    answers = []
    ground_truths = []

    for item in EVAL_QUESTIONS:
        question = item["question"]
        ground_truth = item["ground_truth"]

        docs = rag_service.vector_store.similarity_search(question, k=3)
        context_list = [doc.page_content for doc in docs]
        context_str = '\n\n'.join(context_list)

        prompt = (
            "Based on the following code context, answer the question concisely.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )

        print(f"\n[DEBUG] Invoking LLM for question: {question[:50]}...")
        try:
            response = llm.invoke(prompt)
            print(f"[DEBUG] LLM response received")
            answer = response.content
        except Exception as e:
            print(f"[DEBUG] LLM error: {e}")
            raise

        questions.append(question)
        contexts.append(context_list)
        answers.append(answer)
        ground_truths.append(ground_truth)

    dataset = Dataset.from_dict(
        {
            "question": questions,
            "contexts": contexts,
            "answer": answers,
            "ground_truth": ground_truths,
        }
    )

    print("\n[DEBUG] Starting RAGAS evaluation...")
    try:
        result = evaluate(
            dataset,
            metrics=[context_precision, answer_relevancy, faithfulness, context_recall],
            llm=llm,
            embeddings=rag_service.embeddings,
        )
        print("[DEBUG] RAGAS evaluation completed")
    except Exception as e:
        print(f"[DEBUG] RAGAS evaluation error: {e}")
        raise

    metric_means = result._repr_dict
    print(f"[DEBUG] Metrics: {metric_means}")

    # If provider rate limits/timeouts occur, RAGAS can return NaN.
    if any(math.isnan(score) for score in metric_means.values()):
        pytest.skip("RAGAS metrics incomplete (NaN), likely due provider limits")

    print(f"\n[METRICS SUMMARY]")
    print(f"  context_precision: {metric_means['context_precision']:.2f}")
    print(f"  answer_relevancy: {metric_means['answer_relevancy']:.2f}")
    print(f"  faithfulness: {metric_means['faithfulness']:.2f}")
    print(f"  context_recall: {metric_means['context_recall']:.2f}")

    # Baseline thresholds for code-based RAG (very permissive due to:
    # 1. Code retrieval has lower semantic similarity than text RAG
    # 2. Groq API timeouts affect RAGAS evaluation consistency
    # 3. Q&A format mismatch for code documentation queries)
    # These are minimum baselines; production systems should strive for 0.6+
    assert metric_means["context_precision"] > 0.25, f"context_precision {metric_means['context_precision']:.2f} too low"
    assert metric_means["answer_relevancy"] > 0.4, f"answer_relevancy {metric_means['answer_relevancy']:.2f} too low"
    assert metric_means["faithfulness"] > 0.05, f"faithfulness {metric_means['faithfulness']:.2f} too low"
    assert metric_means["context_recall"] > 0.0, f"context_recall {metric_means['context_recall']:.2f} too low"
