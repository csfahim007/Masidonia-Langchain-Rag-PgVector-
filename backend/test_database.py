#!/usr/bin/env python3
"""Test PostgreSQL / Neon connection and pgvector extension."""

import sys

from sqlalchemy import text

from app.core.database import engine, SessionLocal, User


def main() -> int:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            ext = conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            ).fetchone()
            if not ext:
                print("WARN: pgvector extension not installed (run migrations/001_enable_pgvector.sql)")
            else:
                print("OK: pgvector extension enabled")
    except Exception as exc:
        print(f"FAIL: Database connection failed: {exc}")
        return 1

    db = SessionLocal()
    try:
        count = db.query(User).count()
        print(f"OK: Database connected ({count} users in database)")
    except Exception as exc:
        print(f"FAIL: Query failed: {exc}")
        return 1
    finally:
        db.close()

    print("PASS: PostgreSQL connection OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
