import { useState } from "react";

import { AGENTS } from "../lib/agents";
import { useT } from "../lib/i18n-context";
import { haptic } from "../lib/telegram";

/** Square 1:1 portrait file per agent id (self-framed — shown as-is). */
const AGENT_IMAGE: Record<string, string> = {
  aurelius: "marcus",
  machiavelli: "machiavelli",
  jung: "jung",
};

const HERO_OVERLAY =
  "linear-gradient(180deg, rgba(7,7,6,0.1), #070706 94%), radial-gradient(circle at 76% 34%, rgba(190,154,104,0.2), transparent 150px), linear-gradient(90deg, rgba(0,0,0,0.86) 0 43%, rgba(0,0,0,0.28) 72%, rgba(0,0,0,0.82) 100%)";

export function HomeView({
  activeAgentId,
  onSelectAgent,
  onStartDialog,
}: {
  activeAgentId: string;
  onSelectAgent: (agentId: string) => void;
  onStartDialog: (message?: string) => void;
}) {
  const { t, lang } = useT();
  const [question, setQuestion] = useState("");

  const submitQuestion = (event: React.FormEvent) => {
    event.preventDefault();
    const message = question.trim();
    if (!message) return;
    setQuestion("");
    onStartDialog(message);
  };

  return (
    <section className="block animate-view-in" aria-label={t("nav_home")}>
      <header className="relative mx-[-18px] min-h-[max(430px,50vh)] overflow-hidden border-b border-b-[rgba(255,255,255,0.06)] px-[18px] pt-[18px] pb-[28px] max-[390px]:mx-[-14px] max-[390px]:px-[14px]">
        {/* Portrait layer */}
        <div
          className="pointer-events-none absolute top-[22px] right-[-46px] z-0 h-[420px] w-[min(68vw,340px)] bg-contain bg-center bg-no-repeat opacity-[0.94]"
          style={{
            backgroundImage: "url('/assets/hero-sisyphus.webp')",
            filter: "contrast(1.08) brightness(0.76)",
            maskImage: "linear-gradient(90deg, transparent 0, #000 26%, #000 76%, transparent 100%)",
          }}
        />
        {/* Darkening overlay */}
        <div className="pointer-events-none absolute inset-0 z-[1]" style={{ background: HERO_OVERLAY }} />

        <div className="relative z-[2] mt-[150px] w-[min(78%,360px)] max-[390px]:w-[82%]">
          <h1 className="m-0 font-serif text-[clamp(38px,10.2vw,58px)] leading-none text-balance">
            {t("home_title")}
          </h1>
          <p className="mt-[14px] text-[14px] font-[650] text-[rgba(225,195,150,0.82)]">
            {t("home_subtitle")}
          </p>
        </div>

        <form
          className="relative z-[2] mt-[26px] grid h-16 grid-cols-[1fr_48px] gap-2 rounded-[23px] border border-[rgba(255,255,255,0.1)] bg-[rgba(33,31,29,0.82)] p-[7px] shadow-[0_24px_72px_rgba(0,0,0,0.48)] backdrop-blur-[24px]"
          onSubmit={submitQuestion}
        >
          <input
            type="text"
            maxLength={240}
            autoComplete="off"
            placeholder={t("home_ask_placeholder")}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            className="min-w-0 border-0 bg-transparent px-3 text-[17px] text-text outline-none placeholder:text-[#8c8479]"
          />
          <button
            type="submit"
            aria-label={t("home_ask_placeholder")}
            className="h-12 w-12 cursor-pointer rounded-full bg-[linear-gradient(135deg,#d9bb90,#8a6546)] text-[26px] font-extrabold text-[#201812]"
          >
            ↑
          </button>
        </form>
      </header>

      <section className="mt-6">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="m-0 font-serif text-[24px] leading-[1.1]">{t("home_agents")}</h2>
          <button
            type="button"
            onClick={() => onStartDialog()}
            className="cursor-pointer bg-transparent text-[14px] text-gold"
          >
            {t("home_advice")}
          </button>
        </div>
        <div className="grid grid-cols-3 gap-[10px] pb-2" aria-label={t("home_agents")}>
          {Object.entries(AGENTS).map(([agentId, agent]) => {
            const isActive = activeAgentId === agentId;
            return (
              <article
                key={agentId}
                className={`flex cursor-pointer flex-col overflow-hidden rounded-[18px] border ${
                  isActive
                    ? "border-[rgba(225,195,150,0.64)] shadow-[inset_0_1px_0_rgba(255,255,255,0.1),inset_0_0_34px_rgba(225,195,150,0.06),0_0_0_1px_rgba(225,195,150,0.18)]"
                    : "border-[rgba(255,255,255,0.08)]"
                }`}
                onClick={() => {
                  onSelectAgent(agentId);
                  haptic("selection");
                }}
              >
                <img
                  src={`/assets/${AGENT_IMAGE[agentId]}.webp`}
                  alt={agent.name[lang]}
                  className="block aspect-square w-full object-cover"
                />
                <div className="flex flex-col gap-[2px] px-[10px] pt-[9px] pb-[11px]">
                  <h3 className="font-serif text-[clamp(13px,3vw,17px)] leading-[1.08]">
                    {agent.name[lang]}
                  </h3>
                  <small className="block text-[clamp(9px,2.4vw,11px)] leading-[1.25] text-[rgba(225,195,150,0.82)]">
                    {agent.role[lang]}
                  </small>
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </section>
  );
}
