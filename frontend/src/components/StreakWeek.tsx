import { useT } from "../lib/i18n-context";
import { LOCALES } from "../lib/i18n";
import type { CheckinDay } from "../lib/types";

/** "2026-09-19" → a Date at local midnight, so the weekday is not shifted by the UTC offset. */
function localDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

/** ISO date of a local Date, for the fallback week when the profile has not loaded. */
function isoDate(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** The current device-local week, Monday first, nothing checked: what the strip shows
 *  before the profile arrives (or in a plain browser with no Telegram session). */
function emptyWeek(): CheckinDay[] {
  const today = new Date();
  const sinceMonday = (today.getDay() + 6) % 7;
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - sinceMonday + index);
    return { date: isoDate(date), checked: false, today: index === sinceMonday };
  });
}

/** Two-letter weekday: "Mo" / "Пн". */
function weekdayLabel(date: Date, locale: string): string {
  const short = new Intl.DateTimeFormat(locale, { weekday: "short" }).format(date);
  const letters = short.replace(/\./g, "").slice(0, 2);
  return letters.charAt(0).toUpperCase() + letters.slice(1);
}

/**
 * One-line week strip under the brand row: the streak count, then the current week from
 * Monday as seven discs carrying the weekday letters — filled gold on the days the user wrote
 * to an advisor, ringed today, faint ahead. Writing is the check-in, so the habit is visible
 * before anything is asked of the user.
 */
export function StreakWeek({
  streak = 0,
  checkedInToday = false,
  week,
}: {
  streak?: number;
  checkedInToday?: boolean;
  week?: CheckinDay[];
}) {
  const { t, lang } = useT();
  const locale = LOCALES[lang];
  const days = week && week.length === 7 ? week : emptyWeek();
  const found = days.findIndex((day) => day.today);
  const todayIndex = found === -1 ? days.length - 1 : found;
  const note =
    streak === 0
      ? t("home_streak_start")
      : checkedInToday
        ? t("home_streak_today_done")
        : t("home_streak_today_pending");

  return (
    <section
      className="border-line bg-surface mt-3 flex items-center gap-3 rounded-[8px] border px-3 py-2"
      aria-label={`${t("home_streak_tile")}: ${streak}. ${note}`}
      title={note}
    >
      <strong className="text-gold-strong shrink-0 text-[18px] leading-none font-[750] [font-variant-numeric:tabular-nums]">
        ✦ {streak}
      </strong>

      <ol className="flex min-w-0 flex-1 justify-between" aria-label={t("home_streak_week_aria")}>
        {days.map((day, index) => {
          const ahead = index > todayIndex;
          const disc = day.checked
            ? "bg-gold-strong text-[#1b1510]"
            : day.today
              ? "border-gold text-text border border-dashed"
              : ahead
                ? "border-line text-soft border"
                : "bg-surface-strong text-soft";
          return (
            <li
              key={day.date}
              aria-label={day.checked ? t("home_streak_day_done") : undefined}
              className={`grid h-[26px] w-[26px] place-items-center rounded-full text-[10px] leading-none font-[750] ${disc}`}
            >
              {weekdayLabel(localDate(day.date), locale)}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
