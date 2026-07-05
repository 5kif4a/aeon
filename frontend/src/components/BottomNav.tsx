import type { ViewName } from "../App";
import { useT } from "../lib/i18n-context";
import type { TranslationKey } from "../lib/i18n";
import { haptic } from "../lib/telegram";

const TABS: { id: ViewName; icon: string; labelKey: TranslationKey }[] = [
  { id: "home", icon: "◌", labelKey: "nav_home" },
  { id: "calendar", icon: "◷", labelKey: "nav_diary" },
  { id: "profile", icon: "♜", labelKey: "nav_cabinet" },
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
      className="fixed bottom-[calc(10px+env(safe-area-inset-bottom,0px))] left-1/2 z-[11] grid min-h-[72px] w-[min(calc(100%-36px),486px)] -translate-x-1/2 grid-cols-3 gap-1 rounded-[30px] border border-[rgba(255,255,255,0.08)] bg-[rgba(27,26,24,0.92)] p-[7px] shadow-[0_18px_52px_rgba(0,0,0,0.54)] backdrop-blur-[26px]"
    >
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={`grid cursor-pointer place-items-center gap-[2px] rounded-[24px] ${
            view === tab.id ? "text-gold-strong bg-[rgba(255,255,255,0.08)]" : "text-muted"
          }`}
          onClick={() => {
            onChange(tab.id);
            haptic("selection");
          }}
        >
          <span className="text-[25px] leading-none">{tab.icon}</span>
          <small className="text-[12px]">{t(tab.labelKey)}</small>
        </button>
      ))}
    </nav>
  );
}
