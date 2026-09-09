/**
 * Dev-only stand-ins for the admin API.
 *
 * `pnpm dev` opens the panel without a credential, so every read answers 401. Returning
 * empty lists left whole screens looking like features that do not exist - the settings tab
 * had no fields at all, the segment editor had no conditions, the role matrix had no
 * permissions. These fixtures fill that in, so the panel shows what the UI actually is.
 *
 * Catalogues here (settings, filters, permissions, roles) mirror the backend: keys and
 * bounds come from `services/bot_settings.py`, `services/segments.FILTER_SPECS` and
 * `services/admin_access.PERMISSIONS`. Rows are obviously fake ("Demo …") so nobody mistakes
 * them for production data. Loaded through a dynamic import from `adminQueries`, so this
 * module ends up in its own chunk and never runs in a release build.
 */

import type {
  AdminAccess,
  AdminConversation,
  AdminConversationDetail,
  AdminPage,
  AdminPayment,
  AdminSetting,
  AdminStats,
  AdminUser,
  AdminUserDetail,
  Broadcast,
  BroadcastDelivery,
  Segment,
  SegmentFilterSpec,
  SegmentPreview,
} from "./adminTypes";
import { AGENTS } from "./agents";

const DAY = 86_400_000;
const ago = (days: number) => new Date(Date.now() - days * DAY).toISOString();

function setting(
  key: string,
  kind: AdminSetting["kind"],
  value: AdminSetting["default"],
  description: string,
  bounds?: [number, number],
  overridden = false,
): AdminSetting {
  return {
    key,
    kind,
    description,
    default: value,
    value: overridden ? value : null,
    min: bounds?.[0] ?? null,
    max: bounds?.[1] ?? null,
    updatedAt: overridden ? ago(2) : null,
    updatedBy: overridden ? 900000001 : null,
  };
}

/** Every editable key the bot exposes, with the same kinds and bounds as the backend. */
export function devSettings(): AdminSetting[] {
  return [
    setting(
      "response_style",
      "text",
      "Answer in two or three short paragraphs. No lists unless asked. Address the user " +
        "formally. End with one concrete step they can take today.",
      "Shared response-style block appended to every agent system prompt.",
    ),
    setting("temperature", "float", 0.8, "Gemini temperature.", [0, 2]),
    setting(
      "history_turns",
      "int",
      12,
      "How many recent dialogue messages are sent to Gemini.",
      [2, 40],
    ),
    setting("max_output_tokens", "int", 2500, "Maximum output tokens per answer.", [200, 8000]),
    ...Object.entries(AGENTS).map(([agentId, agent]) =>
      setting(
        `agent_prompt.${agentId}`,
        "text",
        `You are ${agent.name.en}. ${agent.role.en}. Speak from your own writings and ` +
          "experience, never as a modern coach. Keep the reply grounded in the user's own " +
          "situation.",
        `System prompt of ${agent.name.en}.`,
        undefined,
        agentId === "aurelius",
      ),
    ),
  ];
}

/** The segment condition catalogue, mirroring `services/segments.FILTER_SPECS`. */
export function devSegmentFilters(): SegmentFilterSpec[] {
  const spec = (
    key: string,
    kind: SegmentFilterSpec["kind"],
    description: string,
    options: string[] = [],
  ): SegmentFilterSpec => ({ key, kind, description, options });
  return [
    spec("plans", "enum", "Effective plan right now", ["Free", "Trial", "Pro"]),
    spec("languages", "enum", "Interface language", ["ru", "en"]),
    spec("genders", "enum", "Gender from onboarding", ["male", "female", "other"]),
    spec("countries", "ids", "Country from onboarding (exact names)"),
    spec("agents", "enum", "Has talked to any of these agents", Object.keys(AGENTS)),
    spec("onboarded", "bool", "Finished onboarding (birth date set)"),
    spec("hasPaid", "bool", "Has at least one paid Stars charge"),
    spec("trialUsed", "bool", "Has ever started the trial"),
    spec("proAutoRenew", "bool", "Pro subscription renews automatically"),
    spec("dailyNotificationsEnabled", "bool", "Daily notifications are on"),
    spec("marketingEnabled", "bool", "Has not opted out of marketing"),
    spec("signedUpWithinDays", "int", "Signed up in the last N days"),
    spec("signedUpBeforeDays", "int", "Signed up more than N days ago"),
    spec("activeWithinDays", "int", "Asked something or used the app in the last N days"),
    spec("inactiveForDays", "int", "Nothing at all in the last N days"),
    spec("questionsMin", "int", "At least this many questions in total"),
    spec("questionsMax", "int", "At most this many questions in total"),
    spec("streakMin", "int", "Daily check-in streak of at least"),
    spec("userIds", "ids", "Only these user ids"),
  ];
}

/** Permission catalogue plus the built-in roles, so the matrix has rows and columns. */
export function devAccess(): AdminAccess {
  const permission = (key: string, group: string, description: string) => ({
    key,
    group,
    description,
  });
  const permissions = [
    permission("stats.view", "dashboard", "See the dashboard and product metrics"),
    permission("users.view", "users", "Browse users and open a user card"),
    permission("users.grant_pro", "users", "Grant Pro without a payment"),
    permission("conversations.view", "users", "Read user dialogues"),
    permission("payments.view", "billing", "See payments"),
    permission("payments.refund", "billing", "Refund a Stars charge"),
    permission("settings.view", "bot", "See runtime bot settings"),
    permission("settings.edit", "bot", "Change prompts and generation knobs"),
    permission("segments.view", "audience", "See segments and their size"),
    permission("segments.edit", "audience", "Create, change and delete segments"),
    permission("broadcasts.view", "audience", "See broadcasts and their delivery stats"),
    permission("broadcasts.edit", "audience", "Compose and edit broadcast drafts"),
    permission("broadcasts.send", "audience", "Send, schedule and cancel broadcasts"),
    permission("admins.view", "access", "See admins and roles"),
    permission("admins.manage", "access", "Grant, change and revoke admin access"),
  ];
  const support = [
    "stats.view",
    "users.view",
    "users.grant_pro",
    "conversations.view",
    "payments.view",
    "payments.refund",
  ];
  const marketing = [
    "stats.view",
    "users.view",
    "segments.view",
    "segments.edit",
    "broadcasts.view",
    "broadcasts.edit",
    "broadcasts.send",
  ];
  return {
    permissions,
    roles: [
      {
        id: "owner",
        title: "Owner",
        description: "Full access, including who else is an admin",
        permissions: ["*"],
        isSystem: true,
        isOwner: true,
        admins: 1,
      },
      {
        id: "support",
        title: "Support",
        description: "Answers users: reads dialogues, grants Pro, refunds payments",
        permissions: support,
        isSystem: true,
        isOwner: false,
        admins: 1,
      },
      {
        id: "marketing",
        title: "Marketing",
        description: "Builds segments and sends broadcasts; no dialogues, no refunds",
        permissions: marketing,
        isSystem: true,
        isOwner: false,
        admins: 0,
      },
    ],
    admins: [
      {
        userId: 900000001,
        name: "Demo owner",
        username: "demo_owner",
        roleId: "owner",
        roleTitle: "Owner",
        permissions: ["*"],
        note: "seeded by scripts/grant_admin.py",
        grantedBy: null,
      },
      {
        userId: 900000002,
        name: "Demo support",
        username: "demo_support",
        roleId: "support",
        roleTitle: "Support",
        permissions: support,
        note: "on duty",
        grantedBy: 900000001,
      },
    ],
  };
}

function user(
  id: number,
  name: string,
  plan: AdminUser["plan"],
  language: string,
  country: string,
  extra: Partial<AdminUser> = {},
): AdminUser {
  return {
    id,
    name,
    username: name.toLowerCase().replace(/\s+/g, "_"),
    language,
    country,
    activity: "Product manager",
    mainGoal: "Ship the next release without burning out",
    plan,
    birthDate: "1990-04-17",
    createdAt: ago(40),
    lastActiveAt: ago(1),
    questionsTotal: 34,
    conversations: 6,
    paymentsStars: plan === "Pro" ? 350 : 0,
    proExpiresAt: plan === "Pro" ? ago(-20) : null,
    trialExpiresAt: plan === "Trial" ? ago(-2) : null,
    proAutoRenew: plan === "Pro",
    ...extra,
  };
}

export function devUsers(): AdminPage<AdminUser> {
  return {
    items: [
      user(900000101, "Demo Pro", "Pro", "ru", "Kazakhstan"),
      user(900000102, "Demo Trial", "Trial", "en", "Serbia", { questionsTotal: 9 }),
      user(900000103, "Demo Free", "Free", "ru", "Georgia", {
        questionsTotal: 2,
        conversations: 1,
        lastActiveAt: ago(9),
      }),
    ],
    total: 3,
  };
}

export function devUserDetail(userId: number): AdminUserDetail {
  return {
    user: user(userId, "Demo Pro", "Pro", "ru", "Kazakhstan"),
    usage30d: { prompt: 18, rag: 11, council: 2 },
    payments: devPayments().items,
    conversations: devConversations().items,
    events: [
      { id: "e1", type: "payment_succeeded", payload: { amount: 350 }, createdAt: ago(3) },
      { id: "e2", type: "question_limit_hit", payload: {}, createdAt: ago(6) },
      { id: "e3", type: "user_created", payload: { language: "ru" }, createdAt: ago(40) },
    ],
  };
}

function conversation(
  id: string,
  agentId: string,
  status: AdminConversation["status"],
  preview: string,
): AdminConversation {
  return {
    id,
    userId: 900000101,
    agentId,
    title: preview.slice(0, 40),
    status,
    messageCount: 4,
    createdAt: ago(3),
    updatedAt: ago(1),
    userName: "Demo Pro",
    userUsername: "demo_pro",
    userLanguage: "ru",
    userPlan: "Pro",
    preview,
  };
}

export function devConversations(): AdminPage<AdminConversation> {
  return {
    items: [
      conversation("c1", "aurelius", "active", "Как перестать откладывать важное?"),
      conversation("c2", "machiavelli", "closed", "Стоит ли нанимать первого сотрудника?"),
    ],
    total: 2,
  };
}

export function devConversationDetail(conversationId: string): AdminConversationDetail {
  return {
    conversation: conversation(conversationId, "aurelius", "closed", "Как перестать откладывать?"),
    messages: [
      {
        id: "m1",
        position: 0,
        role: "user",
        text: "Как перестать откладывать важное?",
        createdAt: ago(3),
      },
      {
        id: "m2",
        position: 1,
        role: "agent",
        text: "Начните с одного дела и одного часа. Остальное — следствие.",
        createdAt: ago(3),
      },
    ],
  };
}

export function devPayments(): AdminPage<AdminPayment> {
  const payment = (
    id: string,
    status: string,
    amount: number,
    isRecurring: boolean,
  ): AdminPayment => ({
    id,
    userId: 900000101,
    amount,
    currency: "XTR",
    status,
    isRecurring,
    subscriptionExpiresAt: ago(-20),
    createdAt: ago(status === "refunded" ? 12 : 3),
    userLanguage: "ru",
    userCountry: "Kazakhstan",
  });
  return {
    items: [payment("p1", "paid", 350, true), payment("p2", "refunded", 350, false)],
    total: 2,
  };
}

export function devSegments(): Segment[] {
  return [
    {
      id: "s1",
      name: "Demo · active Pro",
      description: "Pro, asked something in the last week",
      kind: "dynamic",
      filters: { plans: ["Pro"], activeWithinDays: 7 },
      size: 128,
      memberCount: 0,
      userIds: [],
      createdBy: 900000001,
      createdAt: ago(20),
      updatedAt: ago(4),
    },
    {
      id: "s2",
      name: "Demo · beta list",
      description: "Hand-picked ids",
      kind: "static",
      filters: {},
      size: 3,
      memberCount: 3,
      userIds: [900000101, 900000102, 900000103],
      createdBy: 900000001,
      createdAt: ago(11),
      updatedAt: ago(11),
    },
  ];
}

export function devSegment(segmentId: string): Segment {
  const found = devSegments().find((segment) => segment.id === segmentId);
  return found ?? { ...devSegments()[0], id: segmentId };
}

export function devSegmentPreview(): SegmentPreview {
  return {
    size: 128,
    byLanguage: { ru: 96, en: 32 },
    sample: devUsers().items,
  };
}

function broadcast(
  id: string,
  title: string,
  status: Broadcast["status"],
  extra: Partial<Broadcast> = {},
): Broadcast {
  return {
    id,
    title,
    category: "marketing",
    status,
    segmentId: "s1",
    segmentName: "Demo · active Pro",
    filters: {},
    content: {
      ru: {
        text: "Pro со скидкой до конца недели.",
        buttonText: "Открыть",
        buttonUrl: "https://t.me/aeon",
      },
      en: {
        text: "Pro is on sale until Sunday.",
        buttonText: "Open",
        buttonUrl: "https://t.me/aeon",
      },
    },
    markdown: true,
    scheduledAt: null,
    startedAt: null,
    finishedAt: null,
    totalRecipients: 0,
    sentCount: 0,
    failedCount: 0,
    blockedCount: 0,
    pendingCount: 0,
    createdBy: 900000001,
    createdAt: ago(6),
    updatedAt: ago(5),
    ...extra,
  };
}

export function devBroadcasts(): Broadcast[] {
  return [
    broadcast("b1", "Demo · September promo", "sent", {
      startedAt: ago(5),
      finishedAt: ago(5),
      totalRecipients: 128,
      sentCount: 120,
      blockedCount: 6,
      failedCount: 2,
    }),
    broadcast("b2", "Demo · maintenance notice", "sending", {
      category: "service",
      startedAt: ago(0),
      totalRecipients: 128,
      sentCount: 41,
      pendingCount: 87,
    }),
    broadcast("b3", "Demo · draft", "draft"),
  ];
}

export function devBroadcast(broadcastId: string): Broadcast {
  const found = devBroadcasts().find((row) => row.id === broadcastId);
  return found ?? { ...devBroadcasts()[2], id: broadcastId };
}

export function devDeliveries(): BroadcastDelivery[] {
  return [
    {
      userId: 900000101,
      name: "Demo Pro",
      username: "demo_pro",
      language: "ru",
      status: "sent",
      error: "",
      sentAt: ago(5),
    },
    {
      userId: 900000102,
      name: "Demo Trial",
      username: "demo_trial",
      language: "en",
      status: "blocked",
      error: "Forbidden: bot was blocked by the user",
      sentAt: null,
    },
    {
      userId: 900000103,
      name: "Demo Free",
      username: "demo_free",
      language: "ru",
      status: "pending",
      error: "",
      sentAt: null,
    },
  ];
}

/** A plausible curve so the dashboard charts show their shape, not a flat zero line. */
export function devStats(days: number): AdminStats {
  const until = new Date();
  const since = new Date(until.getTime() - days * DAY);
  const series = Array.from({ length: days }, (_, index) => {
    const wave = 1 + Math.sin(index / 3) / 2;
    return {
      day: new Date(since.getTime() + index * DAY).toISOString().slice(0, 10),
      newUsers: Math.round(4 * wave),
      activeUsers: Math.round(30 * wave),
      questions: Math.round(90 * wave),
      paymentsStars: index % 4 === 0 ? 350 : 0,
      paymentsCount: index % 4 === 0 ? 1 : 0,
    };
  });
  const sum = (pick: (point: (typeof series)[number]) => number) =>
    series.reduce((total, point) => total + pick(point), 0);
  return {
    window: { label: `${days}d`, since: since.toISOString(), until: until.toISOString() },
    totals: {
      usersTotal: 1240,
      newUsers: sum((point) => point.newUsers),
      onboardingCompleted: Math.round(sum((point) => point.newUsers) * 0.7),
      activeUsers: 312,
      promptQuestions: Math.round(sum((point) => point.questions) * 0.6),
      ragQuestions: Math.round(sum((point) => point.questions) * 0.3),
      councilQuestions: Math.round(sum((point) => point.questions) * 0.1),
      conversationsStarted: 420,
      conversationsByAgent: { aurelius: 210, machiavelli: 120, jung: 90 },
      trialsStarted: 48,
      paymentsCount: sum((point) => point.paymentsCount),
      paymentsStars: sum((point) => point.paymentsStars),
      subscriptionsCanceled: 3,
      limitHits: 27,
      generationFailures: 1,
      proActive: 86,
      trialActive: 12,
      proExpiringSoon: 4,
      proNotRenewing: 7,
    },
    series,
  };
}
