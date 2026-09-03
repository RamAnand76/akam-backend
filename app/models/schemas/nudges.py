from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class NudgeActionRequest(BaseModel):
    action: Literal["cta_primary", "cta_secondary", "dismiss"]


class NudgeItem(BaseModel):
    nudge_id: str
    type: str
    priority: str = "medium"
    title: str
    body: str
    person_node_id: str | None = None
    cluster_id: str | None = None
    pattern_id: str | None = None
    cta_primary: dict | None = None
    cta_secondary: dict | None = None
    deep_link: str | None = None
    created_at: datetime
    expires_at: datetime | None = None


class NudgeActionData(BaseModel):
    recorded: bool = True
    nudge_id: str


class NudgePreferencesData(BaseModel):
    enabled: bool = True
    max_per_day: int = 2
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    timezone: str = "Asia/Kolkata"
    types_enabled: dict = {}


class PatchNudgePreferencesRequest(BaseModel):
    max_per_day: int | None = Field(default=None, ge=0, le=5)
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str | None = None
    types_enabled: dict | None = None


class ScreenTimeAppBreakdown(BaseModel):
    app_name: str
    minutes: int


class ScreenTimeReportRequest(BaseModel):
    date: str
    total_minutes: int
    social_media_minutes: int
    akam_minutes: int
    app_breakdown: list[ScreenTimeAppBreakdown] = []


class ScreenTimeResponseData(BaseModel):
    nudge_triggered: bool = False
    nudge_id: str | None = None
    nudge_body: str | None = None
