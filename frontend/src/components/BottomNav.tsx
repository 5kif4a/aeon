import type { ViewName } from "../App";
import { useT } from "../lib/i18n-context";
import type { TranslationKey } from "../lib/i18n";
import { haptic } from "../lib/telegram";

const TABS: { id: ViewName; icon: string; labelKey: TranslationKey }[] = [
  { id: "home", icon: "⌂", labelKey: "nav_home" },
  { id: "calendar", icon: "◫", labelKey: "nav_diary" },
  { id: "profile", icon: "◎", labelKey: "nav_cabinet" },
];

export function BottomNav({
  view,
  onChange,
}: {
  view: ViewName;
  onChange: (view: ViewName) => void;
}) {
  const { t } = useT();
  return (
    <nav
      aria-label={t("nav_aria")}
      className="border-line fixed bottom-0 left-1/2 z-[11] grid min-h-[calc(68px+env(safe-area-inset-bottom,0px))] w-[min(100%,560px)] -translate-x-1/2 grid-cols-3 border-t bg-[rgba(13,13,12,0.96)] px-2 pb-[env(safe-area-inset-bottom,0px)] shadow-[0_-12px_32px_rgba(0,0,0,0.34)] backdrop-blur-[20px]"
    >
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`relative grid min-w-0 cursor-pointer place-items-center content-center gap-[3px] rounded-[8px] ${
            view === tab.id ? "text-gold-strong" : "text-muted"
          }`}
          onClick={() => {
            onChange(tab.id);
            haptic("selection");
          }}
        >
          {view === tab.id && (
            <i className="bg-gold-strong absolute top-0 h-[2px] w-8 rounded-b-full" />
          )}
          <span className="text-[22px] leading-none" aria-hidden="true">
            {tab.icon}
          </span>
          <small className="max-w-full truncate text-[11px] font-[650]">{t(tab.labelKey)}</small>
        </button>
      ))}
    </nav>
  );
}
