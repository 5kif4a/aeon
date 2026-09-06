import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { adminApi, hasAdminCredential, setAdminToken } from "../lib/adminApi";
import type { AdminUser, AdminUserDetail, TelegramLoginPayload } from "../lib/adminTypes";
import { ApiError } from "../lib/api";

export const PAGE_SIZE = 50;

export function useAdminAuthConfig() {
  return useQuery({ queryKey: ["admin", "auth-config"], queryFn: adminApi.getAuthConfig });
}

/** The current admin, or a 401/403 error when the credential is missing or not allowlisted. */
export function useAdminMe() {
  return useQuery({
    queryKey: ["admin", "me"],
    queryFn: adminApi.getMe,
    enabled: hasAdminCredential(),
    retry: false,
  });
}

export function useAdminLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TelegramLoginPayload) => adminApi.loginWithTelegram(payload),
    onSuccess: (session) => {
      setAdminToken(session.token);
      queryClient.setQueryData(["admin", "me"], session.admin);
    },
  });
}

/** Step one of the OIDC login: ask the backend for the authorize URL and leave the page. */
export function useAdminOAuthStart() {
  return useMutation({
    mutationFn: adminApi.startOAuth,
    onSuccess: ({ authorizeUrl }) => window.location.assign(authorizeUrl),
  });
}

/** Step two: trade the code from Telegram for a panel session. */
export function useAdminOAuthCallback() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ code, state }: { code: string; state: string }) =>
      adminApi.completeOAuth(code, state),
    onSuccess: (session) => {
      setAdminToken(session.token);
      queryClient.setQueryData(["admin", "me"], session.admin);
    },
  });
}

export function useAdminLogout() {
  const queryClient = useQueryClient();
  return () => {
    setAdminToken(null);
    queryClient.removeQueries({ queryKey: ["admin"] });
  };
}

export function useAdminStats(days: number) {
  return useQuery({ queryKey: ["admin", "stats", days], queryFn: () => adminApi.getStats(days) });
}

export function useAdminUsers(params: { q: string; plan: string; page: number }) {
  return useQuery({
    queryKey: ["admin", "users", params],
    queryFn: () =>
      adminApi.getUsers({
        q: params.q,
        plan: params.plan,
        limit: PAGE_SIZE,
        offset: (params.page - 1) * PAGE_SIZE,
      }),
    placeholderData: (previous) => previous,
  });
}

export function useAdminUser(userId: number) {
  return useQuery({
    queryKey: ["admin", "user", userId],
    queryFn: () => adminApi.getUser(userId),
    enabled: Number.isFinite(userId),
  });
}

export function useGrantPro(userId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (days: number) => adminApi.grantPro(userId, days),
    onSuccess: (user: AdminUser) => {
      queryClient.setQueryData(["admin", "user", userId], (detail: AdminUserDetail | undefined) =>
        detail ? { ...detail, user } : detail,
      );
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
}

export function useAdminConversations(params: {
  userId?: number;
  agentId: string;
  status: string;
  page: number;
}) {
  return useQuery({
    queryKey: ["admin", "conversations", params],
    queryFn: () =>
      adminApi.getConversations({
        userId: params.userId,
        agentId: params.agentId,
        status: params.status,
        limit: PAGE_SIZE,
        offset: (params.page - 1) * PAGE_SIZE,
      }),
    placeholderData: (previous) => previous,
  });
}

export function useAdminConversation(conversationId: string) {
  return useQuery({
    queryKey: ["admin", "conversation", conversationId],
    queryFn: () => adminApi.getConversation(conversationId),
  });
}

export function useAdminPayments(page: number) {
  return useQuery({
    queryKey: ["admin", "payments", page],
    queryFn: () => adminApi.getPayments({ limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
    placeholderData: (previous) => previous,
  });
}

/** 401 = no valid credential (show login); 403 = valid Telegram user, not an admin. */
export function authFailure(error: unknown): "unauthenticated" | "forbidden" | null {
  if (!(error instanceof ApiError)) return null;
  if (error.status === 401) return "unauthenticated";
  if (error.status === 403) return "forbidden";
  return null;
}
