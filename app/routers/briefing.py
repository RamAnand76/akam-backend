from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from app.dependencies import CurrentUserDep, DbDep
from app.exceptions import NotFoundException, ValidationException
from app.models.db.graph import Node
from app.models.schemas.briefing import (
    BriefingData,
    OpenPromiseItem,
    PersonBriefingHeader,
    RecentPersonChip,
)
from app.models.schemas.common import ApiResponse, Meta, PaginatedData, Pagination
from app.security.permissions import ensure_ownership

router = APIRouter(prefix="/briefing", tags=["briefing"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


@router.get("", response_model=ApiResponse[BriefingData])
async def get_briefing(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    query: Annotated[str | None, Query()] = None,
    node_id: Annotated[str | None, Query()] = None,
    force_refresh: Annotated[bool, Query()] = False,
) -> ApiResponse[BriefingData]:
    if not query and not node_id:
        raise ValidationException("One of 'query' or 'node_id' is required.")

    # Find person node
    if node_id:
        res = await db.execute(select(Node).where(Node.id == node_id, Node.user_id == current_user.id))
        node = res.scalar_one_or_none()
    else:
        res = await db.execute(
            select(Node).where(
                Node.user_id == current_user.id,
                Node.type == "person",
                Node.label.ilike(f"%{query}%"),
            )
        )
        node = res.scalars().first()

    await ensure_ownership(node, current_user.id)

    name = node.label
    data = BriefingData(
        person=PersonBriefingHeader(
            node_id=node.id,
            name=name,
            relationship_score=0.82,
            score_label="Strong",
            score_delta="+0.06",
            last_mentioned_days_ago=1,
        ),
        summary=f"{name} was recently mentioned. Discussions focused on milestones, decisions, and updates.",
        last_discussed=[
            f"Recent life update with {name}",
            "Weighing key decisions",
            "Follow-up thoughts",
        ],
        open_promises=[
            OpenPromiseItem(
                promise_id="promise-1",
                text=f"Check in with {name} regarding updates",
                mentioned_days_ago=3,
            )
        ],
        patterns=[f"You feel motivated after discussing ideas with {name}"],
        watch_for=f"Take time to listen and celebrate recent accomplishments.",
        conversation_starters=[
            f"How have things been progressing since we last spoke?",
            f"Any updates on what you've been working on?",
        ],
        cached=False,
        generated_at=datetime.utcnow(),
    )

    return ApiResponse(status="success", data=data, meta=_make_meta(request))


@router.get("/people", response_model=ApiResponse[PaginatedData[RecentPersonChip]])
async def get_recent_people(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[PaginatedData[RecentPersonChip]]:
    res = await db.execute(
        select(Node)
        .where(Node.user_id == current_user.id, Node.type == "person")
        .order_by(Node.last_active.desc())
        .limit(6)
    )
    people = res.scalars().all()

    items = [
        RecentPersonChip(
            node_id=p.id,
            name=p.label,
            relationship_score=0.82,
            last_mentioned_days_ago=1,
        )
        for p in people
    ]

    return ApiResponse(
        status="success",
        data=PaginatedData[RecentPersonChip](
            items=items,
            pagination=Pagination(
                cursor=None,
                has_more=False,
                total_count=len(items),
                limit=6,
            ),
        ),
        meta=_make_meta(request),
    )
