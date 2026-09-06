/**
 * Admin panel API client. Two credentials are accepted by the backend: the Mini App
 * initData (inside Telegram) and a browser session token obtained through the
 * Telegram Login Widget. The token lives in localStorage; nothing else is cached.
 */

import { ApiError } from "./api";
import type {
  AdminAuthConfig,
  AdminConversation,
  AdminConversationDetail,
  AdminMe,
  AdminOAuthStart,
  AdminPage,
  AdminPayment,
  AdminSession,
  AdminStats,
  AdminUser,
  AdminUserDetail,
  TelegramLoginPayload,
} from "./adminTypes";
import { tg } from "./telegram";

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
const TOKEN_KEY = "aeon_admin_token";

export function getAdminToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
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
};
