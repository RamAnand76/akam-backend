from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from app.dependencies import CurrentUserDep, DbDep
from app.models.db.graph import Node
from app.models.db.message import Message
from app.models.schemas.common import ApiResponse, Meta

router = APIRouter(prefix="/digest", tags=["digest"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


class RelationshipChange(BaseModel):
    node_id: str
    name: str
    score: float
    delta: str
    delta_direction: str


class WeeklyDigestData(BaseModel):
    week_label: str
    week: str
    stats: dict
    relationships: dict
    top_pattern: dict | None = None
    memory_unlock: dict | None = None
    generated_at: datetime


@router.get("/weekly", response_model=ApiResponse[WeeklyDigestData])
async def get_weekly_digest(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    week: Annotated[str | None, Query()] = None,
) -> ApiResponse[WeeklyDigestData]:
    # Count user messages
    m_count = await db.execute(
        select(func.count()).select_from(Message).where(Message.user_id == current_user.id)
    )
    total_msgs = m_count.scalar_one()

    # Count nodes
    n_count = await db.execute(
        select(func.count()).select_from(Node).where(Node.user_id == current_user.id)
    )
    total_nodes = n_count.scalar_one()

    data = WeeklyDigestData(
        week_label="Current Week",
        week=week or "2026-W36",
        stats={
            "memories_added": total_msgs,
            "people_mentioned": total_nodes,
            "conversations": max(1, total_msgs // 2),
        },
        relationships={
            "strengthening": [
                RelationshipChange(
                    node_id="n1",
                    name="Key Contacts",
                    score=0.92,
                    delta="+0.05",
                    delta_direction="up",
                )
            ],
            "needs_attention": [],
        },
        top_pattern={
            "pattern_id": "p1",
            "text": "Your journaling this week showed focus on productivity and deep connections.",
        },
        memory_unlock={
            "message_id": "m1",
            "text": "You set goals earlier this month that you might want to revisit.",
            "cta_label": "Review goals now",
        },
        generated_at=datetime.utcnow(),
    )

    return ApiResponse(status="success", data=data, meta=_make_meta(request))
