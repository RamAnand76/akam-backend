import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.db.base import Base, JSONType


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    device_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    fcm_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    device_platform: Mapped[str] = mapped_column(String(20), default="android", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    token_generation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    preferences: Mapped["UserPreferences"] = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(5), default="22:00", nullable=False)
    quiet_hours_end: Mapped[str] = mapped_column(String(5), default="08:00", nullable=False)
    sunday_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    nudges_per_day: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    types_enabled: Mapped[dict] = mapped_column(JSONType, default=lambda: {
        "relationship_drift": True,
        "pattern_insight": True,
        "memory_unlock": True,
        "event_reminder": True,
        "sunday_digest": True,
        "brainrot_warning": True,
        "proactive_question": True,
    })

    user: Mapped["User"] = relationship("User", back_populates="preferences")
