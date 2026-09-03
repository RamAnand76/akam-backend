from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.dependencies import CurrentUserDep, DbDep
from app.models.db.message import Message
from app.models.schemas.common import ApiResponse, Meta, PaginatedData, Pagination
from app.security.sanitiser import sanitise_text
from app.services.embedding_service import embedding_service

router = APIRouter(prefix="/search", tags=["search"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    scope: Literal["all", "messages", "clusters", "events"] = "all"
    cluster_id: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class SearchResultItem(BaseModel):
    result_id: str
    type: str = "message"
    content_preview: str
    relevance_score: float
    created_at: datetime
    cluster_badges: list[dict] = []
    message_id: str | None = None


@router.post("", response_model=ApiResponse[PaginatedData[SearchResultItem]])
async def semantic_search(
    body: SearchRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[PaginatedData[SearchResultItem]]:
    clean_q = sanitise_text(body.query, check_prompt_injection=True)
    query_vec = embedding_service.generate_embedding(clean_q)

    # Query recent messages for user
    res = await db.execute(
        select(Message)
        .where(Message.user_id == current_user.id, Message.is_deleted == False)
        .order_by(Message.created_at.desc())
        .limit(100)
    )
    messages = res.scalars().all()

    # Compute vector similarity + keyword bonus
    scored: list[tuple[float, Message]] = []
    q_lower = clean_q.lower()
    for m in messages:
        base_sim = (
            embedding_service.cosine_similarity(query_vec, m.embedding)
            if m.embedding
            else 0.5
        )
        if q_lower in m.content.lower():
            base_sim = min(1.0, base_sim + 0.3)
        scored.append((base_sim, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_results = scored[: body.limit]

    items = [
        SearchResultItem(
            result_id=m.id,
            type="message",
            content_preview=m.content[:150],
            relevance_score=round(score, 2),
            created_at=m.created_at,
            cluster_badges=[{"cluster_id": "c1", "label": "Memories"}],
            message_id=m.id,
        )
        for score, m in top_results
    ]

    return ApiResponse(
        status="success",
        data=PaginatedData[SearchResultItem](
            items=items,
            pagination=Pagination(
                cursor=None,
                has_more=False,
                total_count=len(items),
                limit=body.limit,
            ),
        ),
        meta=_make_meta(request),
    )
