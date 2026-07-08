import jwt
import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.core.database import User
from app.core.config import config
from app.core.redis_client import redis_client, RedisKeys
import logging

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )

    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        expires = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "exp": expires,
        }
        return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id: str, email: str) -> str:
        expires = datetime.utcnow() + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "exp": expires,
        }
        return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        try:
            payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])

            if redis_client:
                blacklist_key = RedisKeys.AUTH_BLACKLIST.format(token=token)
                if redis_client.exists(blacklist_key):
                    return None

            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    @staticmethod
    def blacklist_token(token: str, expires_in: int = 3600):
        if redis_client:
            try:
                redis_client.setex(
                    RedisKeys.AUTH_BLACKLIST.format(token=token),
                    expires_in,
                    "revoked",
                )
            except Exception as e:
                logger.error(f"Failed to blacklist token: {e}")

    @staticmethod
    def _ensure_active(user: User):
        if not user.is_active:
            raise ValueError("User account is disabled")

    @staticmethod
    def register_user(db: Session, email: str, password: str, full_name: str = None) -> Dict:
        if db.query(User).filter(User.email == email).first():
            raise ValueError("User already exists")

        hashed_password = AuthService.hash_password(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": getattr(user, "role", "user"),
        }

    @staticmethod
    def login_user(db: Session, email: str, password: str) -> Dict:
        user = db.query(User).filter(User.email == email).first()
        if not user or not AuthService.verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")

        AuthService._ensure_active(user)

        access_token = AuthService.create_access_token(str(user.id), user.email)
        refresh_token = AuthService.create_refresh_token(str(user.id), user.email)

        if redis_client:
            try:
                redis_client.setex(
                    RedisKeys.AUTH_REFRESH.format(user_id=str(user.id)),
                    config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
                    refresh_token,
                )
            except Exception as e:
                logger.error(f"Failed to store refresh token: {e}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": getattr(user, "role", "user"),
            },
        }

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Dict:
        payload = AuthService.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid refresh token")

        if redis_client:
            try:
                stored_token = redis_client.get(RedisKeys.AUTH_REFRESH.format(user_id=user_id))
            except Exception as e:
                logger.error(f"Failed to get refresh token: {e}")
                stored_token = None

            if stored_token != refresh_token:
                raise ValueError("Invalid refresh token")

        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise ValueError("Invalid refresh token")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            raise ValueError("User not found")

        AuthService._ensure_active(user)

        new_access_token = AuthService.create_access_token(str(user.id), user.email)
        new_refresh_token = AuthService.create_refresh_token(str(user.id), user.email)

        if redis_client:
            try:
                AuthService.blacklist_token(refresh_token, config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)
                redis_client.setex(
                    RedisKeys.AUTH_REFRESH.format(user_id=str(user.id)),
                    config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
                    new_refresh_token,
                )
            except Exception as e:
                logger.error("Failed to rotate refresh token: %s", e)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    def logout_user(user_id: str, access_token: str):
        try:
            payload = jwt.decode(access_token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
            exp = payload.get("exp")
            if exp:
                expires_in = max(0, int(exp - datetime.utcnow().timestamp()))
                AuthService.blacklist_token(access_token, expires_in)
        except jwt.InvalidTokenError:
            pass

        if redis_client:
            try:
                redis_client.delete(RedisKeys.AUTH_REFRESH.format(user_id=user_id))
            except Exception as e:
                logger.error(f"Failed to delete refresh token: {e}")
