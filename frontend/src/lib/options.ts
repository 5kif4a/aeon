/**
 * Select options for the profile form.
 *
 * COUNTRIES mirrors the backend list in `backend/app/i18n.py` — the same set the
 * bot's /start onboarding uses — so the Mini App and the bot store identical
 * localized labels. Keep both lists in sync when the backend list changes.
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

export const GENDERS: SelectOption[] = [
  { code: "male", labels: { ru: "Мужской", en: "Male" } },
  { code: "female", labels: { ru: "Женский", en: "Female" } },
  { code: "other", labels: { ru: "Другой", en: "Other" } },
];

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
