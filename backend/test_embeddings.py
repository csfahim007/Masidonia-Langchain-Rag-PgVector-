#!/usr/bin/env python3
"""Test HuggingFace embedding generation."""

import sys

from app.core.config import config
from app.rag.embeddings import embed_documents, embed_query


def main() -> int:
    try:
        docs = embed_documents(["Masidonia is a RAG document intelligence platform."])
        query = embed_query("What is Masidonia?")
    except Exception as exc:
        print(f"FAIL: Embedding generation failed: {exc}")
        return 1

    if len(docs) != 1 or len(docs[0]) != config.EMBEDDING_DIM:
        print(f"FAIL: Expected 1 x {config.EMBEDDING_DIM} document embedding")
        return 1

    if len(query) != config.EMBEDDING_DIM:
        print(f"FAIL: Expected query embedding dim {config.EMBEDDING_DIM}, got {len(query)}")
        return 1

    print(f"OK: Model={config.EMBEDDING_MODEL}, dim={config.EMBEDDING_DIM}")
    print("PASS: Embedding generation OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
