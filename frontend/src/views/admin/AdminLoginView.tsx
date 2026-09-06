import { useEffect, useRef, useState } from "react";

import { useAdminAuthConfig, useAdminLogin, useAdminOAuthStart } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import type { TelegramLoginPayload } from "../../lib/adminTypes";
import { adminButton, adminCard } from "../../lib/adminUi";
import { ApiError } from "../../lib/api";

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramLoginPayload) => void;
  }
}

const WIDGET_SRC = "https://telegram.org/js/telegram-widget.js?22";

/**
 * Browser sign-in through Telegram.
 *
 * Preferred path: OAuth 2.0 / OIDC - the backend builds the authorize URL, Telegram
 * sends the browser back to `/admin/callback`. The legacy iframe widget, which needs
 * `/setdomain` in @BotFather, is kept for servers without OAuth credentials.
 */
export function AdminLoginView() {
  const { t } = useAdminT();
  const config = useAdminAuthConfig();
  const login = useAdminLogin();
  const oauthStart = useAdminOAuthStart();
  const container = useRef<HTMLDivElement>(null);
  const [widgetReady, setWidgetReady] = useState(false);

  const botUsername = config.data?.botUsername ?? "";
  const oauthEnabled = config.data?.oauthEnabled ?? false;

  useEffect(() => {
    const host = container.current;
    if (!host || !botUsername || oauthEnabled) return;
    window.onTelegramAuth = (user) => login.mutate(user);
    const script = document.createElement("script");
    script.src = WIDGET_SRC;
    script.async = true;
    script.dataset.telegramLogin = botUsername;
    script.dataset.size = "large";
    script.dataset.onauth = "onTelegramAuth(user)";
    script.dataset.requestAccess = "write";
    script.onload = () => setWidgetReady(true);
    host.replaceChildren(script);
    return () => {
      host.replaceChildren();
      delete window.onTelegramAuth;
    };
    // `login` is a stable mutation object for the lifetime of the view.
    // oxlint-disable-next-line react-hooks/exhaustive-deps
  }, [botUsername, oauthEnabled]);

  const errorKey = (() => {
    const error = login.error ?? oauthStart.error;
    if (!error) return null;
    if (error instanceof ApiError && error.status === 403) return "admin_forbidden" as const;
    return "admin_login_failed" as const;
  })();

  return (
    <div className="bg-bg text-text grid min-h-screen place-items-center px-6">
      <div className={`${adminCard} w-full max-w-[420px] text-center`}>
        <span className="border-line mx-auto grid h-10 w-10 place-items-center rounded-full border font-serif text-[17px]">
          Æ
        </span>
        <h1 className="mt-4 text-[20px] font-[750] tracking-[-0.02em]">{t("admin_title")}</h1>
        <p className="text-muted mt-2 text-[13px] leading-relaxed">{t("admin_login_intro")}</p>

        <div className="mt-6 flex min-h-[48px] items-center justify-center">
          {config.isPending ? (
            <span className="text-soft text-[13px]">{t("admin_loading")}</span>
          ) : null}
          {config.data && !config.data.enabled ? (
            <span className="text-danger text-[13px]">{t("admin_login_disabled")}</span>
          ) : null}
          {config.data && config.data.enabled && !botUsername && !oauthEnabled ? (
            <span className="text-danger text-[13px]">{t("admin_login_no_bot")}</span>
          ) : null}
          {oauthEnabled ? (
            <button
              type="button"
              className={adminButton}
              disabled={oauthStart.isPending}
              onClick={() => oauthStart.mutate()}
            >
              {t("admin_login_oauth")}
            </button>
          ) : (
            <div ref={container} hidden={!botUsername} />
          )}
        </div>
        {!oauthEnabled && botUsername && !widgetReady ? (
          <p className="text-soft mt-2 text-[12px]">{t("admin_login_widget_loading")}</p>
        ) : null}
        {login.isPending || oauthStart.isPending ? (
          <p className="text-muted mt-3 text-[13px]">{t("admin_loading")}</p>
        ) : null}
        {errorKey ? <p className="text-danger mt-3 text-[13px]">{t(errorKey)}</p> : null}
        <p className="text-soft mt-6 text-[11px] leading-relaxed">{t("admin_login_hint")}</p>
      </div>
    </div>
  );
}
