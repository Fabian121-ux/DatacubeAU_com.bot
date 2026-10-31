from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ConversationTakeover(Base):
    __tablename__ = "conversation_takeovers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False, server_default=text("'fabian_active'"))
    auto_assist_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    inactivity_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("120"))
    pending_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    takeover_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_inbound_message_id: Mapped[str | None] = mapped_column(String(220))
    last_owner_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assisting_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    handoff_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_transition_reason: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
