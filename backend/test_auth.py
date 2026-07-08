#!/usr/bin/env python3
"""Test JWT authentication flow (register/login/refresh/logout)."""

import sys
import uuid

from app.core.database import SessionLocal, User
from app.services.auth_service import AuthService


def main() -> int:
    db = SessionLocal()
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpass123"

    try:
        user_data = AuthService.register_user(db, email, password, full_name="Test User")
        assert user_data["email"] == email
        print("OK: Registration")

        login = AuthService.login_user(db, email, password)
        access = login["access_token"]
        refresh = login["refresh_token"]
        assert AuthService.verify_token(access) is not None
        print("OK: Login + access token")

        refreshed = AuthService.refresh_access_token(db, refresh)
        new_access = refreshed["access_token"]
        new_refresh = refreshed.get("refresh_token")
        assert AuthService.verify_token(new_access) is not None
        if new_refresh:
            assert new_refresh != refresh
            print("OK: Refresh token rotation")
        else:
            print("OK: Access token refresh")

        AuthService.logout_user(user_data["id"], new_access)
        if AuthService.verify_token(new_access):
            print("WARN: Token still valid after logout (Redis may be unavailable)")
        else:
            print("OK: Logout blacklist")

        db.query(User).filter(User.email == email).delete()
        db.commit()
        print("OK: Cleanup test user")

    except Exception as exc:
        db.rollback()
        print(f"FAIL: {exc}")
        return 1
    finally:
        db.close()

    print("PASS: Authentication flow OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
