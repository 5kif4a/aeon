/* oxlint-disable react/only-export-components -- route components live next to the router */
import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
} from "@tanstack/react-router";

import { AppShell, useAppShell } from "./App";
import { resolveEntryHref } from "./lib/deeplinks";
import { LanguageProvider } from "./lib/i18n-context";
import { pickPracticeTab, pickProfileSheet } from "./lib/views";
import { pickOptionalId, pickPage, pickStatsRange, pickString } from "./lib/adminFormat";
import { AdminConversationDetailView } from "./views/admin/AdminConversationDetailView";
import { AdminConversationsView } from "./views/admin/AdminConversationsView";
import { AdminDashboardView } from "./views/admin/AdminDashboardView";
import { AdminLayout } from "./views/admin/AdminLayout";
import { AdminPaymentsView } from "./views/admin/AdminPaymentsView";
import { AdminUserDetailView } from "./views/admin/AdminUserDetailView";
import { AdminUsersView } from "./views/admin/AdminUsersView";
import { CalendarView } from "./views/CalendarView";
import { HomeView } from "./views/HomeView";
import { LandingView } from "./views/LandingView";
import { ProfileView } from "./views/ProfileView";

const rootRoute = createRootRoute({ component: Outlet });

/** Marketing page. */
const landingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/landing",
  component: LandingView,
});

/**
 * Pathless layout for the Mini App. It renders even without Telegram initData so
 * every screen can be opened in a plain browser during development; outside
 * Telegram the API simply answers 401 and the views show their empty states.
 */
const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  component: () => (
    <LanguageProvider>
      <AppShell />
    </LanguageProvider>
  ),
});

function HomeRoute() {
  const shell = useAppShell();
  return (
    <HomeView
      activeAgentId={shell.activeAgentId}
      onSelectAgent={shell.selectAgent}
      onStartDialog={shell.beginDialog}
      onStartCouncil={shell.beginCouncil}
    />
  );
}

function CalendarRoute() {
  const shell = useAppShell();
  return <CalendarView onMessage={shell.showMessage} onStartDialog={shell.beginDialog} />;
}

const homeRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/",
  component: HomeRoute,
});

const calendarRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/calendar",
  validateSearch: (search: Record<string, unknown>) => ({ tab: pickPracticeTab(search.tab) }),
  component: CalendarRoute,
});

const profileRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/profile",
  validateSearch: (search: Record<string, unknown>) => ({
    sheet: pickProfileSheet(search.sheet),
  }),
  component: ProfileView,
});

/**
 * Product-owner panel. Separate layout (no Mini App shell); access is decided by the
 * backend allowlist, the layout only chooses between the login screen and the frame.
 */
const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin",
  component: AdminLayout,
});

const adminDashboardRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "/",
  validateSearch: (search: Record<string, unknown>) => ({ days: pickStatsRange(search.days) }),
  component: AdminDashboardView,
});

const adminUsersRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "/users",
  validateSearch: (search: Record<string, unknown>) => ({
    q: pickString(search.q),
    plan: pickString(search.plan),
    page: pickPage(search.page),
  }),
  component: AdminUsersView,
});

const adminUserRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "/users/$userId",
  component: AdminUserDetailView,
});

const adminConversationsRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "/conversations",
  validateSearch: (search: Record<string, unknown>) => ({
    userId: pickOptionalId(search.userId),
    agentId: pickString(search.agentId),
    status: pickString(search.status),
    page: pickPage(search.page),
  }),
  component: AdminConversationsView,
});

const adminConversationRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "/conversations/$conversationId",
  component: AdminConversationDetailView,
});

const adminPaymentsRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "/payments",
  validateSearch: (search: Record<string, unknown>) => ({ page: pickPage(search.page) }),
  component: AdminPaymentsView,
});

/** Unknown paths fall back to home so a mistyped deep link never shows a blank page. */
const notFoundRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "$",
  beforeLoad: () => {
    throw redirect({ to: "/", replace: true });
  },
});

const routeTree = rootRoute.addChildren([
  landingRoute,
  appRoute.addChildren([homeRoute, calendarRoute, profileRoute]),
  adminRoute.addChildren([
    adminDashboardRoute,
    adminUsersRoute,
    adminUserRoute,
    adminConversationsRoute,
    adminConversationRoute,
    adminPaymentsRoute,
  ]),
  notFoundRoute,
]);

// Map Telegram start_param / legacy ?view= links onto a route before the router
// snapshots the URL, so deep links from t.me and old bot messages land correctly.
const entryHref = resolveEntryHref();
if (entryHref) window.history.replaceState(null, "", entryHref);

export const router = createRouter({ routeTree, defaultPreload: false });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
