import { useEffect, useState } from "react";

import { LifeGrid } from "../components/LifeGrid";
import {
  useAddDiaryEntry,
  useCloseGoal,
  useDeleteDiaryEntry,
  useDiary,
  useGoal,
  useProfile,
  useSetGoal,
  useUpdateProfile,
} from "../hooks/queries";
import { useT } from "../lib/i18n-context";
import { LOCALES, type TFunc } from "../lib/i18n";
import {
  calculateLifeStats,
  formatDateOnly,
  formatDiaryDate,
  LIFE_EXPECTANCY_YEARS,
  todayKey,
  TOTAL_LIFE_WEEKS,
} from "../lib/life";
import { haptic } from "../lib/telegram";
import { cardPanel, goldButton, textareaField } from "../lib/ui";

type PracticeTab = "life" | "goal" | "diary";

const TABS = [
  { id: "life", icon: "◫", labelKey: "journal_tab_life" },
  { id: "goal", icon: "◎", labelKey: "journal_tab_goal" },
  { id: "diary", icon: "✎", labelKey: "journal_tab_diary" },
] as const;

const DIARY_PROMPTS = [
  { labelKey: "diary_prompt_important_label", promptKey: "diary_prompt_important" },
  { labelKey: "diary_prompt_postpone_label", promptKey: "diary_prompt_postpone" },
  { labelKey: "diary_prompt_oneact_label", promptKey: "diary_prompt_oneact" },
] as const;

export function CalendarView({ onMessage }: { onMessage: (text: string) => void }) {
  const { t, lang } = useT();
  const locale = LOCALES[lang];
  const { data: profile } = useProfile();
  const { data: goal } = useGoal();
  const { data: diary } = useDiary();
  const updateProfile = useUpdateProfile();
  const setGoal = useSetGoal();
  const closeGoal = useCloseGoal();
  const addEntry = useAddDiaryEntry();
  const deleteEntry = useDeleteDiaryEntry();

  const [tab, setTab] = useState<PracticeTab>("goal");
  const [birthDate, setBirthDate] = useState("");
  const [goalText, setGoalText] = useState("");
  const [diaryText, setDiaryText] = useState("");

  useEffect(() => {
    if (profile?.birthDate) setBirthDate(profile.birthDate);
  }, [profile?.birthDate]);

  const stats = profile?.birthDate ? calculateLifeStats(profile.birthDate) : null;
  const activeGoal = goal?.status === "active" ? goal : null;
  const entries = diary ?? [];

  const saveBirthDate = (event: React.FormEvent) => {
    event.preventDefault();
    if (!birthDate) return;
    updateProfile.mutate({ birthDate });
    haptic("impact");
  };

  const submitGoal = (event: React.FormEvent) => {
    event.preventDefault();
    const text = goalText.trim();
    if (!text) return;
    setGoal.mutate(text, {
      onSuccess: () => {
        setGoalText("");
        onMessage(t("goal_set_toast"));
      },
    });
  };

  const submitDiary = (event: React.FormEvent) => {
    event.preventDefault();
    const text = diaryText.trim();
    if (!text) return;
    addEntry.mutate(text, {
      onSuccess: () => {
        setDiaryText("");
        onMessage(t("diary_saved_toast"));
      },
    });
  };

  return (
    <section className="animate-view-in block" aria-label={t("nav_diary")}>
      <header className="pt-7 pb-5">
        <span className="text-gold block text-[12px] font-[750] tracking-[0.14em] uppercase">
          {t("journal_eyebrow")}
        </span>
        <h1 className="mt-2 max-w-[390px] font-serif text-[32px] leading-[1.05]">
          {t("journal_title")}
        </h1>
      </header>

      <div
        className="border-line bg-surface mb-6 grid h-[58px] grid-cols-3 rounded-[8px] border p-1"
        role="tablist"
        aria-label={t("journal_tabs_aria")}
      >
        {TABS.map((item) => {
          const selected = tab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => {
                setTab(item.id);
                haptic("selection");
              }}
              className={`grid min-w-0 grid-cols-[18px_auto] place-content-center items-center gap-1.5 rounded-[6px] text-[12px] font-[750] ${
                selected ? "bg-surface-strong text-gold-strong" : "text-muted"
              }`}
            >
              <span className="text-[17px] leading-none" aria-hidden="true">
                {item.icon}
              </span>
              <span className="truncate">{t(item.labelKey)}</span>
            </button>
          );
        })}
      </div>

      {tab === "life" && (
        <div role="tabpanel" className="animate-view-in">
          <div className="mb-4">
            <h2 className="font-serif text-[24px]">{t("cal_title")}</h2>
            <p className="text-muted mt-1 text-[14px] leading-[1.45]">{t("journal_life_intro")}</p>
          </div>

          <form className={`${cardPanel} p-[14px]`} onSubmit={saveBirthDate}>
            <label htmlFor="birthDateInput" className="text-muted mb-2 block text-[13px]">
              {t("cal_birthdate_label")}
            </label>
            <div className="grid grid-cols-[1fr_auto] gap-2 max-[390px]:grid-cols-1">
              <input
                id="birthDateInput"
                type="date"
                required
                max={todayKey()}
                value={birthDate}
                onChange={(event) => setBirthDate(event.target.value)}
                className="border-line text-text h-[46px] min-w-0 rounded-[8px] border bg-black/20 px-3 outline-none"
              />
              <button type="submit" className={`${goldButton} h-[46px] px-4 font-[750]`}>
                {t("cal_calculate")}
              </button>
            </div>
          </form>

          <section className="mt-3 grid grid-cols-3 gap-2">
            {[
              {
                value: (stats?.weeksLived ?? 0).toLocaleString(locale),
                label: t("cal_weeks_lived"),
              },
              {
                value: (stats?.weeksLeft ?? TOTAL_LIFE_WEEKS).toLocaleString(locale),
                label: t("cal_weeks_left"),
              },
              { value: `${stats?.percent ?? 0}%`, label: t("cal_progress") },
            ].map((item) => (
              <article
                key={item.label}
                className="border-line bg-surface grid min-h-[88px] min-w-0 content-center rounded-[8px] border p-2 text-center"
              >
                <strong className="text-gold-strong text-[22px] leading-none max-[390px]:text-[19px]">
                  {item.value}
                </strong>
                <span className="text-muted mt-2 text-[10px] leading-[1.2]">{item.label}</span>
              </article>
            ))}
          </section>

          <section className="mt-3 rounded-[8px] border border-[#d7cab0] bg-[#e8deca] p-[clamp(14px,4vw,24px)] text-[#25231f] shadow-[0_18px_42px_rgba(0,0,0,0.3)]">
            <div className="mb-4 text-center font-serif text-[24px] tracking-[0.16em] text-[#24231f]">
              {t("cal_memento_print")}
            </div>
            <div className="mb-4 grid grid-cols-[1fr_48px] items-start gap-3 border-y border-[#2d2a241f] py-3">
              <div>
                <h3 className="mb-1 font-serif text-[19px]">{mementoTitle(stats, t)}</h3>
                <p className="text-[13px] leading-[1.42] text-[#5c5548]">
                  {mementoText(stats, t, locale)}
                </p>
              </div>
              <span className="grid h-12 w-12 place-items-center border border-[#25231f6b] text-[20px] font-[850]">
                {stats?.age ?? 0}
              </span>
            </div>
            <LifeGrid weeksLived={stats?.weeksLived ?? 0} />
            <div className="mt-4 flex flex-wrap gap-3 text-[11px] text-[#5d574c]">
              <Legend color="bg-[#25231f]" label={t("legend_lived")} />
              <Legend color="border-[#7d5c3e] bg-[#c5a16d]" label={t("legend_current")} />
              <Legend color="bg-transparent" label={t("legend_ahead")} />
            </div>
          </section>
        </div>
      )}

      {tab === "goal" && (
        <div role="tabpanel" className="animate-view-in">
          <div className="mb-4">
            <h2 className="font-serif text-[24px]">{t("goal_title")}</h2>
            <p className="text-muted mt-1 text-[14px] leading-[1.45]">{t("journal_goal_intro")}</p>
          </div>

          <section
            className={`mb-3 rounded-[8px] border p-4 ${
              activeGoal
                ? "border-[rgba(166,196,138,0.35)] bg-[rgba(166,196,138,0.08)]"
                : "border-line bg-surface"
            }`}
          >
            <span className="text-muted text-[11px] font-[750] tracking-[0.12em] uppercase">
              {activeGoal ? t("goal_status_active") : t("goal_status_empty")}
            </span>
            <p className="mt-2 text-[17px] leading-[1.4] font-[650]">
              {activeGoal ? activeGoal.text : t("goal_none")}
            </p>
          </section>

          <form className={`${cardPanel} grid gap-3 p-4`} onSubmit={submitGoal}>
            <label htmlFor="goalInput" className="text-muted text-[13px]">
              {activeGoal ? t("goal_replace_label") : t("goal_new_label")}
            </label>
            <textarea
              id="goalInput"
              maxLength={180}
              rows={4}
              placeholder={t("goal_placeholder")}
              value={goalText}
              onChange={(event) => setGoalText(event.target.value)}
              className={`${textareaField} min-h-[104px]`}
            />
            <button
              type="submit"
              disabled={setGoal.isPending || !goalText.trim()}
              className={`${goldButton} min-h-[46px] font-[800] disabled:cursor-not-allowed disabled:opacity-40`}
            >
              {activeGoal ? t("goal_replace_button") : t("goal_set_button")}
            </button>
          </form>

          {activeGoal && (
            <button
              type="button"
              onClick={() =>
                closeGoal.mutate(undefined, {
                  onSuccess: () => onMessage(t("goal_closed_toast")),
                })
              }
              className="text-success mt-3 min-h-[46px] w-full rounded-[8px] border border-[rgba(166,196,138,0.24)] bg-[rgba(166,196,138,0.06)] font-[750]"
            >
              ✓ {t("goal_close_button")}
            </button>
          )}
        </div>
      )}

      {tab === "diary" && (
        <div role="tabpanel" className="animate-view-in">
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <h2 className="font-serif text-[24px]">{t("diary_title")}</h2>
              <p className="text-muted mt-1 text-[14px] leading-[1.45]">{t("diary_subtitle")}</p>
            </div>
            <span className="border-line bg-surface text-gold-strong rounded-[8px] border px-3 py-2 text-[12px] font-[750]">
              {entries.length}
            </span>
          </div>

          <div className="mb-3 flex gap-2 overflow-x-auto pb-1" aria-label={t("diary_title")}>
            {DIARY_PROMPTS.map((item) => (
              <button
                key={item.labelKey}
                type="button"
                onClick={() => setDiaryText(t(item.promptKey))}
                className="border-line bg-surface min-h-[38px] shrink-0 rounded-[8px] border px-3 text-[12px] text-[#e6d7bf]"
              >
                {t(item.labelKey)}
              </button>
            ))}
          </div>

          <form className={`${cardPanel} grid gap-3 p-4`} onSubmit={submitDiary}>
            <textarea
              maxLength={700}
              rows={5}
              placeholder={t("diary_placeholder")}
              value={diaryText}
              onChange={(event) => setDiaryText(event.target.value)}
              className={`${textareaField} min-h-[128px]`}
            />
            <button
              type="submit"
              disabled={addEntry.isPending || !diaryText.trim()}
              className={`${goldButton} min-h-[46px] font-[800] disabled:cursor-not-allowed disabled:opacity-40`}
            >
              {t("diary_save_button")}
            </button>
          </form>

          <section className="mt-5">
            <h3 className="text-muted mb-3 text-[13px] font-[750] tracking-[0.12em] uppercase">
              {t("diary_recent")}
            </h3>
            <div className="grid gap-2">
              {entries.length === 0 ? (
                <article className="border-line bg-surface rounded-[8px] border p-4">
                  <strong className="text-gold-strong mb-1 block">{t("diary_empty_title")}</strong>
                  <p className="text-muted text-[14px] leading-[1.45]">{t("diary_empty_text")}</p>
                </article>
              ) : (
                entries.map((entry) => (
                  <article
                    key={entry.id}
                    className="border-line bg-surface rounded-[8px] border p-4"
                  >
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <time className="text-gold text-[12px]">
                        {formatDiaryDate(entry.created_at, locale)}
                      </time>
                      <button
                        type="button"
                        title={t("diary_delete_aria")}
                        aria-label={t("diary_delete_aria")}
                        onClick={() => deleteEntry.mutate(entry.id)}
                        className="text-muted border-line grid h-8 w-8 place-items-center rounded-[8px] border bg-transparent text-[18px]"
                      >
                        ×
                      </button>
                    </div>
                    <p className="text-[15px] leading-[1.5] text-[#eee4d4]">{entry.text}</p>
                  </article>
                ))
              )}
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <i className={`inline-block h-2.5 w-2.5 border border-[#2d2b27] ${color}`} />
      {label}
    </span>
  );
}

function mementoTitle(stats: ReturnType<typeof calculateLifeStats> | null, t: TFunc): string {
  if (!stats) return t("memento_title_no_date");
  if (stats.isFutureDate) return t("memento_title_future");
  if (stats.weeksLeft <= 0) return t("memento_title_passed");
  return t("memento_title_weeks_left", { weeks: stats.weeksLeft.toLocaleString() });
}

function mementoText(
  stats: ReturnType<typeof calculateLifeStats> | null,
  t: TFunc,
  locale: string,
): string {
  if (!stats) {
    return t("memento_text_no_date", { total: TOTAL_LIFE_WEEKS, years: LIFE_EXPECTANCY_YEARS });
  }
  if (stats.isFutureDate) return t("memento_text_future");
  if (stats.weeksLeft <= 0) return t("memento_text_passed");
  return t("memento_text_ninetieth", { date: formatDateOnly(stats.ninetiethBirthday, locale) });
}
