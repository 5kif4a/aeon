/** Admin panel API types mirroring the `admin` section of app/api/schemas.py. */

export interface AdminAuthConfig {
  botUsername: string;
  enabled: boolean;
  /** Telegram OAuth (OIDC) is configured on the server; the widget is the fallback. */
  oauthEnabled: boolean;
}

export interface AdminOAuthStart {
  authorizeUrl: string;
}

/** Payload returned by the Telegram Login Widget `data-onauth` callback. */
export interface TelegramLoginPayload {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
}

export interface AdminMe {
  id: number;
  name: string;
  language: string;
}

export interface AdminSession {
  token: string;
  expiresAt: string;
  admin: AdminMe;
}

export interface AdminStatsTotals {
  usersTotal: number;
  newUsers: number;
  onboardingCompleted: number;
  activeUsers: number;
  promptQuestions: number;
  ragQuestions: number;
  councilQuestions: number;
  conversationsStarted: number;
  conversationsByAgent: Record<string, number>;
  trialsStarted: number;
  paymentsCount: number;
  paymentsStars: number;
  subscriptionsCanceled: number;
  limitHits: number;
  generationFailures: number;
  proActive: number;
  trialActive: number;
  proExpiringSoon: number;
  proNotRenewing: number;
}

export interface AdminDailyPoint {
  day: string;
  newUsers: number;
  activeUsers: number;
  questions: number;
  paymentsStars: number;
  paymentsCount: number;
}

export interface AdminStats {
  window: { label: string; since: string; until: string };
  totals: AdminStatsTotals;
  series: AdminDailyPoint[];
}

export type PlanName = "Free" | "Trial" | "Pro";

export interface AdminUser {
  id: number;
  name: string;
  language: string;
  country: string;
  activity: string;
  mainGoal: string;
  plan: PlanName;
  birthDate: string | null;
  createdAt: string;
  lastActiveAt: string | null;
  questionsTotal: number;
  conversations: number;
  paymentsStars: number;
  proExpiresAt: string | null;
  trialExpiresAt: string | null;
  proAutoRenew: boolean;
}

export interface AdminPage<T> {
  items: T[];
  total: number;
}

export interface AdminPayment {
  id: string;
  userId: number;
  amount: number;
  currency: string;
  status: string;
  isRecurring: boolean;
  subscriptionExpiresAt: string | null;
  createdAt: string;
  userLanguage: string;
  userCountry: string;
}

export interface AdminConversation {
  id: string;
  userId: number;
  agentId: string;
  title: string;
  status: "active" | "closed";
  messageCount: number;
  createdAt: string;
  updatedAt: string;
  userLanguage: string;
  userPlan: string;
  preview: string;
}

export interface AdminEvent {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  createdAt: string;
}

export interface AdminUserDetail {
  user: AdminUser;
  usage30d: { prompt: number; rag: number; council: number };
  payments: AdminPayment[];
  conversations: AdminConversation[];
  events: AdminEvent[];
}

export interface AdminMessage {
  id: string;
  position: number;
  role: "user" | "agent";
  text: string;
  createdAt: string;
}

export interface AdminConversationDetail {
  conversation: AdminConversation;
  messages: AdminMessage[];
}
