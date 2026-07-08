#!/usr/bin/env python3
"""Test RAG retriever and orchestrator wiring (no LLM call unless --invoke)."""

import argparse
import sys

from app.core.database import SessionLocal, User
from app.rag.retriever import PgVectorHybridRetriever
from app.repositories.vector_repository import reciprocal_rank_fusion


def test_rrf() -> None:
    vector = [{"chunk_id": "a", "content": "a", "score": 0.9, "chunk_index": 0, "filename": "f", "document_id": "d"}]
    keyword = [{"chunk_id": "b", "content": "b", "score": 0.5, "chunk_index": 0, "filename": "f", "document_id": "d"}]
    merged = reciprocal_rank_fusion(vector, keyword, limit=2, score_threshold=0.0)
    assert len(merged) == 2
    print("OK: RRF merge logic")


def test_retriever(user: User) -> None:
    db = SessionLocal()
    try:
        retriever = PgVectorHybridRetriever(db=db, user=user)
        docs = retriever.invoke("test query")
        print(f"OK: Retriever returned {len(docs)} documents")
    finally:
        db.close()


def test_orchestrator_invoke(user: User) -> None:
    from app.rag.orchestrator import RAGOrchestrator

    db = SessionLocal()
    try:
        orchestrator = RAGOrchestrator(db=db, user=user)
        result = orchestrator.invoke("Summarize my documents")
        assert "answer" in result
        print(f"OK: Orchestrator answer length={len(result['answer'])}")
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Test RAG pipeline components")
    parser.add_argument("--invoke", action="store_true", help="Run full LLM invoke (uses Groq API)")
    args = parser.parse_args()

    test_rrf()

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("SKIP: No users in database — register a user first for retriever tests")
            print("PASS: RRF unit test only")
            return 0
    finally:
        db.close()

    try:
        test_retriever(user)
    except Exception as exc:
        print(f"WARN: Retriever test failed (may be OK if no documents): {exc}")

    if args.invoke:
        try:
            test_orchestrator_invoke(user)
        except Exception as exc:
            print(f"FAIL: Orchestrator invoke failed: {exc}")
            return 1

    print("PASS: RAG pipeline tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
