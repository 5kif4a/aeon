/** Internationalization logic. Translation strings live in src/locales/*.json. */

import en from "../locales/en.json";
import ru from "../locales/ru.json";

export const SUPPORTED_LANGUAGES = ["en", "ru"] as const;
export type Lang = (typeof SUPPORTED_LANGUAGES)[number];
export const DEFAULT_LANGUAGE: Lang = "en";

export const LANGUAGE_NAMES: Record<Lang, string> = {
  en: "English",
  ru: "Русский",
};

/** Intl locale used for date/number formatting per language. */
export const LOCALES: Record<Lang, string> = {
  en: "en-US",
  ru: "ru-RU",
};

/** Keys come from the English catalog; ru.json must provide the same set. */
export type TranslationKey = keyof typeof en;

const MESSAGES: Record<Lang, Record<TranslationKey, string>> = {
  en,
  ru,
};

export type Vars = Record<string, string | number>;
export type TFunc = (key: TranslationKey, vars?: Vars) => string;

export function normalizeLanguage(code: string | null | undefined): Lang {
  if (!code) return DEFAULT_LANGUAGE;
  const base = code.trim().toLowerCase().replace("_", "-").split("-")[0];
  return (SUPPORTED_LANGUAGES as readonly string[]).includes(base)
    ? (base as Lang)
    : DEFAULT_LANGUAGE;
}

export function translate(lang: Lang, key: TranslationKey, vars?: Vars): string {
  const template = MESSAGES[lang][key] ?? MESSAGES[DEFAULT_LANGUAGE][key] ?? key;
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_match, name: string) =>
    name in vars ? String(vars[name]) : `{${name}}`,
  );
}
