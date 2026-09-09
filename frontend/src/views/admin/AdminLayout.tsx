import { Link, Outlet, useRouterState } from "@tanstack/react-router";

import { DEV_UNLOCKED, useAdminLogout, useAdminMe, authFailure } from "../../hooks/adminQueries";
import { AdminLanguageProvider, useAdminT } from "../../lib/admin-i18n-context";
import { hasAdminCredential } from "../../lib/adminApi";
import { adminButton } from "../../lib/adminUi";
import type { TFunc } from "../../lib/i18n";
import { tg } from "../../lib/telegram";
import { AdminLoginView } from "./AdminLoginView";

const DEFAULT_LIST_SEARCH = { page: 1 } as const;

/** Sidebar entries with the default search params each list route validates.
 *
 * `can` hides what the admin's role does not grant; the backend refuses those routes
 * anyway, so this only keeps the panel from showing dead ends.
 */
function NavLinks({
  pathname,
  t,
  can,
}: {
  pathname: string;
  t: TFunc;
  can: (permission: string) => boolean;
}) {
  const linkClass = (active: boolean) =>
    `rounded-[8px] px-3 py-2 text-[13px] font-[650] whitespace-nowrap transition ${
      active ? "bg-surface-strong text-text" : "text-muted hover:text-text"
    }`;
  return (
    <>
      <Link to="/admin" search={{ days: 30 }} className={linkClass(pathname === "/admin")}>
        {t("admin_nav_dashboard")}
      </Link>
      {can("users.view") ? (
        <Link
          to="/admin/users"
          search={{ q: "", plan: "", ...DEFAULT_LIST_SEARCH }}
          className={linkClass(pathname.startsWith("/admin/users"))}
        >
          {t("admin_nav_users")}
        </Link>
      ) : null}
      {can("conversations.view") ? (
        <Link
          to="/admin/conversations"
          search={{ userId: undefined, agentId: "", status: "", ...DEFAULT_LIST_SEARCH }}
          className={linkClass(pathname.startsWith("/admin/conversations"))}
        >
          {t("admin_nav_conversations")}
        </Link>
      ) : null}
      {can("payments.view") ? (
        <Link
          to="/admin/payments"
          search={DEFAULT_LIST_SEARCH}
          className={linkClass(pathname.startsWith("/admin/payments"))}
        >
          {t("admin_nav_payments")}
        </Link>
      ) : null}
      {can("segments.view") ? (
        <Link to="/admin/segments" className={linkClass(pathname.startsWith("/admin/segments"))}>
          {t("admin_nav_segments")}
        </Link>
      ) : null}
      {can("broadcasts.view") ? (
        <Link
          to="/admin/broadcasts"
          className={linkClass(pathname.startsWith("/admin/broadcasts"))}
        >
          {t("admin_nav_broadcasts")}
        </Link>
      ) : null}
      {can("admins.view") ? (
        <Link to="/admin/access" className={linkClass(pathname.startsWith("/admin/access"))}>
          {t("admin_nav_access")}
        </Link>
      ) : null}
      {can("settings.view") ? (
        <Link to="/admin/settings" className={linkClass(pathname.startsWith("/admin/settings"))}>
          {t("admin_nav_settings")}
        </Link>
      ) : null}
    </>
  );
}

/** Desktop shell for the product-owner panel: auth gate + sidebar. Not part of the Mini App shell. */
export function AdminLayout() {
  const me = useAdminMe();
  return (
    <AdminLanguageProvider language={me.data?.language}>
      <AdminGate />
    </AdminLanguageProvider>
  );
}

function AdminGate() {
  const { t } = useAdminT();
  const me = useAdminMe();
  const logout = useAdminLogout();
  const failure = authFailure(me.error);
  const pathname = useRouterState({ select: (state) => state.location.pathname });

  // The OAuth callback is the one admin path that runs before a credential exists.
  if (pathname === "/admin/callback") {
    return <Outlet />;
  }
  // `pnpm dev` skips the login and the "not an admin" screens: `useAdminMe` falls back to a
  // synthetic owner there, so the panel opens and every screen can be worked on.
  if (!DEV_UNLOCKED && (!hasAdminCredential() || failure === "unauthenticated")) {
    return <AdminLoginView />;
  }
  if (me.isPending) {
    return <Centered>{t("admin_loading")}</Centered>;
  }
  if (!DEV_UNLOCKED && failure === "forbidden") {
    return (
      <Centered>
        <p className="text-text text-[15px]">{t("admin_forbidden")}</p>
        {!tg?.initData ? (
          <button type="button" className={`${adminButton} mt-4`} onClick={logout}>
            {t("admin_logout")}
          </button>
        ) : null}
      </Centered>
    );
  }
  if (me.isError || !me.data) {
    return <Centered>{t("admin_error")}</Centered>;
  }
  return (
    <AdminFrame
      name={me.data.name}
      role={me.data.roleTitle}
      permissions={me.data.permissions}
      onLogout={logout}
    />
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-bg text-muted grid min-h-screen place-items-center px-6 text-center">
      <div>{children}</div>
    </div>
  );
}

function AdminFrame({
  name,
  role,
  permissions,
  onLogout,
}: {
  name: string;
  role: string;
  permissions: string[];
  onLogout: () => void;
}) {
  const { t } = useAdminT();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const can = (permission: string) => permissions.includes("*") || permissions.includes(permission);
  return (
    // On a wide screen the sidebar and the content scroll separately, so a list screen can
    // hand its leftover height to the table instead of growing the whole page.
    <div className="bg-bg text-text min-h-screen lg:grid lg:h-dvh lg:grid-cols-[220px_1fr] lg:overflow-hidden">
      <aside className="border-line bg-surface border-b px-4 py-4 lg:h-dvh lg:overflow-y-auto lg:border-r lg:border-b-0">
        <div className="mb-6 flex items-center gap-2 px-2">
          <span className="border-line grid h-8 w-8 place-items-center rounded-full border font-serif text-[15px]">
            Æ
          </span>
          <div>
            <p className="text-[14px] font-[750] tracking-[-0.02em]">aeon</p>
            <p className="text-soft text-[11px]">{t("admin_title")}</p>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto lg:flex-col" aria-label={t("admin_title")}>
          <NavLinks pathname={pathname} t={t} can={can} />
        </nav>
        <div className="border-line mt-6 hidden border-t pt-4 lg:block">
          <p className="text-muted truncate px-2 text-[12px]">{name}</p>
          <p className="text-soft truncate px-2 text-[11px]">{role}</p>
          {!tg?.initData ? (
            <button
              type="button"
              onClick={onLogout}
              className="text-soft hover:text-text mt-2 cursor-pointer px-2 text-[12px]"
            >
              {t("admin_logout")}
            </button>
          ) : null}
        </div>
      </aside>
      <main className="min-w-0 px-4 py-6 sm:px-8 lg:h-dvh lg:overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
