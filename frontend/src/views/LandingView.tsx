const mentors = [
  {
    name: "Marcus Aurelius",
    role: "Stoic mentor",
    image: "/assets/marcus.webp",
  },
  {
    name: "Niccolò Machiavelli",
    role: "Strategist and pragmatist",
    image: "/assets/machiavelli.webp",
  },
  {
    name: "Carl Jung",
    role: "Guide to yourself",
    image: "/assets/jung.webp",
  },
];

const benefits = [
  [
    "01",
    "Answers from the sources",
    "Trial and Pro answers quote Meditations, The Prince, Discourses on Livy and Man and His Symbols — with the work, chapter and page.",
  ],
  [
    "02",
    "Council of three",
    "One decision, three independent views from Aurelius, Machiavelli and Jung, then a shared verdict with a single next step.",
  ],
  [
    "03",
    "Personal memory",
    "Your profile, active goal, diary and the current conversation feed every answer. Each mentor keeps their own thread.",
  ],
  [
    "04",
    "A daily rhythm",
    "One message a day at your hour: a mentor's thought, your goal and a check-in streak. A weekly review marks another week of your life on the calendar.",
  ],
];

const Check = () => (
  <svg viewBox="0 0 20 20" aria-hidden="true" className="h-5 w-5 shrink-0">
    <path
      d="m4 10.5 3.4 3.4L16 5.7"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export function LandingView() {
  return (
    <div className="landing min-h-screen overflow-hidden bg-[#050505] text-[#f4f1eb]">
      <header className="mx-auto flex h-[76px] max-w-[1320px] items-center justify-between px-5 sm:px-8">
        <a
          href="#top"
          className="flex items-center gap-3 text-xl font-semibold tracking-[-0.04em]"
          aria-label="Aeon"
        >
          <span className="grid h-8 w-8 place-items-center rounded-full border border-white/25 font-serif text-[15px]">
            Æ
          </span>
          aeon
        </a>
        <nav className="hidden items-center gap-8 text-sm text-white/48 md:flex">
          <a className="transition hover:text-white" href="#mentors">
            Mentors
          </a>
          <a className="transition hover:text-white" href="#features">
            Features
          </a>
          <a className="transition hover:text-white" href="#pricing">
            Pricing
          </a>
        </nav>
        <button className="rounded-full bg-[#f4f1eb] px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-white">
          Open the bot <span className="ml-2">↗</span>
        </button>
      </header>

      <main id="top">
        <section className="relative mx-auto flex min-h-[calc(100vh-76px)] max-w-[1440px] flex-col items-center justify-center px-5 pt-20 pb-10 text-center sm:px-8">
          <div className="landing-orbit landing-orbit-one" />
          <div className="landing-orbit landing-orbit-two" />
          <div className="relative z-10 max-w-[990px]">
            <div className="mx-auto mb-8 flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-4 py-2 text-xs text-white/58 backdrop-blur-xl">
              <span className="h-1.5 w-1.5 rounded-full bg-[#d8bd91] shadow-[0_0_12px_#d8bd91]" />
              Your personal council, always in Telegram
            </div>
            <h1 className="landing-display text-[clamp(58px,9.3vw,138px)] leading-[0.82] tracking-[-0.075em]">
              Think clearer.
              <br />
              Act sharper.
            </h1>
            <p className="mx-auto mt-9 max-w-[630px] text-[clamp(17px,2vw,22px)] leading-relaxed text-white/52">
              Talk with Marcus Aurelius, Machiavelli and Carl Jung. Aeon remembers your path and
              helps you make decisions every day.
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <button className="min-w-[190px] rounded-full bg-[#f4f1eb] px-7 py-4 text-sm font-bold text-black transition hover:scale-[1.02] hover:bg-white">
                Start for free <span className="ml-2">→</span>
              </button>
              <a
                href="#features"
                className="min-w-[190px] rounded-full border border-white/12 px-7 py-4 text-sm font-semibold text-white/72 transition hover:border-white/25 hover:text-white"
              >
                How it works
              </a>
            </div>
          </div>

          <div
            id="mentors"
            className="relative z-10 mt-20 grid w-full max-w-[1060px] grid-cols-3 gap-2 sm:gap-4"
          >
            {mentors.map((mentor, index) => (
              <div
                key={mentor.name}
                className={`landing-face relative aspect-[.82] overflow-hidden rounded-[18px] border border-white/9 bg-[#111] sm:rounded-[28px] ${index === 1 ? "sm:-translate-y-8" : ""}`}
              >
                <img
                  src={mentor.image}
                  alt={mentor.name}
                  className="h-full w-full object-cover grayscale transition duration-700 hover:scale-[1.03] hover:grayscale-0"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black via-black/5 to-transparent" />
                <div className="absolute right-2 bottom-3 left-2 text-left sm:right-6 sm:bottom-6 sm:left-6">
                  <p className="landing-display text-[clamp(14px,2.4vw,28px)] leading-none tracking-[-0.035em]">
                    {mentor.name}
                  </p>
                  <p className="mt-1 hidden text-xs text-white/52 sm:block">{mentor.role}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section
          id="features"
          className="border-y border-white/8 bg-[#f1eee7] px-5 py-24 text-[#111] sm:px-8 sm:py-32"
        >
          <div className="mx-auto max-w-[1240px]">
            <div className="grid gap-10 lg:grid-cols-[.82fr_1.18fr] lg:gap-24">
              <div>
                <p className="mb-5 text-xs font-bold tracking-[0.2em] text-black/40 uppercase">
                  Not just another AI chat
                </p>
                <h2 className="landing-display text-[clamp(48px,6.5vw,86px)] leading-[0.92] tracking-[-0.065em]">
                  Advice that knows your context
                </h2>
              </div>
              <div className="grid gap-px overflow-hidden rounded-[24px] border border-black/10 bg-black/10 sm:grid-cols-2">
                {benefits.map(([number, title, text]) => (
                  <article key={number} className="min-h-[240px] bg-[#f1eee7] p-7 sm:p-9">
                    <span className="text-xs font-bold text-black/30">{number}</span>
                    <h3 className="mt-16 text-xl font-semibold tracking-[-0.03em]">{title}</h3>
                    <p className="mt-3 text-[15px] leading-relaxed text-black/52">{text}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="pricing" className="px-5 py-24 sm:px-8 sm:py-32">
          <div className="mx-auto max-w-[1080px] text-center">
            <p className="mb-5 text-xs font-bold tracking-[0.2em] text-[#d8bd91] uppercase">
              Simple pricing
            </p>
            <h2 className="landing-display text-[clamp(52px,7vw,92px)] leading-none tracking-[-0.065em]">
              Start the conversation for free
            </h2>
            <p className="mx-auto mt-6 max-w-[540px] text-lg leading-relaxed text-white/45">
              Get to know the mentors, and when you want more depth — unlock Premium.
            </p>
            <div className="mt-14 grid gap-4 text-left md:grid-cols-2">
              <article className="rounded-[28px] border border-white/10 bg-white/[0.025] p-8 sm:p-10">
                <p className="text-sm font-semibold text-white/48">Basic</p>
                <p className="landing-display mt-6 text-6xl tracking-[-0.06em]">Free</p>
                <p className="mt-2 text-sm text-white/36">To try Aeon out</p>
                <ul className="mt-10 space-y-4 text-sm text-white/68">
                  {[
                    "3 prompt answers a day",
                    "Three AI mentors",
                    "Calendar, diary and goals",
                    "7-day trial, no payment",
                  ].map((item) => (
                    <li key={item} className="flex gap-3">
                      <Check />
                      {item}
                    </li>
                  ))}
                </ul>
                <button className="mt-10 w-full rounded-full border border-white/15 px-6 py-4 text-sm font-bold transition hover:border-white/30">
                  Start for free
                </button>
              </article>
              <article className="relative overflow-hidden rounded-[28px] bg-[#f1eee7] p-8 text-[#111] sm:p-10">
                <div className="absolute -top-28 -right-28 h-72 w-72 rounded-full bg-[#d8bd91]/60 blur-[80px]" />
                <div className="relative">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-black/48">Pro</p>
                    <span className="rounded-full bg-black px-3 py-1.5 text-[10px] font-bold tracking-[.1em] text-white uppercase">
                      Popular
                    </span>
                  </div>
                  <p className="landing-display mt-6 text-6xl tracking-[-0.06em]">350 ★</p>
                  <p className="mt-2 text-sm text-black/42">30 days of full access</p>
                  <ul className="mt-10 space-y-4 text-sm text-black/68">
                    {[
                      "30 RAG answers a day",
                      "Answers from the sources",
                      "Three councils of three a day",
                      "Extended context and memory",
                    ].map((item) => (
                      <li key={item} className="flex gap-3">
                        <Check />
                        {item}
                      </li>
                    ))}
                  </ul>
                  <button className="mt-10 w-full rounded-full bg-black px-6 py-4 text-sm font-bold text-white transition hover:scale-[1.01]">
                    Try Aeon
                  </button>
                </div>
              </article>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/8 px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-[1240px] flex-col gap-5 text-xs text-white/32 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Aeon. Time to think deeper.</p>
          <div className="flex gap-6">
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <span>Telegram</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
