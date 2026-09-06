"""Product-owner panel: metrics, users, conversations, payments. Allowlisted admins only."""

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from app.agents import AGENTS
from app.api.deps import AdminUser, SessionDep
from app.api.schemas import (
    AdminAuthConfigOut,
    AdminConversationDetailOut,
    AdminConversationOut,
    AdminDailyPointOut,
    AdminEventOut,
    AdminLoginIn,
    AdminMeOut,
    AdminMessageOut,
    AdminOAuthCallbackIn,
    AdminOAuthStartOut,
    AdminPageOut,
    AdminPaymentOut,
    AdminPromptPreviewIn,
    AdminPromptPreviewOut,
    AdminSessionOut,
    AdminSettingIn,
    AdminSettingOut,
    AdminStatsOut,
    AdminStatsTotalsOut,
    AdminUserDetailOut,
    AdminUserOut,
    GrantProIn,
    WindowOut,
)
from app.core import admin_auth, admin_oauth
from app.core.config import get_settings
from app.db.models import BillingPayment, Conversation, ProductEvent, User
from app.services import admin, agent_chat, billing, bot_settings, events, stats, users

router = APIRouter(prefix="/admin", tags=["admin"])

STATS_DAYS = {7, 30, 90}
# The prompt preview is a cost-capped, admin-only Gemini call outside the billing flow.
PREVIEW_MAX_OUTPUT_TOKENS = 800
PREVIEW_TIMEOUT_SECONDS = 40


# --- auth --------------------------------------------------------------------------------


@router.get("/auth/config", response_model=AdminAuthConfigOut)
async def auth_config() -> AdminAuthConfigOut:
    settings = get_settings()
    return AdminAuthConfigOut(
        botUsername=settings.bot_username,
        enabled=bool(settings.ops_admin_id_list),
        oauthEnabled=admin_oauth.is_configured(),
    )


@router.post("/auth/oauth/start", response_model=AdminOAuthStartOut)
async def oauth_start() -> AdminOAuthStartOut:
    """Begin the Telegram OIDC login; the PKCE verifier stays on the server."""
    try:
        authorize_url, _ = admin_oauth.begin_login()
    except admin_auth.AdminAuthError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return AdminOAuthStartOut(authorizeUrl=authorize_url)


@router.post("/auth/oauth/callback", response_model=AdminSessionOut)
async def oauth_callback(payload: AdminOAuthCallbackIn, session: SessionDep) -> AdminSessionOut:
    try:
        identity = await admin_oauth.complete_login(payload.code, payload.state)
    except admin_auth.AdminAuthError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    if not admin_auth.is_admin(identity.user_id):
        raise HTTPException(status_code=403, detail="Admin access required")
    user = await users.get_or_create_user(session, identity.user_id, name=identity.name)
    token, expires_at = admin_auth.issue_session_token(identity.user_id)
    await admin.record_admin_event(session, events.ADMIN_LOGIN, identity.user_id, method="oidc")
    return AdminSessionOut(
        token=token,
        expiresAt=datetime.fromtimestamp(expires_at, tz=UTC),
        admin=_admin_me(user),
    )


@router.post("/auth/telegram", response_model=AdminSessionOut)
async def login_with_telegram(payload: AdminLoginIn, session: SessionDep) -> AdminSessionOut:
    try:
        user_id = admin_auth.validate_login_widget(payload.model_dump(exclude_none=True))
    except admin_auth.AdminAuthError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    if not admin_auth.is_admin(user_id):
        raise HTTPException(status_code=403, detail="Admin access required")
    user = await users.get_or_create_user(session, user_id, name=payload.first_name)
    token, expires_at = admin_auth.issue_session_token(user_id)
    await admin.record_admin_event(session, events.ADMIN_LOGIN, user_id, method="login_widget")
    return AdminSessionOut(
        token=token,
        expiresAt=datetime.fromtimestamp(expires_at, tz=UTC),
        admin=_admin_me(user),
    )


@router.get("/me", response_model=AdminMeOut)
async def admin_me(user: AdminUser) -> AdminMeOut:
    return _admin_me(user)


def _admin_me(user: User) -> AdminMeOut:
    return AdminMeOut(id=user.id, name=user.name, language=user.language)


# --- metrics -----------------------------------------------------------------------------


@router.get("/stats", response_model=AdminStatsOut)
async def admin_stats(
    _: AdminUser, session: SessionDep, days: int = Query(default=30)
) -> AdminStatsOut:
    if days not in STATS_DAYS:
        raise HTTPException(status_code=422, detail="days must be one of 7, 30, 90")
    now = datetime.now(UTC)
    window = stats.last_days_window(now, get_settings().ops_timezone, days)
    collected = await stats.collect_stats(session, window, now)
    series = await admin.daily_series(session, window.since, window.until)
    return AdminStatsOut(
        window=WindowOut(label=window.label, since=window.since, until=window.until),
        totals=AdminStatsTotalsOut(
            usersTotal=collected.users_total,
            newUsers=collected.new_users,
            onboardingCompleted=collected.onboarding_completed,
            activeUsers=collected.active_users,
            promptQuestions=collected.prompt_questions,
            ragQuestions=collected.rag_questions,
            councilQuestions=collected.council_questions,
            conversationsStarted=collected.conversations_started,
            conversationsByAgent=collected.conversations_by_agent,
            trialsStarted=collected.trials_started,
            paymentsCount=collected.payments_count,
            paymentsStars=collected.payments_stars,
            subscriptionsCanceled=collected.subscriptions_canceled,
            limitHits=collected.limit_hits,
            generationFailures=collected.generation_failures,
            proActive=collected.pro_active,
            trialActive=collected.trial_active,
            proExpiringSoon=collected.pro_expiring_soon,
            proNotRenewing=collected.pro_not_renewing,
        ),
        series=[
            AdminDailyPointOut(
                day=point.day,
                newUsers=point.new_users,
                activeUsers=point.active_users,
                questions=point.questions,
                paymentsStars=point.payments_stars,
                paymentsCount=point.payments_count,
            )
            for point in series
        ],
    )


# --- users -------------------------------------------------------------------------------


def _user_out(
    user: User,
    *,
    plan: str,
    questions_total: int = 0,
    last_active_at: datetime | None = None,
    conversations: int = 0,
    payments_stars: int = 0,
) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        name=user.name,
        language=user.language,
        country=user.country,
        activity=user.activity,
        mainGoal=user.main_goal,
        plan=plan,
        birthDate=user.birth_date,
        createdAt=user.created_at,
        lastActiveAt=last_active_at,
        questionsTotal=questions_total,
        conversations=conversations,
        paymentsStars=payments_stars,
        proExpiresAt=user.pro_expires_at,
        trialExpiresAt=user.trial_expires_at,
        proAutoRenew=bool(user.pro_auto_renew),
    )


def _payment_out(payment: BillingPayment, language: str = "", country: str = "") -> AdminPaymentOut:
    return AdminPaymentOut(
        id=payment.id,
        userId=payment.user_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        isRecurring=bool(payment.is_recurring),
        subscriptionExpiresAt=payment.subscription_expires_at,
        createdAt=payment.created_at,
        userLanguage=language,
        userCountry=country,
    )


def _conversation_out(
    conversation: Conversation, *, language: str = "", plan: str = "", preview: str = ""
) -> AdminConversationOut:
    return AdminConversationOut(
        id=conversation.id,
        userId=conversation.user_id,
        agentId=conversation.agent_id,
        title=conversation.title,
        status=conversation.status,
        messageCount=conversation.message_count,
        createdAt=conversation.created_at,
        updatedAt=conversation.updated_at,
        userLanguage=language,
        userPlan=plan,
        preview=preview,
    )


def _event_out(event: ProductEvent) -> AdminEventOut:
    return AdminEventOut(
        id=event.id, type=event.type, payload=event.payload, createdAt=event.created_at
    )


@router.get("/users", response_model=AdminPageOut[AdminUserOut])
async def admin_users(
    _: AdminUser,
    session: SessionDep,
    q: str = "",
    plan: str = "",
    limit: int = Query(default=50, ge=1, le=admin.MAX_PAGE),
    offset: int = Query(default=0, ge=0),
) -> AdminPageOut[AdminUserOut]:
    page = await admin.list_users(session, query=q, plan=plan, limit=limit, offset=offset)
    return AdminPageOut(
        items=[
            _user_out(
                row.user,
                plan=row.plan,
                questions_total=row.questions_total,
                last_active_at=row.last_active_at,
                conversations=row.conversations,
                payments_stars=row.payments_stars,
            )
            for row in page.items
        ],
        total=page.total,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
async def admin_user_detail(user_id: int, _: AdminUser, session: SessionDep) -> AdminUserDetailOut:
    detail = await admin.get_user_detail(session, user_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="User not found")
    return AdminUserDetailOut(
        user=_user_out(
            detail.user,
            plan=detail.plan,
            questions_total=sum(detail.usage_30d.values()),
            conversations=len(detail.conversations),
            payments_stars=sum(p.amount for p in detail.payments if p.status == "paid"),
        ),
        usage30d=detail.usage_30d,
        payments=[_payment_out(payment) for payment in detail.payments],
        conversations=[_conversation_out(c) for c in detail.conversations],
        events=[_event_out(event) for event in detail.events],
    )


@router.post("/users/{user_id}/grant-pro", response_model=AdminUserOut)
async def admin_grant_pro(
    user_id: int, payload: GrantProIn, actor: AdminUser, session: SessionDep
) -> AdminUserOut:
    user = await admin.grant_pro(session, user_id, days=payload.days, granted_by=actor.id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_out(user, plan=billing.effective_plan(user))


# --- conversations -----------------------------------------------------------------------


@router.get("/conversations", response_model=AdminPageOut[AdminConversationOut])
async def admin_conversations(
    _: AdminUser,
    session: SessionDep,
    userId: int | None = None,
    agentId: str = "",
    status: str = "",
    limit: int = Query(default=50, ge=1, le=admin.MAX_PAGE),
    offset: int = Query(default=0, ge=0),
) -> AdminPageOut[AdminConversationOut]:
    page = await admin.list_conversations(
        session, user_id=userId, agent_id=agentId, status=status, limit=limit, offset=offset
    )
    return AdminPageOut(
        items=[
            _conversation_out(
                row.conversation,
                language=row.user_language,
                plan=row.user_plan,
                preview=row.preview,
            )
            for row in page.items
        ],
        total=page.total,
    )


@router.get("/conversations/{conversation_id}", response_model=AdminConversationDetailOut)
async def admin_conversation_detail(
    conversation_id: uuid.UUID, actor: AdminUser, session: SessionDep
) -> AdminConversationDetailOut:
    found = await admin.get_conversation(session, conversation_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation, messages = found
    # Reading someone's dialogue is sensitive: keep an audit trail of who opened what.
    await admin.record_admin_event(
        session,
        events.ADMIN_VIEW_CONVERSATION,
        actor.id,
        conversation_id=str(conversation.id),
        subject_user_id=conversation.user_id,
    )
    return AdminConversationDetailOut(
        conversation=_conversation_out(conversation),
        messages=[
            AdminMessageOut(
                id=message.id,
                position=message.position,
                role=message.role,
                text=message.text,
                createdAt=message.created_at,
            )
            for message in messages
        ],
    )


# --- payments ----------------------------------------------------------------------------


@router.get("/payments", response_model=AdminPageOut[AdminPaymentOut])
async def admin_payments(
    _: AdminUser,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=admin.MAX_PAGE),
    offset: int = Query(default=0, ge=0),
) -> AdminPageOut[AdminPaymentOut]:
    page = await admin.list_payments(session, limit=limit, offset=offset)
    return AdminPageOut(
        items=[
            _payment_out(payment, language, country) for payment, language, country in page.items
        ],
        total=page.total,
    )


# --- bot settings ------------------------------------------------------------------------


def _setting_out(state: bot_settings.SettingState) -> AdminSettingOut:
    bounds = state.spec.bounds
    return AdminSettingOut(
        key=state.spec.key,
        kind=state.spec.kind,
        description=state.spec.description,
        default=state.spec.default,
        value=state.value,
        min=bounds[0] if bounds else None,
        max=bounds[1] if bounds else None,
        updatedAt=state.updated_at,
        updatedBy=state.updated_by,
    )


async def _setting_state(session: SessionDep, key: str) -> AdminSettingOut:
    for state in await bot_settings.list_settings(session):
        if state.spec.key == key:
            return _setting_out(state)
    raise HTTPException(status_code=404, detail="Unknown setting")


@router.get("/settings", response_model=list[AdminSettingOut])
async def admin_settings(_: AdminUser, session: SessionDep) -> list[AdminSettingOut]:
    return [_setting_out(state) for state in await bot_settings.list_settings(session)]


@router.put("/settings/{key}", response_model=AdminSettingOut)
async def admin_set_setting(
    key: str, payload: AdminSettingIn, actor: AdminUser, session: SessionDep
) -> AdminSettingOut:
    try:
        await bot_settings.set_value(session, key, payload.value, actor.id)
    except bot_settings.UnknownSettingError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except bot_settings.SettingError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return await _setting_state(session, key)


@router.delete("/settings/{key}", response_model=AdminSettingOut)
async def admin_reset_setting(key: str, actor: AdminUser, session: SessionDep) -> AdminSettingOut:
    try:
        await bot_settings.delete_value(session, key, actor.id)
    except bot_settings.UnknownSettingError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return await _setting_state(session, key)


@router.post("/settings/preview", response_model=AdminPromptPreviewOut)
async def admin_prompt_preview(
    payload: AdminPromptPreviewIn, actor: AdminUser, session: SessionDep
) -> AdminPromptPreviewOut:
    """Run a message through Gemini with unsaved draft settings.

    Deliberately outside billing (no grant is reserved: the caller is an allowlisted
    admin, not a subscriber) and outside Telegram: nothing is sent to any chat and no
    conversation is stored. Output size and duration are capped to bound the cost.
    """
    if payload.agentId not in AGENTS:
        raise HTTPException(status_code=404, detail="Unknown agent")
    try:
        overrides = {
            key: bot_settings.validate(key, value) for key, value in payload.overrides.items()
        }
    except bot_settings.UnknownSettingError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except bot_settings.SettingError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    requested_tokens = overrides.get(bot_settings.MAX_OUTPUT_TOKENS_KEY)
    overrides[bot_settings.MAX_OUTPUT_TOKENS_KEY] = min(
        PREVIEW_MAX_OUTPUT_TOKENS,
        int(requested_tokens)
        if isinstance(requested_tokens, int | float)
        else bot_settings.get_int(
            bot_settings.MAX_OUTPUT_TOKENS_KEY, get_settings().gemini_max_output_tokens
        ),
    )
    await admin.record_admin_event(
        session,
        events.ADMIN_PROMPT_PREVIEW,
        actor.id,
        agent_id=payload.agentId,
        language=payload.language,
        override_keys=sorted(payload.overrides),
    )
    try:
        with bot_settings.draft_overrides(overrides):
            async with asyncio.timeout(PREVIEW_TIMEOUT_SECONDS):
                text = await agent_chat.generate_answer(
                    payload.agentId,
                    payload.message,
                    user=None,
                    history=[],
                    language=payload.language,
                )
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail="Preview timed out") from error
    except Exception as error:  # Gemini/network failures: surface them, no retries here
        raise HTTPException(status_code=502, detail=f"Preview failed: {error}") from error
    return AdminPromptPreviewOut(text=text)
