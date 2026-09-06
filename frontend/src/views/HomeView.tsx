import { Link } from "@tanstack/react-router";
import { useRef, useState } from "react";

import { useActiveConversation, useGoal, useProfile } from "../hooks/queries";
import { useClosingConfirmation } from "../hooks/useClosingConfirmation";
import { AGENTS, agentMeta } from "../lib/agents";
import { useT } from "../lib/i18n-context";
import { LOCALES, type TranslationKey } from "../lib/i18n";
import { calculateLifeStats } from "../lib/life";
import { haptic } from "../lib/telegram";
import { scrollTrack } from "../lib/ui";

const AGENT_IMAGE: Record<string, string> = {
  aurelius: "marcus",
  machiavelli: "machiavelli",
  jung: "jung",
};

/** Example questions offered while there is no conversation to continue. */
const STARTERS: Record<string, TranslationKey[]> = {
  aurelius: ["starter_aurelius_1", "starter_aurelius_2", "starter_aurelius_3"],
  machiavelli: ["starter_machiavelli_1", "starter_machiavelli_2", "starter_machiavelli_3"],
  jung: ["starter_jung_1", "starter_jung_2", "starter_jung_3"],
  council: ["starter_council_1", "starter_council_2", "starter_council_3"],
};

const chipBase =
  "border-line bg-surface text-muted min-h-[38px] max-w-[240px] shrink-0 snap-start rounded-[8px] border px-3 py-2 text-left text-[12px] leading-[1.3]";
const tileBase =
  "border-line bg-surface grid min-h-[74px] content-start gap-1 rounded-[8px] border p-3 no-underline";

export function HomeView({
  activeAgentId,
  onSelectAgent,
  onStartDialog,
  onStartCouncil,
}: {
  activeAgentId: string;
  onSelectAgent: (agentId: string) => void;
  onStartDialog: (message?: string) => void;
  onStartCouncil: (message: string) => void;
}) {
  const { t, lang } = useT();
  const { data: profile } = useProfile();
  const { data: goal } = useGoal();
  const { data: conversation } = useActiveConversation();
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<"agent" | "council">("agent");
  const questionField = useRef<HTMLTextAreaElement>(null);
  useClosingConfirmation(question.trim().length > 0);
  const activeAgent = agentMeta(activeAgentId, lang);
  const starters = mode === "council" ? STARTERS.council : (STARTERS[activeAgentId] ?? []);
  const activeGoal = goal?.status === "active" ? goal : null;
  const lifeWeeks = profile?.birthDate ? calculateLifeStats(profile.birthDate).weeksLived : null;
  const streak = profile?.dailyCheckinStreak ?? 0;

  const submitQuestion = (event: React.FormEvent) => {
    event.preventDefault();
    const message = question.trim();
    if (!message) return;
    setQuestion("");
    haptic("impact");
    if (mode === "council") onStartCouncil(message);
    else onStartDialog(message);
  };

  const applyStarter = (text: string) => {
    setQuestion(text);
    haptic("selection");
    questionField.current?.focus();
  };

  return (
    <section className="animate-view-in block" aria-label={t("nav_home")}>
      {/* The heading names who answers; the council is a modifier of that, not a place to go. */}
      <section className="mt-2" aria-labelledby="ask-title">
        <div className="mb-2 flex items-center justify-between gap-3">
          <h2 id="ask-title" className="min-w-0 truncate font-serif text-[20px] leading-tight">
            {t("home_ask_addressee", {
              name: mode === "council" ? t("home_council") : activeAgent.name,
            })}
          </h2>
          <button
            type="button"
            role="switch"
            aria-checked={mode === "council"}
            aria-label={t("home_council")}
            onClick={() => {
              setMode(mode === "council" ? "agent" : "council");
              haptic("selection");
            }}
            className="flex min-h-11 shrink-0 items-center gap-2 text-[12px] font-[750]"
          >
            <span className={mode === "council" ? "text-text" : "text-muted"}>
              {t("home_council")}
            </span>
            <span
              aria-hidden="true"
              className={`relative block h-[26px] w-[44px] rounded-full transition-colors duration-200 motion-reduce:transition-none ${
                mode === "council" ? "bg-gold-strong" : "border-line bg-surface-strong border"
              }`}
            >
              <i
                className={`absolute top-[3px] block h-5 w-5 rounded-full transition-transform duration-200 motion-reduce:transition-none ${
                  mode === "council"
                    ? "translate-x-[21px] bg-[#1b1510]"
                    : "bg-soft translate-x-[3px]"
                }`}
              />
            </span>
          </button>
        </div>

        <div className="border-line bg-surface overflow-hidden rounded-[8px] border">
          <form className="grid grid-cols-[1fr_48px] items-end gap-2 p-2" onSubmit={submitQuestion}>
            <textarea
              ref={questionField}
              maxLength={320}
              rows={4}
              autoComplete="off"
              placeholder={t(
                mode === "council" ? "home_council_placeholder" : "home_ask_placeholder",
              )}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              className="text-text min-h-[108px] min-w-0 resize-none scroll-mb-[120px] border-0 bg-transparent px-2 py-[10px] text-[16px] leading-[1.4] outline-none placeholder:text-[#81786c]"
            />
            <button
              type="submit"
              title={t("home_send")}
              aria-label={t("home_send")}
              disabled={!question.trim()}
              className="bg-gold-strong grid h-12 w-12 place-items-center rounded-[8px] text-[24px] font-[800] text-[#1b1510] transition-opacity disabled:cursor-not-allowed disabled:opacity-35"
            >
              ↑
            </button>
          </form>
        </div>
      </section>

      {/* Examples only help before there is a thread to return to. */}
      {!conversation && starters.length > 0 && (
        <div className={`${scrollTrack} mt-2 snap-x snap-mandatory gap-2 pb-1`}>
          {starters.map((key) => (
            <button
              key={key}
              type="button"
              className={chipBase}
              onClick={() => applyStarter(t(key))}
            >
              {t(key)}
            </button>
          ))}
        </div>
      )}

      {conversation && (
        <section className="border-line bg-surface mt-3 grid gap-3 rounded-[8px] border p-4">
          <div>
            <span className="text-muted block text-[12px]">
              {t("home_continue_title", { name: conversation.agentName })}
            </span>
            <p className="text-text mt-1 line-clamp-2 text-[14px] leading-[1.4]">
              {conversation.lastMessage}
            </p>
          </div>
          <button
            type="button"
            onClick={() => onStartDialog()}
            className="border-line bg-surface-strong text-text min-h-[42px] rounded-[8px] border text-[13px] font-[750]"
          >
            {t("home_continue_action")}
          </button>
        </section>
      )}

      <section className="mt-6" aria-labelledby="agents-title">
        <div className="mb-3">
          <span className="text-muted block text-[12px]">{t("home_three_views")}</span>
          <h2 id="agents-title" className="mt-1 font-serif text-[22px] leading-tight">
            {t("home_agents")}
          </h2>
        </div>
        {/* Three across, full width. Custom advisors will add rows, so revisit the height then. */}
        <div className="grid grid-cols-3 gap-2">
          {Object.entries(AGENTS).map(([agentId, agent]) => {
            const isActive = activeAgentId === agentId;
            return (
              <button
                key={agentId}
                type="button"
                aria-pressed={isActive}
                className={`min-w-0 overflow-hidden rounded-[8px] border text-left transition-colors ${
                  isActive
                    ? "border-gold bg-[rgba(193,160,116,0.08)]"
                    : "border-line bg-[rgba(255,255,255,0.025)]"
                }`}
                onClick={() => {
                  onSelectAgent(agentId);
                  setMode("agent");
                  haptic("selection");
                }}
              >
                <div className="relative aspect-square overflow-hidden bg-[#111]">
                  <img
                    src={`/assets/${AGENT_IMAGE[agentId]}-card.webp`}
                    alt={agent.name[lang]}
                    width={360}
                    height={360}
                    loading="lazy"
                    decoding="async"
                    className={`block h-full w-full object-cover object-[center_18%] transition-[filter,opacity,transform] duration-500 ease-out motion-reduce:transition-none ${
                      isActive
                        ? "scale-[1.03] opacity-100 brightness-100 grayscale-0 saturate-[1.08]"
                        : "scale-100 opacity-75 brightness-[0.72] grayscale saturate-0"
                    }`}
                  />
                  {isActive && (
                    <span className="bg-gold-strong absolute top-2 right-2 grid h-5 w-5 place-items-center rounded-full text-[11px] font-bold text-[#1b1510]">
                      ✓
                    </span>
                  )}
                </div>
                {/* Cards are ~113px wide at 390px, so long names wrap instead of truncating. */}
                <div className="min-h-[64px] px-2 py-2">
                  <h3 className="text-text text-[13px] leading-[1.15] font-[750] break-words">
                    {agent.name[lang]}
                  </h3>
                  <small className="text-muted mt-1 line-clamp-2 block text-[11px] leading-[1.25]">
                    {agent.role[lang]}
                  </small>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="mt-4 grid grid-cols-2 gap-2">
        <Link to="/calendar" search={{ tab: "life" }} className={tileBase}>
          <span className="text-muted text-[12px]">{t("home_life_week")}</span>
          {lifeWeeks === null ? (
            <strong className="text-text text-[13px] leading-[1.25] font-[650]">
              {t("home_set_birthdate")}
            </strong>
          ) : (
            <strong className="text-text text-[20px] leading-none font-[750]">
              {lifeWeeks.toLocaleString(LOCALES[lang])}
            </strong>
          )}
          {streak > 0 && (
            <small className="text-muted text-[11px]">{t("home_streak", { count: streak })}</small>
          )}
        </Link>
        <Link to="/calendar" search={{ tab: "goal" }} className={tileBase}>
          <span className="text-muted text-[12px]">{t("home_goal_tile")}</span>
          <strong className="text-text line-clamp-2 text-[13px] leading-[1.3] font-[650]">
            {activeGoal ? activeGoal.text : t("home_no_goal")}
          </strong>
        </Link>
      </section>
    </section>
  );
}
