from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.dependencies import get_db, get_current_user, get_current_admin
from app.core.database import User
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class OverviewResponse(BaseModel):
    documents_total: int
    documents_ready: int
    queries_total: int
    queries_this_week: int
    conversations_total: int
    avg_response_time_ms: float
    tokens_used_total: int
    cache_hit_count: int


@router.get("/overview", response_model=OverviewResponse)
async def analytics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AnalyticsService.get_overview(db, current_user)


@router.get("/trends")
async def query_trends(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AnalyticsService.get_query_trends(db, current_user, days)


@router.get("/topics")
async def popular_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AnalyticsService.get_popular_topics(db, current_user)


@router.get("/platform")
async def platform_overview(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return AnalyticsService.get_platform_overview(db)
