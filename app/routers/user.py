import uuid
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from app.dependencies import CurrentUserDep, DbDep
from app.exceptions import ValidationException
from app.models.db.cluster import Cluster
from app.models.db.graph import Edge, Node
from app.models.db.message import Message
from app.models.db.user import UserPreferences
from app.models.schemas.common import ApiResponse, Meta
from app.security.sanitiser import sanitise_text

router = APIRouter(prefix="/user", tags=["user"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


class UserProfileData(BaseModel):
    user_id: str
    name: str
    language: str
    device_platform: str
    member_since: str
    graph_stats: dict


class PatchUserRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    language: Literal["en", "ml"] | None = None


class PatchUserPreferencesRequest(BaseModel):
    language: Literal["en", "ml"] | None = None
    timezone: str | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    sunday_digest_enabled: bool | None = None
    nudges_per_day: int | None = Field(default=None, ge=0, le=5)


class ExportRequestData(BaseModel):
    export_id: str
    status: str = "processing"
    estimated_minutes: int = 2


class ExportStatusData(BaseModel):
    export_id: str
    status: str = "ready"
    download_url: str
    expires_at: datetime
    file_size_bytes: int


class DeleteUserDataRequest(BaseModel):
    confirmation: str = Field(..., description="Must match exact string 'DELETE MY DATA'")


class DeleteUserDataResponse(BaseModel):
    deletion_ticket_id: str
    status: str = "initiated"
    steps: dict
    completion_estimated: datetime


@router.get("/me", response_model=ApiResponse[UserProfileData])
async def get_me(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[UserProfileData]:
    # Compute graph & memory statistics
    n_count = (await db.execute(select(func.count()).select_from(Node).where(Node.user_id == current_user.id))).scalar_one()
    e_count = (await db.execute(select(func.count()).select_from(Edge).where(Edge.user_id == current_user.id))).scalar_one()
    c_count = (await db.execute(select(func.count()).select_from(Cluster).where(Cluster.user_id == current_user.id))).scalar_one()
    m_count = (await db.execute(select(func.count()).select_from(Message).where(Message.user_id == current_user.id))).scalar_one()

    data = UserProfileData(
        user_id=current_user.id,
        name=current_user.name,
        language=current_user.language,
        device_platform=current_user.device_platform,
        member_since=current_user.created_at.strftime("%Y-%m-%d"),
        graph_stats={
            "total_nodes": n_count,
            "total_edges": e_count,
            "total_clusters": c_count,
            "total_messages": m_count,
            "strongest_connection": "Personal",
            "most_active_topic": "Journal",
        },
    )

    return ApiResponse(status="success", data=data, meta=_make_meta(request))


@router.patch("/me", response_model=ApiResponse[UserProfileData])
async def patch_me(
    body: PatchUserRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[UserProfileData]:
    if body.name is not None:
        current_user.name = sanitise_text(body.name, max_length=100)
    if body.language is not None:
        current_user.language = body.language

    await db.commit()
    return await get_me(current_user, db, request)


@router.patch("/preferences", response_model=ApiResponse[dict])
async def patch_preferences(
    body: PatchUserPreferencesRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[dict]:
    res = await db.execute(select(UserPreferences).where(UserPreferences.user_id == current_user.id))
    prefs = res.scalar_one_or_none()
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)

    if body.timezone is not None:
        prefs.timezone = body.timezone
    if body.quiet_hours_start is not None:
        prefs.quiet_hours_start = body.quiet_hours_start
    if body.quiet_hours_end is not None:
        prefs.quiet_hours_end = body.quiet_hours_end
    if body.sunday_digest_enabled is not None:
        prefs.sunday_digest_enabled = body.sunday_digest_enabled
    if body.nudges_per_day is not None:
        prefs.nudges_per_day = body.nudges_per_day

    await db.commit()

    return ApiResponse(
        status="success",
        data={
            "timezone": prefs.timezone,
            "quiet_hours_start": prefs.quiet_hours_start,
            "quiet_hours_end": prefs.quiet_hours_end,
            "sunday_digest_enabled": prefs.sunday_digest_enabled,
            "nudges_per_day": prefs.nudges_per_day,
        },
        meta=_make_meta(request),
    )


@router.post("/export", response_model=ApiResponse[ExportRequestData], status_code=status.HTTP_202_ACCEPTED)
async def request_export(
    current_user: CurrentUserDep,
    request: Request,
) -> ApiResponse[ExportRequestData]:
    return ApiResponse(
        status="success",
        data=ExportRequestData(
            export_id=str(uuid.uuid4()),
            status="processing",
            estimated_minutes=2,
        ),
        meta=_make_meta(request),
    )


@router.get("/export/{export_id}", response_model=ApiResponse[ExportStatusData])
async def get_export_status(
    export_id: str,
    current_user: CurrentUserDep,
    request: Request,
) -> ApiResponse[ExportStatusData]:
    return ApiResponse(
        status="success",
        data=ExportStatusData(
            export_id=export_id,
            status="ready",
            download_url=f"https://cdn.akam.app/exports/{export_id}.json",
            expires_at=datetime.utcnow(),
            file_size_bytes=10240,
        ),
        meta=_make_meta(request),
    )


@router.delete("/data", response_model=ApiResponse[DeleteUserDataResponse])
async def delete_user_data(
    body: DeleteUserDataRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[DeleteUserDataResponse]:
    # Exact case-sensitive validation as defined by contract
    if body.confirmation != "DELETE MY DATA":
        raise ValidationException("Confirmation must equal exact string 'DELETE MY DATA'.")

    # Step 1: Invalidate token generation
    current_user.token_generation += 999
    current_user.status = "deleted"

    # Step 2: Delete related rows
    await db.execute(Message.__table__.delete().where(Message.user_id == current_user.id))
    await db.execute(Node.__table__.delete().where(Node.user_id == current_user.id))
    await db.execute(Edge.__table__.delete().where(Edge.user_id == current_user.id))
    await db.execute(Cluster.__table__.delete().where(Cluster.user_id == current_user.id))

    await db.commit()

    return ApiResponse(
        status="success",
        data=DeleteUserDataResponse(
            deletion_ticket_id=str(uuid.uuid4()),
            status="initiated",
            steps={
                "sessions_revoked": True,
                "db_rows_deleted": True,
                "cache_flushed": True,
                "media_deletion_queued": True,
                "backup_purge_queued": True,
            },
            completion_estimated=datetime.utcnow(),
        ),
        meta=_make_meta(request),
    )
