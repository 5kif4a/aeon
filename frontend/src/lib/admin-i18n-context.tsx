import { createContext, useContext, useMemo } from "react";
import type { ReactNode } from "react";

import { type Lang, LOCALES, normalizeLanguage, translate, type TFunc } from "./i18n";

interface AdminLanguageValue {
  lang: Lang;
  locale: string;
  t: TFunc;
  formatDate: (value: string | null | undefined) => string;
  formatDateTime: (value: string | null | undefined) => string;
  formatNumber: (value: number) => string;
}

const AdminLanguageContext = createContext<AdminLanguageValue | null>(null);

/**
 * Admin screens do not load the Mini App profile; the language comes from the admin's
 * stored profile when known and from the browser otherwise.
 */
export function AdminLanguageProvider({
  language,
  children,
}: {
  language?: string;
  children: ReactNode;
}) {
  const value = useMemo<AdminLanguageValue>(() => {
    const lang = normalizeLanguage(language || navigator.language);
    const locale = LOCALES[lang];
    const date = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });
    const dateTime = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" });
    const number = new Intl.NumberFormat(locale);
    return {
      lang,
      locale,
      t: (key, vars) => translate(lang, key, vars),
      formatDate: (raw) => (raw ? date.format(new Date(raw)) : "—"),
      formatDateTime: (raw) => (raw ? dateTime.format(new Date(raw)) : "—"),
      formatNumber: (raw) => number.format(raw),
    };
  }, [language]);
  return <AdminLanguageContext.Provider value={value}>{children}</AdminLanguageContext.Provider>;
}

// oxlint-disable-next-line react/only-export-components
export function useAdminT(): AdminLanguageValue {
  const context = useContext(AdminLanguageContext);
  if (!context) throw new Error("useAdminT must be used within an AdminLanguageProvider");
  return context;
}
