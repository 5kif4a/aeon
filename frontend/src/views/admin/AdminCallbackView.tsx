import { getRouteApi, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef } from "react";

import { useAdminOAuthCallback } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { adminButton } from "../../lib/adminUi";
import { ApiError } from "../../lib/api";

const route = getRouteApi("/admin/callback");

/**
 * Where Telegram sends the browser back after an OIDC login. The code is traded for a
 * panel session once (StrictMode mounts twice, and the code is single-use), then the
 * URL is replaced so a reload does not retry a spent code.
 */
export function AdminCallbackView() {
  const { t } = useAdminT();
  const { code, state, error } = route.useSearch();
  const exchange = useAdminOAuthCallback();
  const navigate = useNavigate();
  const started = useRef(false);

  useEffect(() => {
    if (started.current || !code || !state) return;
    started.current = true;
    exchange.mutate(
      { code, state },
      { onSuccess: () => void navigate({ to: "/admin", search: { days: 30 }, replace: true }) },
    );
    // `exchange` and `navigate` are stable for the lifetime of the view.
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [code, state]);

  const failed = error || !code || !state || exchange.isError;
  const forbidden = exchange.error instanceof ApiError && exchange.error.status === 403;

  return (
    <div className="bg-bg text-text grid min-h-screen place-items-center px-6 text-center">
      <div>
        {failed ? (
          <>
            <p className="text-danger text-[15px]">
              {forbidden ? t("admin_forbidden") : t("admin_login_failed")}
            </p>
            <button
              type="button"
              className={`${adminButton} mt-4`}
              onClick={() => void navigate({ to: "/admin", search: { days: 30 }, replace: true })}
            >
              {t("admin_login_retry")}
            </button>
          </>
        ) : (
          <p className="text-muted text-[15px]">{t("admin_login_exchanging")}</p>
        )}
      </div>
    </div>
  );
}
