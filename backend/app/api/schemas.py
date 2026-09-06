import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agents import agent_name
from app.core.admin_auth import is_admin
from app.db.models import Conversation, User
from app.i18n import SUPPORTED_LANGUAGES
from app.services.billing import BillingSnapshot, effective_plan
from app.services.users import calculate_age

LanguageCode = Literal[SUPPORTED_LANGUAGES]  # type: ignore[valid-type]

# Longest agent excerpt the Mini App shows on the "continue" card.
LAST_MESSAGE_LIMIT = 200


class ProfileOut(BaseModel):
    id: int
    language: str
    name: str
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
    dailyCheckinStreak: int
    isAdmin: bool = False

    @classmethod
    def from_user(cls, user: User) -> "ProfileOut":
        return cls(
            id=user.id,
            language=user.language,
            name=user.name,
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
            dailyCheckinStreak=user.daily_checkin_streak or 0,
            isAdmin=is_admin(user.id),
        )


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    birthDate: date | None = None
    country: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=128)
    activity: str | None = Field(default=None, max_length=256)
    interests: str | None = Field(default=None, max_length=300)
    mainGoal: str | None = Field(default=None, max_length=300)
    currentProblem: str | None = Field(default=None, max_length=300)
    language: LanguageCode | None = None

    def to_user_fields(self) -> dict:
        mapping = {
            "name": "name",
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


class ActiveConversationOut(BaseModel):
    agentId: str
    agentName: str
    title: str
    lastMessage: str
    messageCount: int
    updatedAt: datetime

    @classmethod
    def from_conversation(
        cls, conversation: Conversation, last_message: str, language: str
    ) -> "ActiveConversationOut":
        return cls(
            agentId=conversation.agent_id,
            agentName=agent_name(conversation.agent_id, language),
            title=conversation.title,
            lastMessage=_preview(last_message),
            messageCount=conversation.message_count,
            updatedAt=conversation.updated_at,
        )


def _preview(text: str) -> str:
    """One-line excerpt for a card: whitespace collapsed, capped at LAST_MESSAGE_LIMIT."""
    collapsed = " ".join(str(text or "").split())
    return collapsed[:LAST_MESSAGE_LIMIT]


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


# --- admin panel -------------------------------------------------------------------------


class AdminAuthConfigOut(BaseModel):
    botUsername: str
    enabled: bool
    # Telegram OAuth (OIDC) is the current way in; the widget stays as a fallback.
    oauthEnabled: bool = False


class AdminOAuthStartOut(BaseModel):
    authorizeUrl: str


class AdminOAuthCallbackIn(BaseModel):
    code: str = Field(min_length=1, max_length=2048)
    state: str = Field(min_length=1, max_length=256)


class AdminLoginIn(BaseModel):
    """Telegram Login Widget payload (https://core.telegram.org/widgets/login)."""

    id: int
    first_name: str = ""
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class AdminMeOut(BaseModel):
    id: int
    name: str
    language: str


class AdminSessionOut(BaseModel):
    token: str
    expiresAt: datetime
    admin: AdminMeOut


class WindowOut(BaseModel):
    label: str
    since: datetime
    until: datetime


class AdminStatsTotalsOut(BaseModel):
    usersTotal: int
    newUsers: int
    onboardingCompleted: int
    activeUsers: int
    promptQuestions: int
    ragQuestions: int
    councilQuestions: int
    conversationsStarted: int
    conversationsByAgent: dict[str, int]
    trialsStarted: int
    paymentsCount: int
    paymentsStars: int
    subscriptionsCanceled: int
    limitHits: int
    generationFailures: int
    proActive: int
    trialActive: int
    proExpiringSoon: int
    proNotRenewing: int


class AdminDailyPointOut(BaseModel):
    day: date
    newUsers: int
    activeUsers: int
    questions: int
    paymentsStars: int
    paymentsCount: int


class AdminStatsOut(BaseModel):
    window: WindowOut
    totals: AdminStatsTotalsOut
    series: list[AdminDailyPointOut]


class AdminUserOut(BaseModel):
    id: int
    name: str
    language: str
    country: str
    activity: str
    mainGoal: str
    plan: str
    birthDate: date | None
    createdAt: datetime
    lastActiveAt: datetime | None
    questionsTotal: int
    conversations: int
    paymentsStars: int
    proExpiresAt: datetime | None
    trialExpiresAt: datetime | None
    proAutoRenew: bool


class AdminPageOut[T](BaseModel):
    items: list[T]
    total: int


class AdminPaymentOut(BaseModel):
    id: uuid.UUID
    userId: int
    amount: int
    currency: str
    status: str
    isRecurring: bool
    subscriptionExpiresAt: datetime | None
    createdAt: datetime
    userLanguage: str = ""
    userCountry: str = ""


class AdminConversationOut(BaseModel):
    id: uuid.UUID
    userId: int
    agentId: str
    title: str
    status: str
    messageCount: int
    createdAt: datetime
    updatedAt: datetime
    userLanguage: str = ""
    userPlan: str = ""
    preview: str = ""


class AdminEventOut(BaseModel):
    id: uuid.UUID
    type: str
    payload: dict
    createdAt: datetime


class AdminUserDetailOut(BaseModel):
    user: AdminUserOut
    usage30d: dict[str, int]
    payments: list[AdminPaymentOut]
    conversations: list[AdminConversationOut]
    events: list[AdminEventOut]


class AdminMessageOut(BaseModel):
    id: uuid.UUID
    position: int
    role: str
    text: str
    createdAt: datetime


class AdminConversationDetailOut(BaseModel):
    conversation: AdminConversationOut
    messages: list[AdminMessageOut]


class GrantProIn(BaseModel):
    days: int = Field(ge=1, le=365)


# Bot settings: prompt texts and generation knobs edited from the admin panel.
SettingValue = str | int | float


class AdminSettingOut(BaseModel):
    key: str
    kind: Literal["text", "int", "float"]
    description: str
    default: SettingValue
    # Stored override, or null when the code default applies.
    value: SettingValue | None
    min: float | None = None
    max: float | None = None
    updatedAt: datetime | None
    updatedBy: int | None


class AdminSettingIn(BaseModel):
    value: SettingValue


class AdminPromptPreviewIn(BaseModel):
    agentId: str
    message: str = Field(min_length=1, max_length=4000)
    language: LanguageCode = "ru"
    # Unsaved draft values applied for this single generation only.
    overrides: dict[str, SettingValue] = Field(default_factory=dict)


class AdminPromptPreviewOut(BaseModel):
    text: str
