/**
 * API types mirroring the backend Pydantic schemas (app/api/schemas.py).
 * Regenerate with `npm run generate:api` when the backend contract changes.
 */

export interface Profile {
  id: number;
  language: string;
  name: string;
  birthDate: string | null;
  age: number | null;
  country: string;
  location: string;
  activity: string;
  interests: string;
  mainGoal: string;
  currentProblem: string;
  plan: string;
  tokens: number;
  activeAgent: string | null;
  /** Lapse-corrected: zero once a day was skipped. */
  dailyCheckinStreak: number;
  checkedInToday: boolean;
  /** The last seven local days, oldest first, for the week strip on the home screen. */
  checkinWeek: CheckinDay[];
  isAdmin: boolean;
}

export interface CheckinDay {
  /** ISO date in the user's notification time zone. */
  date: string;
  checked: boolean;
  today: boolean;
}

export interface ProfileUpdate {
  name?: string;
  birthDate?: string;
  country?: string;
  location?: string;
  activity?: string;
  interests?: string;
  mainGoal?: string;
  currentProblem?: string;
  language?: string;
}

export type TimezoneSource = "default" | "language" | "device" | "manual";

export interface NotificationSettings {
  /** Morning slot: a thought to read. */
  dailyEnabled: boolean;
  reminderHour: number;
  /** Evening slot: a question to answer. */
  eveningEnabled: boolean;
  eveningHour: number;
  weeklyEnabled: boolean;
  /** News and offers sent from the admin panel; service announcements ignore it. */
  marketingEnabled: boolean;
  reminderTimezone: string;
  /** A guessed zone ("default"/"language") is replaced silently by the device zone. */
  timezoneSource: TimezoneSource;
  /** Only the weekly life review needs a birth date. */
  birthDateSet: boolean;
}

export type NotificationSettingsUpdate = Partial<
  Pick<
    NotificationSettings,
    | "dailyEnabled"
    | "eveningEnabled"
    | "weeklyEnabled"
    | "marketingEnabled"
    | "reminderHour"
    | "eveningHour"
    | "reminderTimezone"
  > & {
    /** What the device reports; applied only while the stored zone is a guess. */
    deviceTimezone: string;
  }
>;

export interface Goal {
  id: string;
  text: string;
  status: "active" | "closed";
  created_at: string;
  closed_at: string | null;
}

export interface DiaryEntry {
  id: string;
  text: string;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
}

export interface StartDialogResponse {
  ok: boolean;
  agentName: string;
  botUsername: string;
}

/** The dialogue still open in the bot chat, used to offer "continue" on the home screen. */
export interface ActiveConversation {
  agentId: string;
  agentName: string;
  title: string;
  lastMessage: string;
  messageCount: number;
  updatedAt: string;
}

export interface BillingStatus {
  plan: "Free" | "Trial" | "Pro";
  dailyMode: "prompt" | "rag";
  dailyUsed: number;
  dailyLimit: number;
  dailyRemaining: number;
  promptUsed: number;
  promptLimit: number;
  ragUsed: number;
  ragLimit: number;
  trialTotalUsed: number;
  trialTotalLimit: number;
  councilUsed: number;
  councilLimit: number;
  councilRemaining: number;
  canStartTrial: boolean;
  trialStartedAt: string | null;
  trialExpiresAt: string | null;
  proExpiresAt: string | null;
  proAutoRenew: boolean;
  proPriceStars: number;
  proYearPriceStars: number;
  proYearDiscountPercent: number;
}

export type BillingPeriod = "month" | "year";

export interface Checkout {
  invoiceLink: string;
  priceStars: number;
  period: BillingPeriod;
}
