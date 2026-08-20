import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import User
from app.i18n import SUPPORTED_LANGUAGES
from app.services.billing import BillingSnapshot, effective_plan
from app.services.users import calculate_age

LanguageCode = Literal[SUPPORTED_LANGUAGES]  # type: ignore[valid-type]


class ProfileOut(BaseModel):
    id: int
    language: str
    name: str
    gender: str
    birthDate: date | None
    age: int | None
    country: str
    location: str
    activity: str
    interests: str
    mainGoal: str
    currentProblem: str
    plan: str
    tokens: int
    activeAgent: str | None

    @classmethod
    def from_user(cls, user: User) -> "ProfileOut":
        return cls(
            id=user.id,
            language=user.language,
            name=user.name,
            gender=user.gender,
            birthDate=user.birth_date,
            age=calculate_age(user.birth_date) if user.birth_date else None,
            country=user.country,
            location=user.location,
            activity=user.activity,
            interests=user.interests,
            mainGoal=user.main_goal,
            currentProblem=user.current_problem,
            plan=effective_plan(user),
            tokens=user.tokens,
            activeAgent=user.active_agent,
        )


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    gender: str | None = Field(default=None, max_length=32)
    birthDate: date | None = None
    country: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=128)
    activity: str | None = Field(default=None, max_length=256)
    interests: str | None = Field(default=None, max_length=2000)
    mainGoal: str | None = Field(default=None, max_length=2000)
    currentProblem: str | None = Field(default=None, max_length=2000)
    language: LanguageCode | None = None

    def to_user_fields(self) -> dict:
        mapping = {
            "name": "name",
            "gender": "gender",
            "birthDate": "birth_date",
            "country": "country",
            "location": "location",
            "activity": "activity",
            "interests": "interests",
            "mainGoal": "main_goal",
            "currentProblem": "current_problem",
            "language": "language",
        }
        data = self.model_dump(exclude_unset=True)
        return {mapping[key]: value for key, value in data.items() if key in mapping}


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    status: str
    created_at: datetime
    closed_at: datetime | None


class GoalCreate(BaseModel):
    text: str = Field(min_length=1, max_length=512)


class DiaryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    created_at: datetime


class DiaryEntryCreate(BaseModel):
    text: str = Field(min_length=1, max_length=700)


class StartDialogRequest(BaseModel):
    message: str = Field(default="", max_length=2000)


class StartCouncilRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class StartDialogResponse(BaseModel):
    ok: bool
    agentName: str
    botUsername: str


class AgentOut(BaseModel):
    id: str
    name: str
    role: str


class BillingStatusOut(BaseModel):
    plan: str
    dailyMode: str
    dailyUsed: int
    dailyLimit: int
    dailyRemaining: int
    promptUsed: int
    promptLimit: int
    ragUsed: int
    ragLimit: int
    trialTotalUsed: int
    trialTotalLimit: int
    councilUsed: int
    councilLimit: int
    councilRemaining: int
    canStartTrial: bool
    trialStartedAt: datetime | None
    trialExpiresAt: datetime | None
    proExpiresAt: datetime | None
    proAutoRenew: bool
    proPriceStars: int

    @classmethod
    def from_snapshot(cls, snapshot: BillingSnapshot) -> "BillingStatusOut":
        return cls(
            plan=snapshot.plan,
            dailyMode=snapshot.daily_mode,
            dailyUsed=snapshot.daily_used,
            dailyLimit=snapshot.daily_limit,
            dailyRemaining=snapshot.daily_remaining,
            promptUsed=snapshot.prompt_used,
            promptLimit=snapshot.prompt_limit,
            ragUsed=snapshot.rag_used,
            ragLimit=snapshot.rag_limit,
            trialTotalUsed=snapshot.trial_total_used,
            trialTotalLimit=snapshot.trial_total_limit,
            councilUsed=snapshot.council_used,
            councilLimit=snapshot.council_limit,
            councilRemaining=snapshot.council_remaining,
            canStartTrial=snapshot.can_start_trial,
            trialStartedAt=snapshot.trial_started_at,
            trialExpiresAt=snapshot.trial_expires_at,
            proExpiresAt=snapshot.pro_expires_at,
            proAutoRenew=snapshot.pro_auto_renew,
            proPriceStars=snapshot.pro_price_stars,
        )


class CheckoutOut(BaseModel):
    invoiceLink: str
    priceStars: int


class CancelSubscriptionOut(BaseModel):
    ok: bool
    activeUntil: datetime | None
