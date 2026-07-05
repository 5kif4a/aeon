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
import { cardPanel, goldButton } from "../lib/ui";

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
      <header className="flex min-h-[118px] items-center justify-between pt-[26px]">
        <div>
          <span className="text-muted mb-[6px] block">{t("cal_memento")}</span>
          <h2 className="font-serif text-[24px] leading-[1.1]">{t("cal_title")}</h2>
        </div>
      </header>

      <form className={`${cardPanel} p-[14px]`} onSubmit={saveBirthDate}>
        <label htmlFor="birthDateInput" className="text-muted mb-[10px] block text-[14px]">
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
            className="border-line text-text h-[46px] min-w-0 rounded-[14px] border bg-[rgba(0,0,0,0.22)] px-3 outline-none"
          />
          <button type="submit" className={`${goldButton} h-[46px] px-[14px] font-[750]`}>
            {t("cal_calculate")}
          </button>
        </div>
      </form>

      <section className="mt-3 grid grid-cols-3 gap-[10px]">
        {[
          { value: (stats?.weeksLived ?? 0).toLocaleString(locale), label: t("cal_weeks_lived") },
          {
            value: (stats?.weeksLeft ?? TOTAL_LIFE_WEEKS).toLocaleString(locale),
            label: t("cal_weeks_left"),
          },
          { value: `${stats?.percent ?? 0}%`, label: t("cal_progress") },
        ].map((item) => (
          <article
            key={item.label}
            className="border-line grid min-h-[92px] place-items-center rounded-[18px] border bg-[rgba(255,255,255,0.045)] p-[12px_8px] text-center"
          >
            <strong className="text-gold-strong text-[25px] leading-none max-[390px]:text-[21px]">
              {item.value}
            </strong>
            <span className="text-muted text-[12px]">{item.label}</span>
          </article>
        ))}
      </section>

      <section className="mt-3 rounded-[18px] border border-[rgba(42,39,33,0.25)] bg-[radial-gradient(circle_at_18%_8%,rgba(255,255,255,0.42),transparent_18%),linear-gradient(180deg,#efe6d3_0%,#e6dcc5_100%)] p-[clamp(16px,4vw,28px)] text-[#25231f] shadow-[0_18px_42px_rgba(0,0,0,0.36),inset_0_0_0_1px_rgba(255,255,255,0.34)]">
        <div className="mb-[18px] text-center indent-[0.46em] font-serif text-[clamp(20px,5vw,34px)] leading-[1.1] tracking-[0.46em] text-[#24231f] max-[390px]:indent-[0.28em] max-[390px]:tracking-[0.28em]">
          {t("cal_memento_print")}
        </div>
        <div className="mb-[18px] grid grid-cols-[1fr_52px] items-start gap-3 border-t border-b border-t-[rgba(40,37,31,0.18)] border-b-[rgba(40,37,31,0.18)] py-3">
          <div>
            <h3 className="mb-[5px] font-serif text-[20px]">{mementoTitle(stats, t)}</h3>
            <p className="leading-[1.42] text-[#5c5548]">{mementoText(stats, t, locale)}</p>
          </div>
          <span className="grid h-[52px] w-[52px] place-items-center border border-[rgba(37,35,31,0.42)] text-[22px] font-[850] text-[#24231f]">
            {stats?.age ?? 0}
          </span>
        </div>
        <LifeGrid weeksLived={stats?.weeksLived ?? 0} />
        <div className="mt-4 flex flex-wrap gap-3 text-[12px] text-[#5d574c]">
          <span className="inline-flex items-center gap-[6px]">
            <i className="inline-block h-[10px] w-[10px] border border-[#2d2b27] bg-[#25231f]"></i>{" "}
            {t("legend_lived")}
          </span>
          <span className="inline-flex items-center gap-[6px]">
            <i className="inline-block h-[10px] w-[10px] border border-[#7d5c3e] bg-[#c5a16d]"></i>{" "}
            {t("legend_current")}
          </span>
          <span className="inline-flex items-center gap-[6px]">
            <i className="inline-block h-[10px] w-[10px] border border-[#2d2b27]"></i>{" "}
            {t("legend_ahead")}
          </span>
        </div>
      </section>

      <section className={`${cardPanel} mt-3 p-4`}>
        <h3 className="mb-2 font-serif text-[21px]">{t("goal_title")}</h3>
        <p className="leading-[1.45] text-[#d7cebf]">
          {activeGoal ? t("goal_active", { text: activeGoal.text }) : t("goal_none")}
        </p>
        <form className="mt-[14px] grid gap-[10px]" onSubmit={submitGoal}>
          <textarea
            maxLength={180}
            placeholder={t("goal_placeholder")}
            value={goalText}
            onChange={(event) => setGoalText(event.target.value)}
            className="border-line text-text min-h-[92px] w-full resize-y rounded-[16px] border bg-[rgba(0,0,0,0.22)] p-[14px] leading-[1.45] outline-none"
          ></textarea>
          <button
            type="submit"
            disabled={setGoal.isPending}
            className={`${goldButton} min-h-[44px] font-[750] disabled:opacity-60`}
          >
            {t("goal_set_button")}
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
            className="text-danger mt-[10px] min-h-[44px] w-full cursor-pointer rounded-[14px] bg-[rgba(213,114,103,0.12)] font-[750]"
          >
            {t("goal_close_button")}
          </button>
        )}
      </section>

      <section className={`${cardPanel} mt-3 p-4`}>
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h3 className="font-serif text-[21px]">{t("diary_title")}</h3>
            <p className="mt-1 text-[13px] leading-[1.45] text-[#d7cebf]">{t("diary_subtitle")}</p>
          </div>
          <span className="text-gold-strong rounded-[12px] bg-[rgba(225,195,150,0.11)] px-[10px] py-2 text-[13px] font-[750]">
            {entries.length}
          </span>
        </div>
        <div
          className="-mx-1 my-[2px] flex gap-2 overflow-x-auto px-1 pb-2"
          aria-label={t("diary_title")}
        >
          {DIARY_PROMPTS.map((item) => (
            <button
              key={item.labelKey}
              type="button"
              onClick={() => setDiaryText(t(item.promptKey))}
              className="min-h-[36px] shrink-0 cursor-pointer rounded-full border border-[rgba(225,195,150,0.14)] bg-[rgba(255,255,255,0.055)] px-3 text-[13px] text-[#e6d7bf]"
            >
              {t(item.labelKey)}
            </button>
          ))}
        </div>
        <form className="grid gap-[10px]" onSubmit={submitDiary}>
          <textarea
            maxLength={700}
            placeholder={t("diary_placeholder")}
            value={diaryText}
            onChange={(event) => setDiaryText(event.target.value)}
            className="border-line text-text min-h-[116px] w-full resize-y rounded-[18px] border bg-[rgba(0,0,0,0.24)] p-[14px] leading-[1.45] outline-none"
          ></textarea>
          <button
            type="submit"
            disabled={addEntry.isPending}
            className={`${goldButton} min-h-[44px] font-extrabold disabled:opacity-60`}
          >
            {t("diary_save_button")}
          </button>
        </form>
        <div className="mt-3 grid gap-[10px]">
          {entries.length === 0 ? (
            <article className="rounded-[18px] border border-[rgba(255,255,255,0.065)] bg-[rgba(255,255,255,0.045)] p-[13px]">
              <strong className="text-gold-strong mb-1 block">{t("diary_empty_title")}</strong>
              <p className="leading-[1.45] text-[#eee4d4]">{t("diary_empty_text")}</p>
            </article>
          ) : (
            entries.map((entry) => (
              <article
                key={entry.id}
                className="rounded-[18px] border border-[rgba(255,255,255,0.065)] bg-[rgba(255,255,255,0.045)] p-[13px]"
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="text-gold text-[12px]">
                    {formatDiaryDate(entry.created_at, locale)}
                  </span>
                  <button
                    type="button"
                    aria-label={t("diary_delete_aria")}
                    onClick={() => deleteEntry.mutate(entry.id)}
                    className="text-muted grid h-[30px] w-[30px] cursor-pointer place-items-center rounded-full bg-[rgba(255,255,255,0.06)]"
                  >
                    ×
                  </button>
                </div>
                <p className="leading-[1.45] text-[#eee4d4]">{entry.text}</p>
              </article>
            ))
          )}
        </div>
      </section>
    </section>
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
