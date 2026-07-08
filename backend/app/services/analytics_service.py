from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import Conversation, Document, QueryLog, User


class AnalyticsService:

    @staticmethod
    def get_overview(db: Session, user: User) -> dict:
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)

        total_docs = db.query(Document).filter(Document.user_id == user.id).count()
        ready_docs = (
            db.query(Document)
            .filter(Document.user_id == user.id, Document.status == "ready")
            .count()
        )
        total_queries = db.query(QueryLog).filter(QueryLog.user_id == user.id).count()
        weekly_queries = (
            db.query(QueryLog)
            .filter(QueryLog.user_id == user.id, QueryLog.created_at >= week_ago)
            .count()
        )
        total_conversations = (
            db.query(Conversation).filter(Conversation.user_id == user.id).count()
        )
        avg_response = (
            db.query(func.avg(QueryLog.response_time_ms))
            .filter(QueryLog.user_id == user.id)
            .scalar()
        ) or 0
        total_tokens = (
            db.query(func.sum(QueryLog.tokens_used))
            .filter(QueryLog.user_id == user.id)
            .scalar()
        ) or 0
        cache_hits = (
            db.query(QueryLog)
            .filter(QueryLog.user_id == user.id, QueryLog.cached.is_(True))
            .count()
        )

        return {
            "documents_total": total_docs,
            "documents_ready": ready_docs,
            "queries_total": total_queries,
            "queries_this_week": weekly_queries,
            "conversations_total": total_conversations,
            "avg_response_time_ms": round(float(avg_response), 2),
            "tokens_used_total": int(total_tokens),
            "cache_hit_count": cache_hits,
        }

    @staticmethod
    def get_query_trends(db: Session, user: User, days: int = 7) -> list[dict]:
        since = datetime.utcnow() - timedelta(days=days - 1)
        rows = (
            db.query(
                func.date(QueryLog.created_at).label("day"),
                func.count(QueryLog.id).label("count"),
            )
            .filter(QueryLog.user_id == user.id, QueryLog.created_at >= since)
            .group_by(func.date(QueryLog.created_at))
            .order_by(func.date(QueryLog.created_at))
            .all()
        )
        counts_by_day = {str(row.day): row.count for row in rows}
        result = []
        for i in range(days):
            day = (since + timedelta(days=i)).date()
            key = str(day)
            result.append({"date": key, "queries": counts_by_day.get(key, 0)})
        return result

    @staticmethod
    def get_popular_topics(db: Session, user: User, limit: int = 5) -> list[dict]:
        rows = (
            db.query(QueryLog.question, func.count(QueryLog.id).label("count"))
            .filter(QueryLog.user_id == user.id)
            .group_by(QueryLog.question)
            .order_by(func.count(QueryLog.id).desc())
            .limit(limit)
            .all()
        )
        return [{"question": row.question, "count": row.count} for row in rows]

    @staticmethod
    def get_platform_overview(db: Session) -> dict:
        from app.core.database import User

        total_users = db.query(User).count()
        total_docs = db.query(Document).count()
        total_queries = db.query(QueryLog).count()
        total_conversations = db.query(Conversation).count()
        active_users = (
            db.query(QueryLog.user_id)
            .filter(QueryLog.created_at >= datetime.utcnow() - timedelta(days=7))
            .distinct()
            .count()
        )
        return {
            "users_total": total_users,
            "documents_total": total_docs,
            "queries_total": total_queries,
            "conversations_total": total_conversations,
            "active_users_week": active_users,
        }
