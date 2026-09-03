import uuid
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.db.base import Base, JSONType, VectorType


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' | 'assistant'
    input_mode: Mapped[str] = mapped_column(String(10), default="text", nullable=False)  # 'text' | 'voice'
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)  # 'en' | 'ml'
    parent_message_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True, index=True)
    branch_depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    branch_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    display_mode: Mapped[str] = mapped_column(String(30), default="bubble", nullable=False)  # 'bubble' | 'large_question' | 'pattern_insight'
    suggested_replies: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    intent_detected: Mapped[str | None] = mapped_column(String(50), nullable=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    embedding: Mapped[list | None] = mapped_column(VectorType, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    children: Mapped[list["Message"]] = relationship("Message", back_populates="parent", cascade="all, delete-orphan")
    parent: Mapped["Message | None"] = relationship("Message", back_populates="children", remote_side=[id])

    __table_args__ = (
        Index("ix_messages_user_session", "user_id", "session_date"),
        Index("ix_messages_user_parent", "user_id", "parent_message_id"),
    )
