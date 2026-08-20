const mentors = [
  {
    name: "Марк Аврелий",
    role: "Стоический наставник",
    image: "/assets/marcus.webp",
    quote: "Отделяй то, что в твоей власти, от того, что тебе не принадлежит.",
  },
  {
    name: "Никколо Макиавелли",
    role: "Стратег и прагматик",
    image: "/assets/machiavelli.webp",
    quote: "Смотри на реальность прямо — и действуй раньше, чем действуют за тебя.",
  },
  {
    name: "Карл Юнг",
    role: "Проводник к себе",
    image: "/assets/jung.webp",
    quote: "То, чего ты избегаешь внутри, незаметно управляет тобой снаружи.",
  },
];

const benefits = [
  ["01", "Личная память", "Aeon помнит твои цели, контекст и прошлые разговоры — не приходится начинать заново."],
  ["02", "Ответы из первоисточников", "Советы опираются на труды Аврелия, Макиавелли и Юнга, а не на общие фразы."],
  ["03", "Ежедневный ритм", "Короткие утренние ориентиры и вечерняя рефлексия помогают не терять направление."],
  ["04", "Совет трёх", "Один вопрос — три разных взгляда: стойкость, стратегия и понимание себя."],
];

const Check = () => (
  <svg viewBox="0 0 20 20" aria-hidden="true" className="h-5 w-5 shrink-0">
    <path d="m4 10.5 3.4 3.4L16 5.7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export function LandingView() {
  return (
    <div className="landing min-h-screen overflow-hidden bg-[#050505] text-[#f4f1eb]">
      <div className="border-b border-white/8 bg-[#0d0d0d] px-5 py-2.5 text-center text-[11px] font-semibold tracking-[0.16em] text-white/55 uppercase">
        Три великих ума. Один личный советник.
      </div>

      <header className="mx-auto flex h-[76px] max-w-[1320px] items-center justify-between px-5 sm:px-8">
        <a href="#top" className="flex items-center gap-3 text-xl font-semibold tracking-[-0.04em]" aria-label="Aeon">
          <span className="grid h-8 w-8 place-items-center rounded-full border border-white/25 font-serif text-[15px]">Æ</span>
          aeon
        </a>
        <nav className="hidden items-center gap-8 text-sm text-white/48 md:flex">
          <a className="transition hover:text-white" href="#mentors">Наставники</a>
          <a className="transition hover:text-white" href="#features">Возможности</a>
          <a className="transition hover:text-white" href="#pricing">Тарифы</a>
        </nav>
        <button className="rounded-full bg-[#f4f1eb] px-5 py-2.5 text-sm font-semibold text-black transition hover:bg-white">
          Открыть бота <span className="ml-2">↗</span>
        </button>
      </header>

      <main id="top">
        <section className="relative mx-auto flex min-h-[calc(100vh-112px)] max-w-[1440px] flex-col items-center justify-center px-5 pt-20 pb-10 text-center sm:px-8">
          <div className="landing-orbit landing-orbit-one" />
          <div className="landing-orbit landing-orbit-two" />
          <div className="relative z-10 max-w-[990px]">
            <div className="mx-auto mb-8 flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-4 py-2 text-xs text-white/58 backdrop-blur-xl">
              <span className="h-1.5 w-1.5 rounded-full bg-[#d8bd91] shadow-[0_0_12px_#d8bd91]" />
              Личный совет всегда рядом в Telegram
            </div>
            <h1 className="landing-display text-[clamp(58px,9.3vw,138px)] leading-[0.82] tracking-[-0.075em]">
              Мысли яснее.<br />Действия точнее.
            </h1>
            <p className="mx-auto mt-9 max-w-[630px] text-[clamp(17px,2vw,22px)] leading-relaxed text-white/52">
              Поговори с Марком Аврелием, Макиавелли и Карлом Юнгом. Aeon помнит твой путь и помогает принимать решения каждый день.
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <button className="min-w-[190px] rounded-full bg-[#f4f1eb] px-7 py-4 text-sm font-bold text-black transition hover:scale-[1.02] hover:bg-white">
                Начать бесплатно <span className="ml-2">→</span>
              </button>
              <a href="#features" className="min-w-[190px] rounded-full border border-white/12 px-7 py-4 text-sm font-semibold text-white/72 transition hover:border-white/25 hover:text-white">
                Как это работает
              </a>
            </div>
          </div>

          <div className="relative z-10 mt-20 grid w-full max-w-[1060px] grid-cols-3 gap-2 sm:gap-4">
            {mentors.map((mentor, index) => (
              <div key={mentor.name} className={`landing-face relative aspect-[.82] overflow-hidden rounded-[18px] border border-white/9 bg-[#111] sm:rounded-[28px] ${index === 1 ? "sm:-translate-y-8" : ""}`}>
                <img src={mentor.image} alt={mentor.name} className="h-full w-full object-cover grayscale transition duration-700 hover:scale-[1.03] hover:grayscale-0" />
                <div className="absolute inset-0 bg-gradient-to-t from-black via-black/5 to-transparent" />
                <div className="absolute right-2 bottom-3 left-2 text-left sm:right-6 sm:bottom-6 sm:left-6">
                  <p className="landing-display text-[clamp(14px,2.4vw,28px)] leading-none tracking-[-0.035em]">{mentor.name}</p>
                  <p className="mt-1 hidden text-xs text-white/52 sm:block">{mentor.role}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section id="features" className="border-y border-white/8 bg-[#f1eee7] px-5 py-24 text-[#111] sm:px-8 sm:py-32">
          <div className="mx-auto max-w-[1240px]">
            <div className="grid gap-10 lg:grid-cols-[.82fr_1.18fr] lg:gap-24">
              <div>
                <p className="mb-5 text-xs font-bold tracking-[0.2em] text-black/40 uppercase">Не просто чат с AI</p>
                <h2 className="landing-display text-[clamp(48px,6.5vw,86px)] leading-[0.92] tracking-[-0.065em]">Совет, который знает твой контекст</h2>
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

        <section id="mentors" className="px-5 py-24 sm:px-8 sm:py-32">
          <div className="mx-auto max-w-[1240px]">
            <div className="mb-14 max-w-[760px]">
              <p className="mb-5 text-xs font-bold tracking-[0.2em] text-[#d8bd91] uppercase">Три перспективы</p>
              <h2 className="landing-display text-[clamp(50px,7vw,94px)] leading-[0.9] tracking-[-0.065em]">Выбирай голос под свой вопрос</h2>
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              {mentors.map((mentor, index) => (
                <article key={mentor.name} className="group rounded-[28px] border border-white/9 bg-white/[0.025] p-3">
                  <div className="relative aspect-[1.12] overflow-hidden rounded-[20px]">
                    <img src={mentor.image} alt="" className="h-full w-full object-cover grayscale transition duration-700 group-hover:scale-105 group-hover:grayscale-0" />
                    <span className="absolute top-4 left-4 rounded-full border border-white/15 bg-black/35 px-3 py-1.5 text-[10px] font-bold tracking-[.14em] text-white/65 uppercase backdrop-blur-md">0{index + 1}</span>
                  </div>
                  <div className="px-3 pt-6 pb-5">
                    <h3 className="landing-display text-3xl tracking-[-0.04em]">{mentor.name}</h3>
                    <p className="mt-1 text-sm text-[#d8bd91]">{mentor.role}</p>
                    <p className="mt-8 border-t border-white/8 pt-6 text-[15px] leading-relaxed text-white/46">«{mentor.quote}»</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="pricing" className="px-5 py-24 sm:px-8 sm:py-32">
          <div className="mx-auto max-w-[1080px] text-center">
            <p className="mb-5 text-xs font-bold tracking-[0.2em] text-[#d8bd91] uppercase">Простые тарифы</p>
            <h2 className="landing-display text-[clamp(52px,7vw,92px)] leading-none tracking-[-0.065em]">Начни разговор бесплатно</h2>
            <p className="mx-auto mt-6 max-w-[540px] text-lg leading-relaxed text-white/45">Познакомься с наставниками, а когда захочешь больше глубины — открой Premium.</p>
            <div className="mt-14 grid gap-4 text-left md:grid-cols-2">
              <article className="rounded-[28px] border border-white/10 bg-white/[0.025] p-8 sm:p-10">
                <p className="text-sm font-semibold text-white/48">Базовый</p>
                <p className="landing-display mt-6 text-6xl tracking-[-0.06em]">0 ₸</p>
                <p className="mt-2 text-sm text-white/36">Чтобы попробовать Aeon</p>
                <ul className="mt-10 space-y-4 text-sm text-white/68">
                  {["3 prompt-ответа в день", "Три AI-наставника", "Календарь, дневник и цели", "7 дней Trial без оплаты"].map((item) => <li key={item} className="flex gap-3"><Check />{item}</li>)}
                </ul>
                <button className="mt-10 w-full rounded-full border border-white/15 px-6 py-4 text-sm font-bold transition hover:border-white/30">Начать бесплатно</button>
              </article>
              <article className="relative overflow-hidden rounded-[28px] bg-[#f1eee7] p-8 text-[#111] sm:p-10">
                <div className="absolute -top-28 -right-28 h-72 w-72 rounded-full bg-[#d8bd91]/60 blur-[80px]" />
                <div className="relative">
                  <div className="flex items-center justify-between"><p className="text-sm font-semibold text-black/48">Pro</p><span className="rounded-full bg-black px-3 py-1.5 text-[10px] font-bold tracking-[.1em] text-white uppercase">Популярный</span></div>
                  <p className="landing-display mt-6 text-6xl tracking-[-0.06em]">299 ★</p>
                  <p className="mt-2 text-sm text-black/42">30 дней полного доступа</p>
                  <ul className="mt-10 space-y-4 text-sm text-black/68">
                    {["30 RAG-ответов в день", "Ответы из первоисточников", "Три Совета трёх в день", "Расширенный контекст и память"].map((item) => <li key={item} className="flex gap-3"><Check />{item}</li>)}
                  </ul>
                  <button className="mt-10 w-full rounded-full bg-black px-6 py-4 text-sm font-bold text-white transition hover:scale-[1.01]">Попробовать Aeon</button>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section className="px-5 pt-16 sm:px-8">
          <div className="relative mx-auto max-w-[1240px] overflow-hidden rounded-t-[36px] border border-b-0 border-white/10 bg-[#111] px-6 py-20 text-center sm:px-12 sm:py-28">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(216,189,145,.25),transparent_50%)]" />
            <div className="relative">
              <p className="landing-display text-[clamp(52px,8vw,112px)] leading-[0.88] tracking-[-0.07em]">Спроси того,<br />кто видел глубже.</p>
              <button className="mt-10 rounded-full bg-[#f4f1eb] px-8 py-4 text-sm font-bold text-black transition hover:scale-[1.02]">Открыть бота в Telegram <span className="ml-2">↗</span></button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-white/8 px-5 py-8 sm:px-8">
        <div className="mx-auto flex max-w-[1240px] flex-col gap-5 text-xs text-white/32 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Aeon. Время думать глубже.</p>
          <div className="flex gap-6"><a href="#features">Возможности</a><a href="#pricing">Тарифы</a><span>Telegram</span></div>
        </div>
      </footer>
    </div>
  );
}
