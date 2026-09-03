from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.dependencies import CurrentUserDep, DbDep
from app.exceptions import NotFoundException
from app.models.db.event import Event, EventPanel, EventPanelItem
from app.models.schemas.common import ApiResponse, Meta, PaginatedData, Pagination
from app.models.schemas.events import (
    CreateEventRequest,
    CreatePanelRequest,
    DeleteEventData,
    EventItem,
    EventPanelSchema,
    LinkEventRequest,
    PanelCreateItemSchema,
    PanelItemSchema,
    PatchEventRequest,
    PatchPanelItemRequest,
)
from app.security.permissions import ensure_ownership
from app.security.sanitiser import sanitise_text

router = APIRouter(prefix="/events", tags=["events"])


def _make_meta(request: Request) -> Meta:
    request_id = getattr(request.state, "request_id", "01J4MXYZ")
    return Meta(request_id=request_id, timestamp=datetime.utcnow(), version="2.0.0")


def _event_to_schema(e: Event) -> EventItem:
    panels_schema = []
    for p in e.panels:
        items_schema = [
            PanelItemSchema(
                item_id=i.id,
                text=i.text,
                done=i.done,
                image_url=i.image_url,
                location=i.location,
                person_name=i.person_name,
                person_node_id=i.person_node_id,
                sort_order=i.sort_order,
            )
            for i in p.items
        ]
        panels_schema.append(
            EventPanelSchema(
                panel_id=p.id,
                type=p.type,
                label=p.label,
                color=p.color,
                sort_order=p.sort_order,
                items=items_schema,
            )
        )

    date_lbl = f"{e.date_start.strftime('%d %b')}"
    if e.date_end:
        date_lbl += f" - {e.date_end.strftime('%d %b')}"

    return EventItem(
        event_id=e.id,
        title=e.title,
        emoji=e.emoji,
        date_start=e.date_start,
        date_end=e.date_end,
        date_label=date_lbl,
        status=e.status,
        panels=panels_schema,
        linked_cluster_id=e.linked_cluster_id,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


@router.get("", response_model=ApiResponse[PaginatedData[EventItem]])
async def get_events(
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
    status_filter: Annotated[str | None, Query(alias="status")] = "upcoming",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ApiResponse[PaginatedData[EventItem]]:
    query = (
        select(Event)
        .options(selectinload(Event.panels).selectinload(EventPanel.items))
        .where(Event.user_id == current_user.id)
    )
    if status_filter:
        query = query.where(Event.status == status_filter)

    query = query.order_by(Event.date_start.asc()).limit(limit)
    res = await db.execute(query)
    events = res.scalars().all()

    items = [_event_to_schema(e) for e in events]
    return ApiResponse(
        status="success",
        data=PaginatedData[EventItem](
            items=items,
            pagination=Pagination(
                cursor=items[-1].event_id if items else None,
                has_more=len(items) == limit,
                total_count=len(items),
                limit=limit,
            ),
        ),
        meta=_make_meta(request),
    )


@router.post("", response_model=ApiResponse[EventItem], status_code=status.HTTP_201_CREATED)
async def create_event(
    body: CreateEventRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[EventItem]:
    clean_title = sanitise_text(body.title, max_length=200)

    event = Event(
        user_id=current_user.id,
        title=clean_title,
        emoji=body.emoji,
        date_start=body.date_start,
        date_end=body.date_end,
        status="upcoming",
    )
    db.add(event)
    await db.flush()

    for p_idx, p in enumerate(body.panels):
        panel = EventPanel(
            event_id=event.id,
            user_id=current_user.id,
            type=p.type,
            label=sanitise_text(p.label, max_length=100),
            color=p.color,
            sort_order=p_idx,
        )
        db.add(panel)
        await db.flush()

        for i_idx, item in enumerate(p.items):
            panel_item = EventPanelItem(
                panel_id=panel.id,
                user_id=current_user.id,
                text=sanitise_text(item.text, max_length=500) if item.text else None,
                done=item.done,
                image_url=item.image_url,
                location=item.location,
                person_name=item.person_name,
                person_node_id=item.person_node_id,
                sort_order=i_idx,
            )
            db.add(panel_item)

    await db.commit()
    # Re-fetch with relations
    res = await db.execute(
        select(Event)
        .options(selectinload(Event.panels).selectinload(EventPanel.items))
        .where(Event.id == event.id)
    )
    loaded_event = res.scalar_one()

    return ApiResponse(status="success", data=_event_to_schema(loaded_event), meta=_make_meta(request))


@router.patch("/{event_id}", response_model=ApiResponse[EventItem])
async def patch_event(
    event_id: str,
    body: PatchEventRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[EventItem]:
    res = await db.execute(
        select(Event)
        .options(selectinload(Event.panels).selectinload(EventPanel.items))
        .where(Event.id == event_id, Event.user_id == current_user.id)
    )
    event = res.scalar_one_or_none()
    await ensure_ownership(event, current_user.id)

    if body.title is not None:
        event.title = sanitise_text(body.title, max_length=200)
    if body.emoji is not None:
        event.emoji = body.emoji
    if body.date_start is not None:
        event.date_start = body.date_start
    if body.date_end is not None:
        event.date_end = body.date_end
    if body.status is not None:
        event.status = body.status

    await db.commit()
    return ApiResponse(status="success", data=_event_to_schema(event), meta=_make_meta(request))


@router.delete("/{event_id}", response_model=ApiResponse[DeleteEventData])
async def delete_event(
    event_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[DeleteEventData]:
    res = await db.execute(select(Event).where(Event.id == event_id, Event.user_id == current_user.id))
    event = res.scalar_one_or_none()
    await ensure_ownership(event, current_user.id)

    await db.delete(event)
    await db.commit()

    return ApiResponse(
        status="success",
        data=DeleteEventData(deleted=True, event_id=event_id),
        meta=_make_meta(request),
    )


@router.post("/{event_id}/panels", response_model=ApiResponse[EventPanelSchema], status_code=status.HTTP_201_CREATED)
async def add_panel(
    event_id: str,
    body: CreatePanelRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[EventPanelSchema]:
    res = await db.execute(select(Event).where(Event.id == event_id, Event.user_id == current_user.id))
    event = res.scalar_one_or_none()
    await ensure_ownership(event, current_user.id)

    panel = EventPanel(
        event_id=event_id,
        user_id=current_user.id,
        type=body.type,
        label=sanitise_text(body.label, max_length=100),
        color=body.color,
    )
    db.add(panel)
    await db.commit()
    await db.refresh(panel)

    return ApiResponse(
        status="success",
        data=EventPanelSchema(
            panel_id=panel.id,
            type=panel.type,
            label=panel.label,
            color=panel.color,
            items=[],
        ),
        meta=_make_meta(request),
    )


@router.post(
    "/{event_id}/panels/{panel_id}/items",
    response_model=ApiResponse[PanelItemSchema],
    status_code=status.HTTP_201_CREATED,
)
async def add_panel_item(
    event_id: str,
    panel_id: str,
    body: PanelCreateItemSchema,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[PanelItemSchema]:
    res = await db.execute(
        select(EventPanel).where(
            EventPanel.id == panel_id,
            EventPanel.event_id == event_id,
            EventPanel.user_id == current_user.id,
        )
    )
    panel = res.scalar_one_or_none()
    await ensure_ownership(panel, current_user.id)

    item = EventPanelItem(
        panel_id=panel_id,
        user_id=current_user.id,
        text=sanitise_text(body.text, max_length=500) if body.text else None,
        done=body.done,
        image_url=body.image_url,
        location=body.location,
        person_name=body.person_name,
        person_node_id=body.person_node_id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return ApiResponse(
        status="success",
        data=PanelItemSchema(
            item_id=item.id,
            text=item.text,
            done=item.done,
            image_url=item.image_url,
            location=item.location,
            person_name=item.person_name,
            person_node_id=item.person_node_id,
        ),
        meta=_make_meta(request),
    )


@router.patch("/{event_id}/panels/{panel_id}/items/{item_id}", response_model=ApiResponse[PanelItemSchema])
async def patch_panel_item(
    event_id: str,
    panel_id: str,
    item_id: str,
    body: PatchPanelItemRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[PanelItemSchema]:
    res = await db.execute(
        select(EventPanelItem).where(
            EventPanelItem.id == item_id,
            EventPanelItem.panel_id == panel_id,
            EventPanelItem.user_id == current_user.id,
        )
    )
    item = res.scalar_one_or_none()
    await ensure_ownership(item, current_user.id)

    if body.text is not None:
        item.text = sanitise_text(body.text, max_length=500)
    if body.done is not None:
        item.done = body.done

    await db.commit()

    return ApiResponse(
        status="success",
        data=PanelItemSchema(
            item_id=item.id,
            text=item.text,
            done=item.done,
            image_url=item.image_url,
            location=item.location,
            person_name=item.person_name,
            person_node_id=item.person_node_id,
        ),
        meta=_make_meta(request),
    )


@router.delete("/{event_id}/panels/{panel_id}/items/{item_id}", response_model=ApiResponse[dict])
async def delete_panel_item(
    event_id: str,
    panel_id: str,
    item_id: str,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[dict]:
    res = await db.execute(
        select(EventPanelItem).where(
            EventPanelItem.id == item_id,
            EventPanelItem.panel_id == panel_id,
            EventPanelItem.user_id == current_user.id,
        )
    )
    item = res.scalar_one_or_none()
    await ensure_ownership(item, current_user.id)

    await db.delete(item)
    await db.commit()

    return ApiResponse(status="success", data={"deleted": True}, meta=_make_meta(request))


@router.post("/{event_id}/link", response_model=ApiResponse[dict])
async def link_event_cluster(
    event_id: str,
    body: LinkEventRequest,
    current_user: CurrentUserDep,
    db: DbDep,
    request: Request,
) -> ApiResponse[dict]:
    res = await db.execute(select(Event).where(Event.id == event_id, Event.user_id == current_user.id))
    event = res.scalar_one_or_none()
    await ensure_ownership(event, current_user.id)

    event.linked_cluster_id = body.cluster_id
    await db.commit()

    return ApiResponse(status="success", data={"linked": True}, meta=_make_meta(request))
