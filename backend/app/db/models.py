import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram chat id
    language: Mapped[str] = mapped_column(String(8), default="en")
    name: Mapped[str] = mapped_column(String(64), default="")
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
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_rag_used: Mapped[int] = mapped_column(Integer, default=0)
    trial_council_used: Mapped[bool] = mapped_column(Boolean, default=False)
    pro_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pro_subscription_charge_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    pro_auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    active_agent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    daily_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    weekly_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
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
