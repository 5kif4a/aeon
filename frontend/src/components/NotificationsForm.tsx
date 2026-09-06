import { useMemo } from "react";

import { useNotificationSettings, useUpdateNotificationSettings } from "../hooks/queries";
import { useT } from "../lib/i18n-context";
import { LOCALES } from "../lib/i18n";
import { TIMEZONES, deviceTimezone, timezoneLabel } from "../lib/options";
import { haptic } from "../lib/telegram";
import type { NotificationSettingsUpdate } from "../lib/types";
import { field, fieldLabel } from "../lib/ui";

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

function SelectChevron() {
  return (
    <svg
      className="text-muted pointer-events-none absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M6 8l4 4 4-4" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Toggle({
  label,
  hint,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  disabled: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className="border-line grid min-h-[54px] grid-cols-[1fr_auto] items-center gap-3 border-b px-1 py-2 text-left last:border-b-0 disabled:opacity-60"
    >
      <span>
        <strong className="text-text block text-[14px] font-[650]">{label}</strong>
        <small className="text-muted text-[12px] leading-[1.35]">{hint}</small>
      </span>
      <span
        aria-hidden="true"
        className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
          checked ? "bg-gold-strong" : "bg-surface-strong border-line border"
        }`}
      >
        <i
          className={`absolute top-1 h-4 w-4 rounded-full transition-all ${
            checked ? "left-6 bg-[#1e1711]" : "left-1 bg-[rgba(255,255,255,0.45)]"
          }`}
        />
      </span>
    </button>
  );
}

/**
 * Delivery window for the daily message and the weekly life review. The same columns
 * back the bot's /settings, so a change here shows up there and vice versa.
 */
export function NotificationsForm() {
  const { t, lang } = useT();
  const locale = LOCALES[lang];
  const settingsQuery = useNotificationSettings();
  const update = useUpdateNotificationSettings();
  const settings = settingsQuery.data;

  const device = deviceTimezone();
  const zone = settings?.reminderTimezone ?? "UTC";
  // The saved zone and the device zone are always offered, even outside the curated list.
  const zoneOptions = useMemo(() => {
    const options = [...TIMEZONES];
    for (const candidate of [device, zone]) {
      if (candidate && !options.includes(candidate)) options.unshift(candidate);
    }
    return options;
  }, [device, zone]);

  const save = (payload: NotificationSettingsUpdate) => {
    haptic("selection");
    update.mutate(payload);
  };

  if (settingsQuery.isPending) {
    return <p className="text-muted text-[13px]">{t("notifications_loading")}</p>;
  }
  if (!settings) {
    return <p className="text-danger text-[13px]">{t("notifications_load_failed")}</p>;
  }

  const localNow = new Intl.DateTimeFormat(locale, {
    timeZone: zone,
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
  const pending = update.isPending;

  return (
    <div className="grid gap-4">
      <p className="text-muted text-[13px] leading-[1.45]">{t("notifications_intro")}</p>

      {!settings.birthDateSet && (
        <p className="border-line bg-surface text-muted rounded-[8px] border p-3 text-[13px] leading-[1.45]">
          {t("notifications_needs_birthdate")}
        </p>
      )}

      <div className="border-line bg-surface rounded-[8px] border px-3">
        <Toggle
          label={t("notifications_daily")}
          hint={t("notifications_daily_hint")}
          checked={settings.dailyEnabled}
          disabled={pending}
          onChange={(next) => save({ dailyEnabled: next })}
        />
        <Toggle
          label={t("notifications_weekly")}
          hint={t("notifications_weekly_hint")}
          checked={settings.weeklyEnabled}
          disabled={pending}
          onChange={(next) => save({ weeklyEnabled: next })}
        />
      </div>

      <label className={fieldLabel}>
        {t("notifications_hour")}
        <div className="relative">
          <select
            value={settings.reminderHour}
            disabled={pending}
            onChange={(event) => save({ reminderHour: Number(event.target.value) })}
            className={`${field} cursor-pointer appearance-none pr-9`}
          >
            {HOURS.map((hour) => (
              <option key={hour} value={hour}>{`${String(hour).padStart(2, "0")}:00`}</option>
            ))}
          </select>
          <SelectChevron />
        </div>
      </label>

      <label className={fieldLabel}>
        {t("notifications_timezone")}
        <div className="relative">
          <select
            value={zone}
            disabled={pending}
            onChange={(event) => save({ reminderTimezone: event.target.value })}
            className={`${field} cursor-pointer appearance-none pr-9`}
          >
            {zoneOptions.map((option) => (
              <option key={option} value={option}>
                {timezoneLabel(option, locale)}
              </option>
            ))}
          </select>
          <SelectChevron />
        </div>
        <small className="text-muted text-[12px]">
          {t("notifications_local_now", { time: localNow })}
        </small>
      </label>

      {device && device !== zone && (
        <button
          type="button"
          disabled={pending}
          onClick={() => save({ reminderTimezone: device })}
          className="border-line bg-surface text-text min-h-11 rounded-[8px] border px-3 text-[13px] font-[650]"
        >
          {t("notifications_use_device", { zone: timezoneLabel(device, locale) })}
        </button>
      )}

      {update.isError && (
        <p className="text-danger text-[13px]">{t("notifications_save_failed")}</p>
      )}
    </div>
  );
}
