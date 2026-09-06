/**
 * Deep links into the Mini App.
 *
 * Telegram offers two ways in:
 *  - `web_app` buttons and the chat menu button accept any URL, so the bot links
 *    straight to a path such as `/calendar?tab=goal`;
 *  - `https://t.me/<bot>/<app>?startapp=<param>` links cannot carry a path; the
 *    value arrives as `initDataUnsafe.start_param` and is mapped to a route here.
 *
 * Older bot messages still carry `?view=calendar` links; they are mapped too.
 */

import { tg } from "./telegram";

const START_PARAM_ROUTES: Record<string, string> = {
  home: "/",
  calendar: "/calendar",
  calendar_life: "/calendar?tab=life",
  calendar_goal: "/calendar?tab=goal",
  calendar_diary: "/calendar?tab=diary",
  profile: "/profile",
  profile_about: "/profile?sheet=about",
  profile_pro: "/profile?sheet=pro",
  profile_notifications: "/profile?sheet=notifications",
};

/** The route to start on, or null to keep the current URL. */
export function resolveEntryHref(location: Location = window.location): string | null {
  const url = new URL(location.href);
  if (url.pathname !== "/" && url.pathname !== "") return null;

  const startParam = tg?.initDataUnsafe?.start_param ?? url.searchParams.get("tgWebAppStartParam");
  const legacyView = url.searchParams.get("view");
  const key = startParam || legacyView;
  if (!key) return null;
  return START_PARAM_ROUTES[key] ?? null;
}
