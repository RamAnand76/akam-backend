from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field


class PanelItemSchema(BaseModel):
    item_id: str | None = None
    text: str | None = None
    done: bool = False
    image_url: str | None = None
    location: str | None = None
    person_name: str | None = None
    person_node_id: str | None = None
    sort_order: int = 0


class PanelCreateItemSchema(BaseModel):
    text: str | None = None
    done: bool = False
    image_url: str | None = None
    location: str | None = None
    person_name: str | None = None
    person_node_id: str | None = None


class EventPanelSchema(BaseModel):
    panel_id: str | None = None
    type: Literal["plans", "trips", "invited", "custom"]
    label: str
    color: str | None = None
    sort_order: int = 0
    items: list[PanelItemSchema] = []


class EventItem(BaseModel):
    event_id: str
    title: str
    emoji: str | None = None
    date_start: date
    date_end: date | None = None
    date_label: str | None = None
    status: str = "upcoming"
    panels: list[EventPanelSchema] = []
    linked_cluster_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateEventRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    emoji: str | None = None
    date_start: date
    date_end: date | None = None
    panels: list[EventPanelSchema] = []


class PatchEventRequest(BaseModel):
    title: str | None = None
    emoji: str | None = None
    date_start: date | None = None
    date_end: date | None = None
    status: Literal["upcoming", "past", "cancelled"] | None = None


class CreatePanelRequest(BaseModel):
    type: Literal["plans", "trips", "invited", "custom"]
    label: str = Field(..., min_length=1, max_length=100)
    color: str | None = None


class PatchPanelItemRequest(BaseModel):
    text: str | None = None
    done: bool | None = None


class LinkEventRequest(BaseModel):
    cluster_id: str
    node_id: str | None = None


class DeleteEventData(BaseModel):
    deleted: bool = True
    event_id: str
