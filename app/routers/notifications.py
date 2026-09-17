from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from app.dependencies import CurrentUserDep, DbDep
from app.models.db.notification import Notification
from app.models.schemas.notifications import NotificationListResponse, NotificationResponse
from app.models.schemas.common import ApiResponse, Meta

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


@router.get("", response_model=ApiResponse[NotificationListResponse])
async def get_notifications(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiResponse[NotificationListResponse]:
    # Mocking implementation for frontend integration
    return ApiResponse(
        status="success",
        data=NotificationListResponse(
            data=[],
            unread_count=0,
            total_count=0
        ),
        meta=_make_meta(request),
    )


@router.patch("/mark-read", response_model=ApiResponse[dict])
async def mark_notifications_read(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[dict]:
    # Mocking implementation for frontend integration
    return ApiResponse(
        status="success",
        data={"updated": True},
        meta=_make_meta(request),
    )
