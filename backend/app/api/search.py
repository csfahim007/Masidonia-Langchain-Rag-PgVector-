from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.models.dependencies import get_db, get_current_user, get_write_user
from app.core.database import User
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    snippet: str
    score: float
    chunk_index: int


class SearchHistoryItem(BaseModel):
    id: str
    query: str
    mode: str
    results_count: int
    created_at: str


@router.get("", response_model=list[SearchResult])
async def search(
    q: str = Query(..., min_length=1),
    document_id: Optional[str] = None,
    mode: str = Query("hybrid", pattern="^(hybrid|vector|keyword)$"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SearchService.search(db, current_user, q, document_id, mode, limit)


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"suggestions": SearchService.autocomplete(db, current_user, q)}


@router.get("/history", response_model=list[SearchHistoryItem])
async def search_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SearchService.get_history(db, current_user, limit)


@router.delete("/history")
async def clear_search_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    deleted = SearchService.clear_history(db, current_user)
    return {"message": "Search history cleared", "deleted": deleted}
