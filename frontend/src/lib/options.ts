/**
 * Select options for the profile form.
 *
 * COUNTRIES mirrors the backend list in `backend/app/i18n.py` — the same set the
 * bot's /start onboarding uses — so the Mini App and the bot store identical
 * localized labels. Keep both lists in sync when the backend list changes.
 *
 * TIMEZONES mirrors TIMEZONE_OPTIONS in `backend/app/bot/ui.py`, so the notification
 * picker offers the same zones as the bot. The API accepts any IANA zone, so the
 * device's own zone is offered on top of this list rather than being forced into it.
 */

import type { Lang } from "./i18n";

export interface SelectOption {
  code: string;
  labels: Record<Lang, string>;
}

export const COUNTRIES: SelectOption[] = [
  { code: "kz", labels: { ru: "Казахстан", en: "Kazakhstan" } },
  { code: "ru", labels: { ru: "Россия", en: "Russia" } },
  { code: "us", labels: { ru: "США", en: "United States" } },
  { code: "tr", labels: { ru: "Турция", en: "Turkey" } },
  { code: "ae", labels: { ru: "ОАЭ", en: "UAE" } },
  { code: "de", labels: { ru: "Германия", en: "Germany" } },
  { code: "other", labels: { ru: "Другая страна", en: "Other" } },
];

export const TIMEZONES: string[] = [
  "UTC",
  "Europe/Lisbon",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Madrid",
  "Europe/Warsaw",
  "Europe/Kyiv",
  "Europe/Istanbul",
  "Europe/Moscow",
  "Asia/Tbilisi",
  "Asia/Yerevan",
  "Asia/Dubai",
  "Asia/Tashkent",
  "Asia/Almaty",
  "Asia/Bangkok",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
  "America/Sao_Paulo",
  "America/New_York",
  "America/Toronto",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
];

/** The zone the device reports, or "" when the browser will not say. */
export function deviceTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  } catch {
    return "";
  }
}

/** "Asia/Almaty" → "Almaty · UTC+5"; unknown zones keep their raw name. */
export function timezoneLabel(zone: string, locale: string): string {
  const city = zone === "UTC" ? "UTC" : (zone.split("/").pop() ?? zone).replace(/_/g, " ");
  const offset = timezoneOffsetLabel(zone, locale);
  return offset ? `${city} · ${offset}` : city;
}

function timezoneOffsetLabel(zone: string, locale: string): string {
  try {
    const parts = new Intl.DateTimeFormat(locale, {
      timeZone: zone,
      timeZoneName: "shortOffset",
    }).formatToParts(new Date());
    return parts.find((part) => part.type === "timeZoneName")?.value ?? "";
  } catch {
    return "";
  }
}

/**
 * Resolve a stored value to its option regardless of the language it was saved
 * in (the bot may have written "Казахстан" while the UI is now English), so the
 * matching option stays selected.
 */
export function matchOption(options: SelectOption[], value: string): SelectOption | undefined {
  const needle = value.trim().toLowerCase();
  if (!needle) return undefined;
  return options.find(
    (option) =>
      option.code === needle ||
      Object.values(option.labels).some((label) => label.toLowerCase() === needle),
  );
}
