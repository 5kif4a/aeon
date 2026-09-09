/**
 * Admin panel API client. Two credentials are accepted by the backend: the Mini App
 * initData (inside Telegram) and a browser session token obtained through the
 * Telegram Login Widget. The token lives in localStorage; nothing else is cached.
 */

import { ApiError } from "./api";
import type {
  AdminAccess,
  AdminAccount,
  AdminAuthConfig,
  AdminConversation,
  AdminConversationDetail,
  AdminMe,
  AdminOAuthStart,
  AdminPage,
  AdminPayment,
  AdminPromptPreview,
  AdminPromptPreviewInput,
  AdminRole,
  AdminSetting,
  AdminSettingValue,
  AdminSession,
  AdminStats,
  AdminUser,
  AdminUserDetail,
  Broadcast,
  BroadcastDelivery,
  BroadcastInput,
  Segment,
  SegmentFilterSpec,
  SegmentFilters,
  SegmentInput,
  SegmentKind,
  SegmentPreview,
  TelegramLoginPayload,
} from "./adminTypes";
import { tg } from "./telegram";

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
const TOKEN_KEY = "aeon_admin_token";

/**
 * Dev convenience: `VITE_ADMIN_TOKEN` in `frontend/.env.local` is used when localStorage
 * holds no session, so `pnpm dev` talks to the panel API without a Telegram login. Mint one
 * with `uv run python -c "from app.core import admin_auth; print(admin_auth.issue_session_token(<id>)[0])"`.
 * `import.meta.env.DEV` is statically false in `pnpm build`, so this never ships.
 */
const DEV_TOKEN = import.meta.env.DEV ? (import.meta.env.VITE_ADMIN_TOKEN ?? "") : "";

export function getAdminToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY) || DEV_TOKEN || null;
  } catch {
    return DEV_TOKEN || null;
  }
}

export function setAdminToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // storage unavailable (private mode); the session simply does not persist
  }
}

/** True when some credential exists; the backend decides whether it is an admin one. */
export function hasAdminCredential(): boolean {
  return Boolean(getAdminToken() || tg?.initData);
}

function authorization(): string {
  const token = getAdminToken();
  if (token) return `admin ${token}`;
  return `tma ${tg?.initData ?? ""}`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: authorization(),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(detail, response.status);
  }
  return response.json();
}

function query(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

async function requestVoid(path: string, options: RequestInit = {}): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: authorization(),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(detail, response.status);
  }
}

export const adminApi = {
  getAuthConfig: () => request<AdminAuthConfig>("/api/admin/auth/config"),
  loginWithTelegram: (payload: TelegramLoginPayload) =>
    request<AdminSession>("/api/admin/auth/telegram", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  startOAuth: () => request<AdminOAuthStart>("/api/admin/auth/oauth/start", { method: "POST" }),
  completeOAuth: (code: string, state: string) =>
    request<AdminSession>("/api/admin/auth/oauth/callback", {
      method: "POST",
      body: JSON.stringify({ code, state }),
    }),
  getMe: () => request<AdminMe>("/api/admin/me"),

  getStats: (days: number) => request<AdminStats>(`/api/admin/stats${query({ days })}`),

  getUsers: (params: { q?: string; plan?: string; limit: number; offset: number }) =>
    request<AdminPage<AdminUser>>(`/api/admin/users${query(params)}`),
  getUser: (userId: number) => request<AdminUserDetail>(`/api/admin/users/${userId}`),
  grantPro: (userId: number, days: number) =>
    request<AdminUser>(`/api/admin/users/${userId}/grant-pro`, {
      method: "POST",
      body: JSON.stringify({ days }),
    }),
  refundPayment: (userId: number, paymentId: string) =>
    request<AdminPayment>(`/api/admin/users/${userId}/payments/${paymentId}/refund`, {
      method: "POST",
    }),

  getConversations: (params: {
    userId?: number;
    agentId?: string;
    status?: string;
    limit: number;
    offset: number;
  }) => request<AdminPage<AdminConversation>>(`/api/admin/conversations${query(params)}`),
  getConversation: (conversationId: string) =>
    request<AdminConversationDetail>(`/api/admin/conversations/${conversationId}`),

  getPayments: (params: { limit: number; offset: number }) =>
    request<AdminPage<AdminPayment>>(`/api/admin/payments${query(params)}`),

  getSettings: () => request<AdminSetting[]>("/api/admin/settings"),
  setSetting: (key: string, value: AdminSettingValue) =>
    request<AdminSetting>(`/api/admin/settings/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
  resetSetting: (key: string) =>
    request<AdminSetting>(`/api/admin/settings/${encodeURIComponent(key)}`, { method: "DELETE" }),
  previewPrompt: (input: AdminPromptPreviewInput) =>
    request<AdminPromptPreview>("/api/admin/settings/preview", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  getAccess: () => request<AdminAccess>("/api/admin/access"),
  createRole: (role: { id: string; title: string; description: string; permissions: string[] }) =>
    request<AdminRole>("/api/admin/access/roles", {
      method: "POST",
      body: JSON.stringify(role),
    }),
  updateRole: (
    roleId: string,
    patch: { title?: string; description?: string; permissions?: string[] },
  ) =>
    request<AdminRole>(`/api/admin/access/roles/${encodeURIComponent(roleId)}`, {
      method: "PUT",
      body: JSON.stringify(patch),
    }),
  deleteRole: (roleId: string) =>
    requestVoid(`/api/admin/access/roles/${encodeURIComponent(roleId)}`, { method: "DELETE" }),
  grantAdmin: (payload: { userId: number; roleId: string; note: string }) =>
    request<AdminAccount>("/api/admin/access/admins", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  revokeAdmin: (userId: number) =>
    requestVoid(`/api/admin/access/admins/${userId}`, { method: "DELETE" }),

  getSegmentFilters: () => request<SegmentFilterSpec[]>("/api/admin/segments/filters"),
  getSegments: () => request<Segment[]>("/api/admin/segments"),
  getSegment: (segmentId: string) => request<Segment>(`/api/admin/segments/${segmentId}`),
  createSegment: (input: SegmentInput) =>
    request<Segment>("/api/admin/segments", { method: "POST", body: JSON.stringify(input) }),
  updateSegment: (segmentId: string, input: SegmentInput) =>
    request<Segment>(`/api/admin/segments/${segmentId}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  deleteSegment: (segmentId: string) =>
    requestVoid(`/api/admin/segments/${segmentId}`, { method: "DELETE" }),
  previewSegment: (input: { kind: SegmentKind; filters: SegmentFilters; userIds: number[] }) =>
    request<SegmentPreview>("/api/admin/segments/preview", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  getBroadcasts: () => request<Broadcast[]>("/api/admin/broadcasts"),
  getBroadcast: (broadcastId: string) => request<Broadcast>(`/api/admin/broadcasts/${broadcastId}`),
  getBroadcastAudience: (broadcastId: string) =>
    request<SegmentPreview>(`/api/admin/broadcasts/${broadcastId}/audience`),
  createBroadcast: (input: BroadcastInput) =>
    request<Broadcast>("/api/admin/broadcasts", { method: "POST", body: JSON.stringify(input) }),
  updateBroadcast: (broadcastId: string, input: BroadcastInput) =>
    request<Broadcast>(`/api/admin/broadcasts/${broadcastId}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  deleteBroadcast: (broadcastId: string) =>
    requestVoid(`/api/admin/broadcasts/${broadcastId}`, { method: "DELETE" }),
  scheduleBroadcast: (broadcastId: string, scheduledAt: string | null) =>
    request<Broadcast>(`/api/admin/broadcasts/${broadcastId}/schedule`, {
      method: "POST",
      body: JSON.stringify({ scheduledAt }),
    }),
  cancelBroadcast: (broadcastId: string) =>
    request<Broadcast>(`/api/admin/broadcasts/${broadcastId}/cancel`, { method: "POST" }),
  testBroadcast: (broadcastId: string, language: string) =>
    requestVoid(`/api/admin/broadcasts/${broadcastId}/test`, {
      method: "POST",
      body: JSON.stringify({ language }),
    }),
  getBroadcastDeliveries: (broadcastId: string, status: string) =>
    request<BroadcastDelivery[]>(
      `/api/admin/broadcasts/${broadcastId}/deliveries${query({ status, limit: 200 })}`,
    ),
};
