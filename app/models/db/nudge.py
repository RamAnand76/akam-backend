import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.db.base import Base, JSONType


class Nudge(Base):
    __tablename__ = "nudges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # relationship_drift, pattern_insight, memory_unlock, event_reminder, etc.
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # high, medium, low
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    person_node_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cluster_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    pattern_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cta_primary_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    cta_secondary_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    deep_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_nudges_user_shown", "user_id", "shown"),
    )


class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RelationshipScore(Base):
    __tablename__ = "relationship_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    person_node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 1.0
    delta: Mapped[str] = mapped_column(String(20), default="0.00", nullable=False)
    delta_direction: Mapped[str] = mapped_column(String(10), default="flat", nullable=False)  # up, down, flat
    last_computed: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
