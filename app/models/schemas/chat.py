from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    language: Literal["en", "ml"] = "en"
    input_mode: Literal["text", "voice"] = "text"
    session_date: date
    client_message_id: str


class BranchMessageRequest(BaseModel):
    parent_message_id: str
    content: str = Field(..., min_length=1, max_length=10000)
    language: Literal["en", "ml"] = "en"
    input_mode: Literal["text", "voice"] = "text"
    client_message_id: str


class SuggestedReplyRequest(BaseModel):
    reply_text: str = Field(..., min_length=1, max_length=1000)
    parent_ai_message_id: str
    client_message_id: str


class MessageItem(BaseModel):
    message_id: str
    client_message_id: str | None = None
    content: str
    role: str
    parent_message_id: str | None = None
    branch_depth: int = 0
    branch_index: int = 0
    session_date: date
    created_at: datetime


class AIResponseItem(BaseModel):
    message_id: str
    content: str
    role: str = "assistant"
    display_mode: str = "bubble"
    suggested_replies: list[str] = []
    pattern_triggered: bool = False
    pattern_id: str | None = None


class ProcessingDetails(BaseModel):
    intent_detected: str | None = None
    entities_extracted: list[str] = []
    graph_updated: bool = True
    clusters_updated: list[str] = []


class SendMessageResponseData(BaseModel):
    message: MessageItem
    ai_response: AIResponseItem
    processing: ProcessingDetails


class VoiceMessageResponseData(SendMessageResponseData):
    transcript: str
    language_detected: str
    audio_duration_ms: int


class BranchSibling(BaseModel):
    message_id: str
    content: str
    branch_index: int


class BranchMessageResponseData(BaseModel):
    message: MessageItem
    ai_response: AIResponseItem
    siblings: list[BranchSibling] = []


class MessageThreadNode(BaseModel):
    message_id: str
    content: str
    role: str
    input_mode: str = "text"
    transcript: str | None = None
    language: str = "en"
    parent_message_id: str | None = None
    branch_depth: int = 0
    branch_index: int = 0
    display_mode: str = "bubble"
    suggested_replies: list[str] = []
    children: list["MessageThreadNode"] = []
    cluster_memberships: list[dict] = []
    created_at: datetime


class DeleteMessageData(BaseModel):
    deleted_count: int
    message_id: str
