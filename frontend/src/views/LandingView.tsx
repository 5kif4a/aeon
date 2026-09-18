import { getRouteApi } from "@tanstack/react-router";
import { useEffect } from "react";

import { agentMeta } from "../lib/agents";
import { BIOGRAPHIES } from "../lib/biographies";
import { translate, type TFunc } from "../lib/i18n";

const route = getRouteApi("/landing");
const BOT_URL = "https://t.me/AI_Stoic_bot";
const t: TFunc = (key, vars) => translate("en", key, vars);
const mentors = [
  { id: "aurelius", image: "/assets/marcus.webp" },
  { id: "machiavelli", image: "/assets/machiavelli.webp" },
  { id: "jung", image: "/assets/jung.webp" },
] as const;
const mentorName = (id: string) =>
  id === "machiavelli" ? t("landing_machiavelli") : agentMeta(id, "en").name;

function TelegramIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" className="h-5 w-5 shrink-0">
      <path d="M21.4 3.6 18.2 20c-.2 1.1-.9 1.4-1.8.9l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.4-5 9.1-8.2c.4-.4-.1-.6-.6-.3L5.8 13.7 1 12.2c-1-.3-1-1 .2-1.5L20 3.4c.9-.3 1.6.2 1.4.2Z" />
    </svg>
  );
}

export function LandingView() {
  const { mentor: selectedId } = route.useSearch();
  const navigate = route.useNavigate();
  const selected = agentMeta(selectedId, "en");
  const biography = BIOGRAPHIES[selectedId].en;

  useEffect(() => {
    const previousLanguage = document.documentElement.lang;
    const previousTitle = document.title;
    document.documentElement.lang = "en";
    document.title = t("landing_page_title");
    return () => {
      document.documentElement.lang = previousLanguage;
      document.title = previousTitle;
    };
  }, []);

  return (
    <div className="landing relative isolate flex min-h-svh flex-col overflow-x-clip bg-[#050505] bg-[radial-gradient(ellipse_at_8%_20%,#d8bd911a,transparent_50%),radial-gradient(ellipse_at_95%_85%,#9b73481f,transparent_45%)] text-[#f4f1eb] lg:h-svh">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(#d8bd9107_1px,transparent_1px),linear-gradient(90deg,#d8bd9107_1px,transparent_1px)] mask-[radial-gradient(ellipse_at_center,transparent_20%,black_100%)] bg-size-[72px_72px]"
      />
      <div className="flex shrink-0 items-center border-b border-white/8 text-[#d8bd91]">
        <div className="landing-marquee min-w-0 flex-1 overflow-hidden py-3">
          <div className="landing-marquee-track flex w-max">
            {[0, 1].map((copy) => (
              <div
                key={copy}
                aria-hidden={copy === 1}
                className="flex min-w-[100vw] shrink-0 items-center justify-around"
              >
                {(
                  [
                    "landing_marquee_unlock",
                    "landing_marquee_future",
                    "landing_marquee_change",
                    "landing_marquee_mind",
                  ] as const
                ).map((phrase) => (
                  <span
                    key={phrase}
                    className="flex shrink-0 items-center gap-10 pr-10 text-[11px] tracking-[0.14em] uppercase sm:text-xs"
                  >
                    {t(phrase)}
                    <span aria-hidden="true" className="text-white/30">
                      ✳
                    </span>
                  </span>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      <main className="mx-auto flex min-h-0 w-full max-w-[1480px] flex-1 items-center px-4 py-8 sm:px-8 lg:px-12 lg:py-3">
        <section
          aria-labelledby="landing-heading"
          className="grid w-full items-center gap-5 lg:grid-cols-[.8fr_1.65fr] lg:gap-8"
        >
          <div className="rounded-[28px] border border-white/8 bg-white/[0.025] px-6 py-8 sm:px-8 lg:py-7">
            <p className="text-[64px] leading-none font-semibold tracking-[-0.075em] lg:text-[clamp(48px,9vh,80px)]">
              {t("landing_brand")}
            </p>
            <h1
              id="landing-heading"
              className="mt-6 max-w-[360px] text-[clamp(28px,2.8vw,40px)] leading-[1.1] font-semibold tracking-[-0.045em]"
            >
              {t("landing_heading")}
            </h1>
            <p className="mt-4 max-w-[360px] text-sm leading-relaxed text-white/55">
              {t("landing_intro")}
            </p>
            <a
              href={BOT_URL}
              className="mt-6 flex w-full items-center justify-center gap-3 rounded-2xl bg-[#f4f1eb] px-5 py-4 text-sm font-semibold text-[#111] transition hover:bg-white/85 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#d8bd91]"
            >
              <TelegramIcon />
              {t("landing_start")}
            </a>
          </div>

          <div className="min-w-0 rounded-[28px] border border-white/8 bg-[#111] p-3 sm:p-4">
            <div className="mb-3 flex items-center justify-between gap-3 px-1 pt-1 text-xs text-white/50">
              <p>{t("landing_pick_mentor")}</p>
              <span aria-hidden="true">↙</span>
            </div>
            <div
              role="group"
              aria-label={t("landing_pick_mentor")}
              className="grid grid-cols-3 gap-2 sm:gap-3"
            >
              {mentors.map((mentor) => {
                const active = selectedId === mentor.id;
                return (
                  <button
                    key={mentor.id}
                    type="button"
                    aria-pressed={active}
                    aria-controls="mentor-biography"
                    onClick={() =>
                      void navigate({
                        search: { mentor: mentor.id },
                        replace: true,
                        resetScroll: false,
                      })
                    }
                    className={`group relative aspect-[.7] min-w-0 cursor-pointer overflow-hidden rounded-[18px] border text-left transition sm:aspect-[.95] lg:aspect-auto lg:h-[clamp(90px,calc(100svh-460px),260px)] ${active ? "border-[#d8bd91]" : "border-transparent hover:border-white/35"}`}
                  >
                    <img
                      src={mentor.image}
                      alt=""
                      className={`h-full w-full object-cover transition duration-500 motion-reduce:transition-none ${active ? "opacity-100" : "opacity-65 grayscale group-hover:opacity-100 group-hover:grayscale-0"}`}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/10 to-transparent" />
                    <span
                      aria-hidden="true"
                      className={`absolute top-2 right-2 grid h-6 w-6 place-items-center rounded-full text-xs ${active ? "bg-[#d8bd91] text-black" : "bg-black/30 text-white/70"}`}
                    >
                      {active ? "✓" : "+"}
                    </span>
                    <div className="absolute right-2 bottom-3 left-2 sm:right-4 sm:bottom-4 sm:left-4">
                      <p className="text-[13px] leading-tight font-semibold tracking-[-0.02em] sm:text-lg">
                        {mentorName(mentor.id)}
                      </p>
                      <p className="mt-1.5 text-[10px] text-white/65 sm:text-xs">
                        {agentMeta(mentor.id, "en").role}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>

            <article
              id="mentor-biography"
              aria-labelledby="biography-heading"
              className="mt-4 flex h-[340px] flex-col px-2 pb-1 sm:h-[260px] sm:px-3 lg:h-[250px]"
            >
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <h2 id="biography-heading" className="text-xl font-semibold tracking-[-0.025em]">
                  {mentorName(selectedId)}
                </h2>
                <span className="rounded-full bg-[#d8bd91]/10 px-2.5 py-1 text-[11px] text-[#d8bd91]">
                  {selected.role}
                </span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-white/50">
                {biography.years} · {biography.subtitle}
              </p>
              <div
                key={selectedId}
                aria-live="polite"
                className="landing-biography mt-3 space-y-3 text-[13px] leading-relaxed text-white/60"
              >
                <p>{t(`landing_bio_${selectedId}`)}</p>
                <p className="text-[#d8bd91]">{t(`landing_helps_${selectedId}`)}</p>
              </div>
              <a
                href={BOT_URL}
                className="mt-auto inline-flex min-h-10 shrink-0 items-center gap-3 self-start rounded-full border border-white/15 px-5 py-2.5 text-xs font-medium transition hover:border-[#d8bd91]/60 hover:bg-[#d8bd91]/5 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#d8bd91]"
              >
                {t("landing_chat", { name: mentorName(selectedId) })}
                <span aria-hidden="true">↗</span>
              </a>
            </article>
          </div>
        </section>
      </main>

      <footer className="shrink-0 px-5 py-2 sm:px-8">
        <div className="mx-auto flex max-w-[1384px] flex-wrap items-center justify-between gap-4 text-xs text-white/40">
          <p>{t("landing_copyright")}</p>
          <a
            href={BOT_URL}
            className="inline-flex min-h-11 items-center gap-2 transition hover:text-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#d8bd91]"
          >
            {t("landing_telegram")}
            <span aria-hidden="true">↗</span>
          </a>
        </div>
      </footer>
    </div>
  );
}
