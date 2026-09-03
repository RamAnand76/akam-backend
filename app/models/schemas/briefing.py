from datetime import datetime
from pydantic import BaseModel


class PersonBriefingHeader(BaseModel):
    node_id: str
    name: str
    relationship_score: float = 0.82
    score_label: str = "Strong"
    score_delta: str = "+0.06"
    last_mentioned_days_ago: int = 1


class OpenPromiseItem(BaseModel):
    promise_id: str
    text: str
    mentioned_days_ago: int = 3
    source_message_id: str | None = None


class BriefingData(BaseModel):
    person: PersonBriefingHeader
    summary: str
    last_discussed: list[str] = []
    open_promises: list[OpenPromiseItem] = []
    patterns: list[str] = []
    watch_for: str | None = None
    conversation_starters: list[str] = []
    cached: bool = False
    generated_at: datetime


class RecentPersonChip(BaseModel):
    node_id: str
    name: str
    relationship_score: float
    last_mentioned_days_ago: int
