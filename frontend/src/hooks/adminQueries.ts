import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { adminApi, hasAdminCredential, setAdminToken } from "../lib/adminApi";
import type {
  AdminConversation,
  AdminMe,
  AdminPage,
  AdminPromptPreviewInput,
  AdminPayment,
  AdminSetting,
  AdminSettingValue,
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
  TelegramLoginPayload,
} from "../lib/adminTypes";
import { ApiError } from "../lib/api";

export const PAGE_SIZE = 50;

/**
 * `pnpm dev` opens the panel without a credential, the same way the Mini App screens do.
 *
 * Every read below goes through `devSafe`: with no session (and no `VITE_ADMIN_TOKEN`) the
 * request cannot succeed, so instead of a loader or an error the screen renders with empty
 * data - which is what you want while working on the layout. Set `VITE_ADMIN_TOKEN` to see
 * real rows. `import.meta.env.DEV` is statically false in `pnpm build`, so neither this
 * constant nor anything guarded by it survives a release build.
 */
export const DEV_UNLOCKED = import.meta.env.DEV;

export const DEV_ADMIN: AdminMe = {
  id: 0,
  name: "dev",
  // Empty: the panel language then follows the browser, as it does before sign-in.
  language: "",
  roleId: "owner",
  roleTitle: "Owner (dev)",
  permissions: ["*"],
  isOwner: true,
};

/**
 * Dev-only: a read that cannot be authorized resolves to empty data instead of failing.
 *
 * The fallback happens inside the query function, so react-query sees a plain success: the
 * result object is never rewritten (rewriting it re-reads every tracked field and hands the
 * component a new reference on each render, which spins into an endless render/refetch loop)
 * and the empty value is cached like real data. In a production build this returns the
 * fetcher untouched, so real failures still surface as errors.
 */
function devSafe<T, A extends unknown[] = []>(
  fetcher: (...args: A) => Promise<T>,
  empty: () => T | Promise<T>,
): (...args: A) => Promise<T> {
  if (!DEV_UNLOCKED) return fetcher;
  return async (...args: A) => {
    try {
      return await fetcher(...args);
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        return await empty();
      }
      throw error;
    }
  };
}

/**
 * Dev stand-ins live in their own module, imported only when a read actually fails, so the
 * fixtures land in a separate chunk instead of the release bundle.
 */
const fixtures = () => import("../lib/adminDevFixtures");

export function useAdminAuthConfig() {
  return useQuery({ queryKey: ["admin", "auth-config"], queryFn: adminApi.getAuthConfig });
}

/** The current admin, or a 401/403 error when the credential is missing or not allowlisted. */
export function useAdminMe() {
  return useQuery({
    queryKey: ["admin", "me"],
    queryFn: devSafe(adminApi.getMe, () => DEV_ADMIN),
    // In dev the request runs even without a credential: it answers 401 and `devSafe` turns
    // that into the synthetic owner, which is what opens the panel.
    enabled: DEV_UNLOCKED || hasAdminCredential(),
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
  return useQuery({
    queryKey: ["admin", "stats", days],
    queryFn: devSafe(
      () => adminApi.getStats(days),
      () => fixtures().then((m) => m.devStats(days)),
    ),
  });
}

export function useAdminUsers(params: { q: string; plan: string; page: number }) {
  return useQuery({
    queryKey: ["admin", "users", params],
    queryFn: devSafe<AdminPage<AdminUser>>(
      () =>
        adminApi.getUsers({
          q: params.q,
          plan: params.plan,
          limit: PAGE_SIZE,
          offset: (params.page - 1) * PAGE_SIZE,
        }),
      () => fixtures().then((m) => m.devUsers()),
    ),
    placeholderData: (previous) => previous,
  });
}

/**
 * Paged user search for the combobox: one page per scroll, `q` narrows it server-side.
 * `getNextPageParam` returns the next offset while the API still has rows to give.
 */
export function useAdminUsersInfinite(query: string) {
  return useInfiniteQuery({
    queryKey: ["admin", "users-search", query],
    initialPageParam: 0,
    queryFn: devSafe<AdminPage<AdminUser>, [{ pageParam: number }]>(
      ({ pageParam }) =>
        adminApi.getUsers({ q: query, plan: "", limit: PAGE_SIZE, offset: pageParam }),
      () => fixtures().then((m) => m.devUsers()),
    ),
    getNextPageParam: (last: AdminPage<AdminUser>, pages) => {
      const loaded = pages.reduce((total, page) => total + page.items.length, 0);
      return loaded < last.total ? loaded : undefined;
    },
  });
}

export function useAdminUser(userId: number) {
  return useQuery({
    queryKey: ["admin", "user", userId],
    queryFn: devSafe(
      () => adminApi.getUser(userId),
      () => fixtures().then((m) => m.devUserDetail(userId)),
    ),
    // `0` is what callers pass for "no user yet"; it must not become GET /users/0.
    enabled: Number.isFinite(userId) && userId > 0,
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

export function useRefundPayment(userId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (paymentId: string) => adminApi.refundPayment(userId, paymentId),
    onSuccess: () => {
      // The refund changes the payment row, the user's plan and the event log at once.
      queryClient.invalidateQueries({ queryKey: ["admin", "user", userId] });
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "payments"] });
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
    queryFn: devSafe<AdminPage<AdminConversation>>(
      () =>
        adminApi.getConversations({
          userId: params.userId,
          agentId: params.agentId,
          status: params.status,
          limit: PAGE_SIZE,
          offset: (params.page - 1) * PAGE_SIZE,
        }),
      () => fixtures().then((m) => m.devConversations()),
    ),
    placeholderData: (previous) => previous,
  });
}

export function useAdminConversation(conversationId: string) {
  return useQuery({
    queryKey: ["admin", "conversation", conversationId],
    queryFn: devSafe(
      () => adminApi.getConversation(conversationId),
      () => fixtures().then((m) => m.devConversationDetail(conversationId)),
    ),
  });
}

export function useAdminPayments(page: number) {
  return useQuery({
    queryKey: ["admin", "payments", page],
    queryFn: devSafe<AdminPage<AdminPayment>>(
      () => adminApi.getPayments({ limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
      () => fixtures().then((m) => m.devPayments()),
    ),
    placeholderData: (previous) => previous,
  });
}

export function useAdminSettings() {
  return useQuery({
    queryKey: ["admin", "settings"],
    queryFn: devSafe<AdminSetting[]>(adminApi.getSettings, () =>
      fixtures().then((m) => m.devSettings()),
    ),
  });
}

function replaceSetting(queryClient: ReturnType<typeof useQueryClient>, saved: AdminSetting) {
  queryClient.setQueryData(["admin", "settings"], (items: AdminSetting[] | undefined) =>
    items ? items.map((item) => (item.key === saved.key ? saved : item)) : items,
  );
}

/** Saves one override; the backend refreshes the running bot in-process. */
export function useSaveSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: AdminSettingValue }) =>
      adminApi.setSetting(key, value),
    onSuccess: (saved) => replaceSetting(queryClient, saved),
  });
}

/** Drops an override so the code default applies again. */
export function useResetSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => adminApi.resetSetting(key),
    onSuccess: (saved) => replaceSetting(queryClient, saved),
  });
}

/** One-off Gemini run with unsaved drafts; nothing is cached or stored. */
export function usePromptPreview() {
  return useMutation({
    mutationFn: (input: AdminPromptPreviewInput) => adminApi.previewPrompt(input),
  });
}

/** 401 = no valid credential (show login); 403 = valid Telegram user, not an admin. */
export function authFailure(error: unknown): "unauthenticated" | "forbidden" | null {
  if (!(error instanceof ApiError)) return null;
  if (error.status === 401) return "unauthenticated";
  if (error.status === 403) return "forbidden";
  return null;
}

/** True when the signed-in admin holds `permission` (owners hold everything). */
export function useCan(): (permission: string) => boolean {
  const me = useAdminMe();
  const permissions = me.data?.permissions ?? [];
  return (permission: string) => permissions.includes("*") || permissions.includes(permission);
}

// --- access control ---------------------------------------------------------------------

export function useAdminAccess() {
  return useQuery({
    queryKey: ["admin", "access"],
    queryFn: devSafe(adminApi.getAccess, () => fixtures().then((m) => m.devAccess())),
  });
}

/** Every access mutation reloads the whole matrix: roles and grants are read together. */
function useAccessMutation<TArgs>(mutationFn: (args: TArgs) => Promise<unknown>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "access"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "me"] });
    },
  });
}

export function useGrantAdmin() {
  return useAccessMutation((payload: { userId: number; roleId: string; note: string }) =>
    adminApi.grantAdmin(payload),
  );
}

export function useRevokeAdmin() {
  return useAccessMutation((userId: number) => adminApi.revokeAdmin(userId));
}

export function useCreateRole() {
  return useAccessMutation(
    (role: { id: string; title: string; description: string; permissions: string[] }) =>
      adminApi.createRole(role),
  );
}

export function useUpdateRole() {
  return useAccessMutation(
    (args: { roleId: string; permissions?: string[]; title?: string; description?: string }) =>
      adminApi.updateRole(args.roleId, {
        permissions: args.permissions,
        title: args.title,
        description: args.description,
      }),
  );
}

export function useDeleteRole() {
  return useAccessMutation((roleId: string) => adminApi.deleteRole(roleId));
}

// --- segments ---------------------------------------------------------------------------

export function useSegmentFilters() {
  return useQuery({
    queryKey: ["admin", "segment-filters"],
    queryFn: devSafe<SegmentFilterSpec[]>(adminApi.getSegmentFilters, () =>
      fixtures().then((m) => m.devSegmentFilters()),
    ),
    staleTime: Infinity, // the catalog only changes with a deploy
  });
}

export function useSegments() {
  return useQuery({
    queryKey: ["admin", "segments"],
    queryFn: devSafe<Segment[]>(adminApi.getSegments, () =>
      fixtures().then((m) => m.devSegments()),
    ),
  });
}

export function useSegment(segmentId: string | null) {
  return useQuery({
    queryKey: ["admin", "segment", segmentId],
    queryFn: devSafe(
      () => adminApi.getSegment(segmentId as string),
      () => fixtures().then((m) => m.devSegment(segmentId ?? "")),
    ),
    enabled: Boolean(segmentId),
  });
}

function useSegmentMutation<TArgs>(mutationFn: (args: TArgs) => Promise<unknown>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "segments"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "segment"] });
    },
  });
}

export function useSaveSegment() {
  return useSegmentMutation((args: { segmentId: string | null; input: SegmentInput }) =>
    args.segmentId
      ? adminApi.updateSegment(args.segmentId, args.input)
      : adminApi.createSegment(args.input),
  );
}

export function useDeleteSegment() {
  return useSegmentMutation((segmentId: string) => adminApi.deleteSegment(segmentId));
}

/** Counts an unsaved definition; a mutation because the editor asks for it explicitly. */
export function useSegmentPreview() {
  return useMutation({
    mutationFn: (input: { kind: SegmentKind; filters: SegmentFilters; userIds: number[] }) =>
      adminApi.previewSegment(input),
  });
}

// --- broadcasts -------------------------------------------------------------------------

export function useBroadcasts() {
  return useQuery({
    queryKey: ["admin", "broadcasts"],
    queryFn: devSafe<Broadcast[]>(adminApi.getBroadcasts, () =>
      fixtures().then((m) => m.devBroadcasts()),
    ),
    // While something is going out, the counters move on their own.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((row) => row.status === "sending") ? 5000 : false,
  });
}

export function useBroadcast(broadcastId: string | null) {
  return useQuery({
    queryKey: ["admin", "broadcast", broadcastId],
    queryFn: devSafe<Broadcast>(
      () => adminApi.getBroadcast(broadcastId as string),
      () => fixtures().then((m) => m.devBroadcast(broadcastId ?? "")),
    ),
    enabled: Boolean(broadcastId),
    refetchInterval: (query) => (query.state.data?.status === "sending" ? 5000 : false),
  });
}

export function useBroadcastAudience(broadcastId: string | null) {
  return useQuery({
    queryKey: ["admin", "broadcast-audience", broadcastId],
    queryFn: devSafe(
      () => adminApi.getBroadcastAudience(broadcastId as string),
      () => fixtures().then((m) => m.devSegmentPreview()),
    ),
    enabled: Boolean(broadcastId),
    retry: false,
  });
}

export function useBroadcastDeliveries(broadcastId: string | null, status: string) {
  return useQuery({
    queryKey: ["admin", "broadcast-deliveries", broadcastId, status],
    queryFn: devSafe<BroadcastDelivery[]>(
      () => adminApi.getBroadcastDeliveries(broadcastId as string, status),
      () => fixtures().then((m) => m.devDeliveries()),
    ),
    enabled: Boolean(broadcastId),
  });
}

function useBroadcastMutation<TArgs>(mutationFn: (args: TArgs) => Promise<unknown>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "broadcasts"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "broadcast"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "broadcast-audience"] });
    },
  });
}

export function useSaveBroadcast() {
  return useBroadcastMutation((args: { broadcastId: string | null; input: BroadcastInput }) =>
    args.broadcastId
      ? adminApi.updateBroadcast(args.broadcastId, args.input)
      : adminApi.createBroadcast(args.input),
  );
}

export function useDeleteBroadcast() {
  return useBroadcastMutation((broadcastId: string) => adminApi.deleteBroadcast(broadcastId));
}

export function useScheduleBroadcast() {
  return useBroadcastMutation((args: { broadcastId: string; scheduledAt: string | null }) =>
    adminApi.scheduleBroadcast(args.broadcastId, args.scheduledAt),
  );
}

export function useCancelBroadcast() {
  return useBroadcastMutation((broadcastId: string) => adminApi.cancelBroadcast(broadcastId));
}

export function useTestBroadcast() {
  return useMutation({
    mutationFn: (args: { broadcastId: string; language: string }) =>
      adminApi.testBroadcast(args.broadcastId, args.language),
  });
}
