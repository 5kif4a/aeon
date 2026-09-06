import { useEffect, useRef, useState } from "react";

import { useAdminAuthConfig, useAdminLogin } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import type { TelegramLoginPayload } from "../../lib/adminTypes";
import { adminCard } from "../../lib/adminUi";
import { ApiError } from "../../lib/api";

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramLoginPayload) => void;
  }
}

const WIDGET_SRC = "https://telegram.org/js/telegram-widget.js?22";

/**
 * Browser sign-in through the Telegram Login Widget. The widget calls
 * `window.onTelegramAuth` with a payload signed by Telegram; the backend verifies it
 * and checks the admin allowlist.
 */
export function AdminLoginView() {
  const { t } = useAdminT();
  const config = useAdminAuthConfig();
  const login = useAdminLogin();
  const container = useRef<HTMLDivElement>(null);
  const [widgetReady, setWidgetReady] = useState(false);

  const botUsername = config.data?.botUsername ?? "";

  useEffect(() => {
    const host = container.current;
    if (!host || !botUsername) return;
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
  }, [botUsername]);

  const errorKey = (() => {
    const error = login.error;
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
          {config.data && config.data.enabled && !botUsername ? (
            <span className="text-danger text-[13px]">{t("admin_login_no_bot")}</span>
          ) : null}
          <div ref={container} hidden={!botUsername} />
        </div>
        {botUsername && !widgetReady ? (
          <p className="text-soft mt-2 text-[12px]">{t("admin_login_widget_loading")}</p>
        ) : null}
        {login.isPending ? (
          <p className="text-muted mt-3 text-[13px]">{t("admin_loading")}</p>
        ) : null}
        {errorKey ? <p className="text-danger mt-3 text-[13px]">{t(errorKey)}</p> : null}
        <p className="text-soft mt-6 text-[11px] leading-relaxed">{t("admin_login_hint")}</p>
      </div>
    </div>
  );
}
