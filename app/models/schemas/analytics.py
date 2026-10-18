from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator


ALLOWED_EVENT_NAMES = {
    "screen_view",
    "app_open",
    "app_background",
    "model_download_started",
    "model_download_progress",
    "model_download_completed",
    "model_download_failed",
    "memory_card_viewed",
    "chat_session_started",
    "chat_message_sent",
    "backup_started",
    "backup_completed",
    "backup_failed",
    "theme_changed",
    "notification_opened",
    "opt_in_changed",
}

ALLOWED_PROP_KEYS = {
    "screen",
    "status",
    "stage",
    "action",
    "theme",
    "progress_percent",
    "duration_ms",
    "size_bytes",
    "count",
    "error_code",
    "is_success",
    "opted_in",
}


class AnalyticsEventItem(BaseModel):
    name: str = Field(..., description="Allow-listed telemetry event name")
    ts: datetime = Field(..., description="Client event timestamp (UTC)")
    props: dict[str, Any] = Field(default_factory=dict, description="Allow-listed key-value telemetry properties")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v not in ALLOWED_EVENT_NAMES:
            raise ValueError(f"Event name '{v}' is not in the allow-list.")
        return v

    @field_validator("props")
    @classmethod
    def validate_props(cls, v: dict[str, Any]) -> dict[str, Any]:
        for key, val in v.items():
            if key not in ALLOWED_PROP_KEYS:
                raise ValueError(f"Property key '{key}' is not permitted in anonymous analytics.")
            if isinstance(val, str):
                if len(val) > 40:
                    raise ValueError(f"Property value for '{key}' exceeds maximum allowed length of 40 characters.")
            elif not isinstance(val, (int, float, bool, type(None))):
                raise ValueError(f"Property '{key}' must be a primitive value (string, number, boolean).")
        return v


class AnalyticsIngestRequest(BaseModel):
    anon_id: str = Field(..., min_length=16, max_length=64, description="Rotating anonymous client identifier")
    app_version: str = Field(..., min_length=1, max_length=32, description="Client app semantic version")
    events: list[AnalyticsEventItem] = Field(..., min_length=1, max_length=100, description="Batch of telemetry events")


class AnalyticsIngestResponse(BaseModel):
    accepted: int
