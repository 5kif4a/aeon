import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram chat id
    language: Mapped[str] = mapped_column(String(8), default="en")
    name: Mapped[str] = mapped_column(String(64), default="")
    # Telegram @username without the "@", refreshed whenever the user contacts us.
    username: Mapped[str] = mapped_column(String(64), default="")
    gender: Mapped[str] = mapped_column(String(32), default="")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    country: Mapped[str] = mapped_column(String(64), default="")
    location: Mapped[str] = mapped_column(String(128), default="")
    activity: Mapped[str] = mapped_column(String(256), default="")
    interests: Mapped[str] = mapped_column(Text, default="")
    main_goal: Mapped[str] = mapped_column(Text, default="")
    current_problem: Mapped[str] = mapped_column(Text, default="")
    plan: Mapped[str] = mapped_column(String(32), default="Free")
    tokens: Mapped[int] = mapped_column(default=120)
    trial_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_rag_used: Mapped[int] = mapped_column(Integer, default=0)
    trial_council_used: Mapped[bool] = mapped_column(Boolean, default=False)
    pro_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pro_subscription_charge_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    pro_auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    trial_ending_reminded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_ended_reminded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pro_expired_reminded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active_agent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    daily_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    weekly_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Opt-out for marketing broadcasts; service broadcasts ignore it (see services/broadcasts.py).
    marketing_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    reminder_hour: Mapped[int] = mapped_column(Integer, default=9)
    last_daily_notification_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_life_weekly_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_daily_checkin_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_checkin_streak: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    goals: Mapped[list["Goal"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    diary_entries: Mapped[list["DiaryEntry"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    daily_usages: Mapped[list["DailyUsage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    payments: Mapped[list["BillingPayment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    last_reminder_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="goals")


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="diary_entries")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'closed')", name="ck_conversations_status"),
        Index(
            "uq_conversations_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.position",
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'agent')", name="ck_conversation_messages_role"),
        UniqueConstraint("conversation_id", "position", name="uq_conversation_messages_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class DailyUsage(Base):
    __tablename__ = "daily_usages"
    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_daily_usage_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    usage_date: Mapped[date] = mapped_column(Date, index=True)
    prompt_questions: Mapped[int] = mapped_column(Integer, default=0)
    rag_questions: Mapped[int] = mapped_column(Integer, default=0)
    council_questions: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="daily_usages")


class RagChunkRecord(Base):
    """One embedded passage of an agent's book corpus (see services/rag.py).

    ``embedding`` holds the L2-normalized vector packed as little-endian float32
    (``rag_embedding_dim * 4`` bytes). pgvector is deliberately not used: the corpora
    are a few thousand rows per (agent, language) and are scanned in memory with numpy.
    Rows are written only by ``scripts/embed_rag.py``.
    """

    __tablename__ = "rag_chunks"
    __table_args__ = (
        UniqueConstraint("agent_id", "language", "chunk_id", name="uq_rag_chunks_agent_lang_chunk"),
        Index("ix_rag_chunks_agent_language", "agent_id", "language"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(8))  # ru | en
    chunk_id: Mapped[str] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(Text, default="")
    chapter: Mapped[str] = mapped_column(Text, default="")
    page: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BillingPayment(Base):
    __tablename__ = "billing_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    invoice_payload: Mapped[str] = mapped_column(String(256))
    currency: Mapped[str] = mapped_column(String(8))
    amount: Mapped[int] = mapped_column(Integer)
    telegram_payment_charge_id: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    provider_payment_charge_id: Mapped[str] = mapped_column(String(256), default="")
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="paid")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="payments")


class ProductEvent(Base):
    """Append-only product analytics log (signups, payments, limits, failures, ops markers)."""

    __tablename__ = "product_events"
    __table_args__ = (Index("ix_product_events_type_created_at", "type", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Nullable: ops markers (digest sent) and system alerts are not tied to a user.
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class BotSetting(Base):
    """Runtime override of one bot setting (prompt text or generation knob).

    Code holds the defaults (`services.bot_settings.defaults`); a row exists only while the
    product owner has overridden a value from the admin panel.
    """

    __tablename__ = "bot_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str | int | float] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Telegram id of the admin who saved the value; nullable for imports/scripts.
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class AdminRole(Base):
    """A named set of admin-panel permissions (the rows of the access matrix).

    Permission keys are defined in code (`services.admin_access.PERMISSIONS`); a role stores
    the subset it grants, or `["*"]` for the built-in owner role. System roles ship with the
    product and cannot be deleted.
    """

    __tablename__ = "admin_roles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # slug
    title: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(200), default="")
    permissions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    accounts: Mapped[list["AdminAccount"]] = relationship(back_populates="role")


class AdminAccount(Base):
    """Admin access granted to one Telegram user, with the role that decides its scope.

    This table is the only source of access. What keeps the panel reachable is the "last
    manager" invariant in `services/admin_access.py`; an emptied table is repaired with
    `scripts/grant_admin.py`.
    """

    __tablename__ = "admin_accounts"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("admin_roles.id", ondelete="RESTRICT"), index=True
    )
    note: Mapped[str] = mapped_column(String(200), default="")
    granted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    role: Mapped[AdminRole] = relationship(back_populates="accounts")
    user: Mapped[User] = relationship()


class UserSegment(Base):
    """A reusable audience: either a saved filter (`dynamic`) or a fixed id list (`static`).

    Dynamic segments are re-evaluated every time they are counted or sent to, so a broadcast
    always reaches the current membership; `filters` is validated against
    `services.segments.FILTER_SPECS`.
    """

    __tablename__ = "user_segments"
    __table_args__ = (
        CheckConstraint("kind IN ('dynamic', 'static')", name="ck_user_segments_kind"),
        UniqueConstraint("name", name="uq_user_segments_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(300), default="")
    kind: Mapped[str] = mapped_column(String(16), default="dynamic")
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    members: Mapped[list["SegmentMember"]] = relationship(
        back_populates="segment", cascade="all, delete-orphan"
    )


class SegmentMember(Base):
    """One user pinned into a static segment."""

    __tablename__ = "segment_members"

    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_segments.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    segment: Mapped[UserSegment] = relationship(back_populates="members")


class Broadcast(Base):
    """One manual push to a segment: localized content plus its delivery state.

    `category` decides whether `users.marketing_enabled` is respected: `marketing` skips
    opted-out users, `service` (outages, policy changes) reaches everyone in the audience.
    Sending is done by the `broadcast_queue` job, one `broadcast_deliveries` row per
    recipient, so a restart resumes instead of sending twice.
    """

    __tablename__ = "broadcasts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'scheduled', 'sending', 'sent', 'canceled', 'failed')",
            name="ck_broadcasts_status",
        ),
        CheckConstraint("category IN ('marketing', 'service')", name="ck_broadcasts_category"),
        Index("ix_broadcasts_status_scheduled_at", "status", "scheduled_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(16), default="marketing")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    # Saved audience; when null the broadcast carries its own ad-hoc `filters`.
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_segments.id", ondelete="SET NULL"), nullable=True
    )
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {"en": {"text": ..., "buttonText": ..., "buttonUrl": ...}, "ru": {...}}; the user's
    # language decides which entry is used, with the default language as the fallback.
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    markdown: Mapped[bool] = mapped_column(Boolean, default=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    segment: Mapped[UserSegment | None] = relationship()
    deliveries: Mapped[list["BroadcastDelivery"]] = relationship(
        back_populates="broadcast", cascade="all, delete-orphan"
    )


class BroadcastDelivery(Base):
    """Per-recipient row of a broadcast: the queue, the audit trail and the idempotency key."""

    __tablename__ = "broadcast_deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'blocked')",
            name="ck_broadcast_deliveries_status",
        ),
        UniqueConstraint("broadcast_id", "user_id", name="uq_broadcast_deliveries_recipient"),
        Index("ix_broadcast_deliveries_broadcast_status", "broadcast_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    broadcast_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("broadcasts.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending")
    error: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    broadcast: Mapped[Broadcast] = relationship(back_populates="deliveries")
