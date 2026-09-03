from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Query, Request, status
from sqlalchemy import func, select
from app.dependencies import CurrentUserDep, DbDep
from app.models.db.cluster import Cluster, ClusterEdge, MessageClusterMembership
from app.models.db.message import Message
from app.models.schemas.clusters import (
    ClusterDetailData,
    ClusterItem,
    ClusterMemberMessage,
    ClusterPreview,
    CreateClusterRequest,
    CrossClusterLink,
    DeleteClusterData,
    PatchClusterRequest,
)
from app.models.schemas.common import ApiResponse, Meta, PaginatedData, Pagination
from app.security.permissions import ensure_ownership
from app.security.sanitiser import sanitise_text

router = APIRouter(prefix="/clusters", tags=["clusters"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


@router.get("", response_model=ApiResponse[PaginatedData[ClusterItem]])
async def get_clusters(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ApiResponse[PaginatedData[ClusterItem]]:
    query = (
        select(Cluster)
        .where(Cluster.user_id == current_user.id)
        .order_by(Cluster.last_active.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    clusters = result.scalars().all()

    items: list[ClusterItem] = []
    for c in clusters:
        items.append(
            ClusterItem(
                cluster_id=c.id,
                label=c.label,
                card_style=c.card_style,
                color_accent=c.color_accent,
                preview=ClusterPreview(type="text_cards", snippets=["Recent thoughts in this cluster..."]),
                message_count=c.member_count,
                last_active=c.last_active,
                tags=[],
                cross_cluster_links=[],
            )
        )

    return ApiResponse(
        status="success",
        data=PaginatedData[ClusterItem](
            items=items,
            pagination=Pagination(
                cursor=items[-1].cluster_id if items else None,
                has_more=len(items) == limit,
                total_count=len(items),
                limit=limit,
            ),
        ),
        meta=_make_meta(request),
    )


@router.get("/{cluster_id}", response_model=ApiResponse[PaginatedData[ClusterMemberMessage]])
async def get_cluster_detail(
    cluster_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> ApiResponse[PaginatedData[ClusterMemberMessage]]:
    result = await db.execute(
        select(Cluster).where(Cluster.id == cluster_id, Cluster.user_id == current_user.id)
    )
    cluster = result.scalar_one_or_none()
    await ensure_ownership(cluster, current_user.id)

    # Fetch member messages
    mem_res = await db.execute(
        select(MessageClusterMembership).where(MessageClusterMembership.cluster_id == cluster_id)
    )
    mems = mem_res.scalars().all()
    msg_ids = [m.message_id for m in mems]

    items: list[ClusterMemberMessage] = []
    if msg_ids:
        msg_res = await db.execute(
            select(Message).where(Message.id.in_(msg_ids), Message.user_id == current_user.id).limit(limit)
        )
        msgs = msg_res.scalars().all()
        for m in msgs:
            items.append(
                ClusterMemberMessage(
                    message_id=m.id,
                    content=m.content,
                    role=m.role,
                    created_at=m.created_at,
                    membership_weight=0.92,
                    is_partial_member=False,
                    also_in_clusters=[],
                )
            )

    return ApiResponse(
        status="success",
        data=PaginatedData[ClusterMemberMessage](
            items=items,
            pagination=Pagination(
                cursor=items[-1].message_id if items else None,
                has_more=len(items) == limit,
                total_count=len(items),
                limit=limit,
            ),
        ),
        meta=_make_meta(request),
    )


@router.post("", response_model=ApiResponse[ClusterItem], status_code=status.HTTP_201_CREATED)
async def create_cluster(
    body: CreateClusterRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[ClusterItem]:
    clean_label = sanitise_text(body.label, max_length=200)

    cluster = Cluster(
        user_id=current_user.id,
        label=clean_label,
        color_accent=body.color_accent,
        is_manual=True,
    )
    db.add(cluster)
    await db.commit()
    await db.refresh(cluster)

    return ApiResponse(
        status="success",
        data=ClusterItem(
            cluster_id=cluster.id,
            label=cluster.label,
            card_style=cluster.card_style,
            color_accent=cluster.color_accent,
            preview=ClusterPreview(),
            message_count=0,
            last_active=cluster.last_active,
        ),
        meta=_make_meta(request),
    )


@router.patch("/{cluster_id}", response_model=ApiResponse[ClusterItem])
async def patch_cluster(
    cluster_id: str,
    body: PatchClusterRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[ClusterItem]:
    result = await db.execute(
        select(Cluster).where(Cluster.id == cluster_id, Cluster.user_id == current_user.id)
    )
    cluster = result.scalar_one_or_none()
    await ensure_ownership(cluster, current_user.id)

    if body.label is not None:
        cluster.label = sanitise_text(body.label, max_length=200)
    if body.color_accent is not None:
        cluster.color_accent = body.color_accent

    await db.commit()

    return ApiResponse(
        status="success",
        data=ClusterItem(
            cluster_id=cluster.id,
            label=cluster.label,
            card_style=cluster.card_style,
            color_accent=cluster.color_accent,
            preview=ClusterPreview(),
            message_count=cluster.member_count,
            last_active=cluster.last_active,
        ),
        meta=_make_meta(request),
    )


@router.delete("/{cluster_id}", response_model=ApiResponse[DeleteClusterData])
async def delete_cluster(
    cluster_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[DeleteClusterData]:
    result = await db.execute(
        select(Cluster).where(Cluster.id == cluster_id, Cluster.user_id == current_user.id)
    )
    cluster = result.scalar_one_or_none()
    await ensure_ownership(cluster, current_user.id)

    count_mem = cluster.member_count
    await db.delete(cluster)
    await db.commit()

    return ApiResponse(
        status="success",
        data=DeleteClusterData(
            deleted=True,
            messages_queued_for_reassignment=count_mem,
            reassignment_job_id="local-reassignment-completed",
        ),
        meta=_make_meta(request),
    )
