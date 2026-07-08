#!/usr/bin/env python3
"""Test Redis Cloud connection with SSL."""

import sys

from app.core.redis_client import connect_redis, is_redis_available


def main() -> int:
    connect_redis()
    if not is_redis_available():
        print("FAIL: Redis is not available")
        return 1

    from app.core.redis_client import get_redis

    client = get_redis()
    assert client is not None
    client.set("masidonia:test", "ok", ex=30)
    value = client.get("masidonia:test")
    client.delete("masidonia:test")

    if value != "ok":
        print(f"FAIL: Unexpected value {value!r}")
        return 1

    print("PASS: Redis Cloud connection and read/write OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
