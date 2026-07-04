import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { useProfile, useUpdateProfile } from "../hooks/queries";
import { type Lang, normalizeLanguage, translate, type TFunc } from "./i18n";
import { detectLanguageCode } from "./telegram";

interface LanguageContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: TFunc;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { data: profile } = useProfile();
  const updateProfile = useUpdateProfile();
  const [lang, setLangState] = useState<Lang>(() => normalizeLanguage(detectLanguageCode()));

  // Adopt the persisted profile language once it loads (unless the user just switched).
  useEffect(() => {
    if (profile?.language) setLangState(normalizeLanguage(profile.language));
  }, [profile?.language]);

  // Keep the document language in sync for accessibility.
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback(
    (next: Lang) => {
      setLangState(next);
      updateProfile.mutate({ language: next });
    },
    [updateProfile],
  );

  const value = useMemo<LanguageContextValue>(
    () => ({ lang, setLang, t: (key, vars) => translate(lang, key, vars) }),
    [lang, setLang],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

// The provider and its hook are intentionally co-located; fast refresh is dev-only.
// oxlint-disable-next-line react/only-export-components
export function useT(): LanguageContextValue {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useT must be used within a LanguageProvider");
  return context;
}
