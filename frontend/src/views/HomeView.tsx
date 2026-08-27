import { useState } from "react";

import { useBillingStatus } from "../hooks/queries";
import { AGENTS, agentMeta } from "../lib/agents";
import { useT } from "../lib/i18n-context";
import { haptic } from "../lib/telegram";

const AGENT_IMAGE: Record<string, string> = {
  aurelius: "marcus",
  machiavelli: "machiavelli",
  jung: "jung",
};

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
  const { data: billing } = useBillingStatus();
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<"agent" | "council">("agent");
  const activeAgent = agentMeta(activeAgentId, lang);
  const planLabel = billing
    ? t(billing.plan === "Pro" ? "plan_pro" : billing.plan === "Trial" ? "plan_trial" : "plan_free")
    : "";

  const submitQuestion = (event: React.FormEvent) => {
    event.preventDefault();
    const message = question.trim();
    if (!message) return;
    setQuestion("");
    haptic("impact");
    if (mode === "council") onStartCouncil(message);
    else onStartDialog(message);
  };

  return (
    <section className="animate-view-in block" aria-label={t("nav_home")}>
      <header className="border-line relative mx-[-18px] min-h-[328px] overflow-hidden border-b px-[18px] pt-[18px] max-[390px]:mx-[-14px] max-[390px]:px-[14px]">
        <div className="relative z-[2] flex items-center justify-between gap-3">
          <strong className="font-serif text-[18px] font-normal tracking-[0.18em]">AEON</strong>
          {billing && (
            <span className="border-line bg-surface/80 text-muted inline-flex min-h-8 items-center gap-2 rounded-[8px] border px-3 text-[12px] backdrop-blur-xl">
              <b className="text-gold-strong font-[750]">{planLabel}</b>
              <i className="bg-soft h-1 w-1 rounded-full" />
              {t("home_answers_left", { count: billing.dailyRemaining })}
            </span>
          )}
        </div>

        <img
          src="/assets/hero-sisyphus.webp"
          alt=""
          aria-hidden="true"
          className="pointer-events-none absolute top-[46px] right-[-30px] z-0 h-[276px] w-[252px] object-contain object-center opacity-75"
        />
        <div className="pointer-events-none absolute inset-0 z-[1] bg-[linear-gradient(90deg,#070706_0%,rgba(7,7,6,0.96)_42%,rgba(7,7,6,0.28)_78%,#070706_100%),linear-gradient(180deg,transparent_58%,#070706_100%)]" />

        <div className="relative z-[2] mt-[92px] max-w-[340px] pr-4">
          <span className="text-gold mb-3 block text-[12px] font-[750] tracking-[0.14em] uppercase">
            {t("home_eyebrow")}
          </span>
          <h1 className="m-0 max-w-[320px] font-serif text-[44px] leading-[0.98] max-[390px]:text-[38px]">
            {t("home_title")}
          </h1>
          <p className="text-muted mt-4 max-w-[280px] text-[14px] leading-[1.45]">
            {t("home_subtitle")}
          </p>
        </div>
      </header>

      <section className="mt-5" aria-labelledby="question-title">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <span className="text-muted block text-[12px]">{t("home_today_prompt")}</span>
            <h2 id="question-title" className="mt-1 font-serif text-[22px] leading-tight">
              {mode === "council"
                ? t("home_question_label_council")
                : t("home_question_label_agent", { name: activeAgent.name })}
            </h2>
          </div>
        </div>

        <div className="border-line bg-surface overflow-hidden rounded-[8px] border">
          <div className="border-line grid h-11 grid-cols-2 border-b p-1 text-[12px] font-[750]">
            <button
              type="button"
              className={
                mode === "agent"
                  ? "bg-surface-strong text-text rounded-[6px]"
                  : "text-muted rounded-[6px]"
              }
              onClick={() => setMode("agent")}
            >
              {t("home_single_agent")}
            </button>
            <button
              type="button"
              className={
                mode === "council"
                  ? "bg-surface-strong text-gold-strong rounded-[6px]"
                  : "text-muted rounded-[6px]"
              }
              onClick={() => setMode("council")}
            >
              {t("home_council")}
            </button>
          </div>

          <form className="grid grid-cols-[1fr_48px] items-end gap-2 p-2" onSubmit={submitQuestion}>
            <textarea
              maxLength={320}
              rows={2}
              autoComplete="off"
              placeholder={t(
                mode === "council" ? "home_council_placeholder" : "home_ask_placeholder",
              )}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              className="text-text min-h-[60px] min-w-0 resize-none border-0 bg-transparent px-2 py-[10px] text-[16px] leading-[1.35] outline-none placeholder:text-[#81786c]"
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

      <section className="mt-7" aria-labelledby="agents-title">
        <div className="mb-3">
          <span className="text-muted block text-[12px]">{t("home_three_views")}</span>
          <h2 id="agents-title" className="mt-1 font-serif text-[22px] leading-tight">
            {t("home_agents")}
          </h2>
        </div>
        <div className="grid grid-cols-3 gap-2" aria-label={t("home_agents")}>
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
                <div className="relative aspect-[4/3] overflow-hidden bg-[#111]">
                  <img
                    src={`/assets/${AGENT_IMAGE[agentId]}.webp`}
                    alt={agent.name[lang]}
                    className={`block h-full w-full object-cover object-top transition-[filter,opacity,transform] duration-500 ease-out motion-reduce:transition-none ${
                      isActive
                        ? "scale-[1.03] opacity-100 grayscale-0 saturate-[1.08] brightness-100"
                        : "scale-100 opacity-75 grayscale saturate-0 brightness-[0.72]"
                    }`}
                  />
                  {isActive && (
                    <span className="bg-gold-strong absolute top-2 right-2 grid h-5 w-5 place-items-center rounded-full text-[11px] font-bold text-[#1b1510]">
                      ✓
                    </span>
                  )}
                </div>
                <div className="min-h-[70px] px-2 py-[9px]">
                  <h3 className="text-text text-[13px] leading-[1.15] font-[750] break-words max-[340px]:text-[11px]">
                    {agent.name[lang]}
                  </h3>
                  <small className="text-muted mt-1 block text-[10px] leading-[1.25] max-[340px]:text-[9px]">
                    {agent.role[lang]}
                  </small>
                </div>
              </button>
            );
          })}
        </div>
      </section>
    </section>
  );
}
