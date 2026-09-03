from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from app.dependencies import CurrentUserDep, DbDep
from app.models.db.nudge import Nudge
from app.models.db.user import UserPreferences
from app.models.schemas.common import ApiResponse, Meta, PaginatedData, Pagination
from app.models.schemas.nudges import (
    NudgeActionData,
    NudgeActionRequest,
    NudgeItem,
    NudgePreferencesData,
    PatchNudgePreferencesRequest,
    ScreenTimeReportRequest,
    ScreenTimeResponseData,
)
from app.security.permissions import ensure_ownership

router = APIRouter(prefix="/nudges", tags=["nudges"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


@router.get("", response_model=ApiResponse[PaginatedData[NudgeItem]])
async def get_nudges(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[PaginatedData[NudgeItem]]:
    query = (
        select(Nudge)
        .where(Nudge.user_id == current_user.id, Nudge.shown == False)
        .order_by(Nudge.created_at.desc())
        .limit(10)
    )
    res = await db.execute(query)
    nudges = res.scalars().all()

    items = [
        NudgeItem(
            nudge_id=n.id,
            type=n.type,
            priority=n.priority,
            title=n.title,
            body=n.body,
            person_node_id=n.person_node_id,
            cluster_id=n.cluster_id,
            pattern_id=n.pattern_id,
            cta_primary=n.cta_primary_json or {"label": "View", "action": "open"},
            cta_secondary=n.cta_secondary_json or {"label": "Dismiss", "action": "dismiss"},
            deep_link=n.deep_link,
            created_at=n.created_at,
            expires_at=n.expires_at,
        )
        for n in nudges
    ]

    return ApiResponse(
        status="success",
        data=PaginatedData[NudgeItem](
            items=items,
            pagination=Pagination(
                cursor=None,
                has_more=False,
                total_count=len(items),
                limit=10,
            ),
        ),
        meta=_make_meta(request),
    )


@router.post("/{nudge_id}/action", response_model=ApiResponse[NudgeActionData])
async def record_nudge_action(
    nudge_id: str,
    body: NudgeActionRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[NudgeActionData]:
    res = await db.execute(select(Nudge).where(Nudge.id == nudge_id, Nudge.user_id == current_user.id))
    nudge = res.scalar_one_or_none()
    await ensure_ownership(nudge, current_user.id)

    nudge.action_taken = body.action
    nudge.shown = True
    nudge.shown_at = datetime.utcnow()
    await db.commit()

    return ApiResponse(
        status="success",
        data=NudgeActionData(recorded=True, nudge_id=nudge_id),
        meta=_make_meta(request),
    )


@router.get("/preferences", response_model=ApiResponse[NudgePreferencesData])
async def get_nudge_preferences(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[NudgePreferencesData]:
    res = await db.execute(select(UserPreferences).where(UserPreferences.user_id == current_user.id))
    prefs = res.scalar_one_or_none()
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)

    return ApiResponse(
        status="success",
        data=NudgePreferencesData(
            enabled=True,
            max_per_day=prefs.nudges_per_day,
            quiet_hours_start=prefs.quiet_hours_start,
            quiet_hours_end=prefs.quiet_hours_end,
            timezone=prefs.timezone,
            types_enabled=prefs.types_enabled,
        ),
        meta=_make_meta(request),
    )


@router.patch("/preferences", response_model=ApiResponse[NudgePreferencesData])
async def patch_nudge_preferences(
    body: PatchNudgePreferencesRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[NudgePreferencesData]:
    res = await db.execute(select(UserPreferences).where(UserPreferences.user_id == current_user.id))
    prefs = res.scalar_one_or_none()
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)

    if body.max_per_day is not None:
        prefs.nudges_per_day = body.max_per_day
    if body.quiet_hours_start is not None:
        prefs.quiet_hours_start = body.quiet_hours_start
    if body.quiet_hours_end is not None:
        prefs.quiet_hours_end = body.quiet_hours_end
    if body.timezone is not None:
        prefs.timezone = body.timezone
    if body.types_enabled is not None:
        merged = dict(prefs.types_enabled)
        merged.update(body.types_enabled)
        prefs.types_enabled = merged

    await db.commit()

    return ApiResponse(
        status="success",
        data=NudgePreferencesData(
            enabled=True,
            max_per_day=prefs.nudges_per_day,
            quiet_hours_start=prefs.quiet_hours_start,
            quiet_hours_end=prefs.quiet_hours_end,
            timezone=prefs.timezone,
            types_enabled=prefs.types_enabled,
        ),
        meta=_make_meta(request),
    )


@router.post("/screentime", response_model=ApiResponse[ScreenTimeResponseData])
async def report_screentime(
    body: ScreenTimeReportRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[ScreenTimeResponseData]:
    # Brainrot threshold check (>120 minutes of social media)
    triggered = body.social_media_minutes >= 120
    nudge_id = None
    nudge_body = None

    if triggered:
        nudge_body = (
            f"You've spent {body.social_media_minutes} minutes on social media today. "
            f"Your real relationships are waiting."
        )
        n = Nudge(
            user_id=current_user.id,
            type="brainrot_warning",
            priority="high",
            title="Digital Well-being Insight",
            body=nudge_body,
            cta_primary_json={"label": "Put down phone", "action": "dismiss"},
            expires_at=datetime.utcnow() + timedelta(hours=12),
        )
        db.add(n)
        await db.commit()
        await db.refresh(n)
        nudge_id = n.id

    return ApiResponse(
        status="success",
        data=ScreenTimeResponseData(
            nudge_triggered=triggered,
            nudge_id=nudge_id,
            nudge_body=nudge_body,
        ),
        meta=_make_meta(request),
    )
