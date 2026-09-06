import { useT } from "../lib/i18n-context";
import { LIFE_EXPECTANCY_YEARS, TOTAL_LIFE_WEEKS, WEEKS_PER_YEAR } from "../lib/life";

export function LifeGrid({ weeksLived }: { weeksLived: number }) {
  const { t } = useT();
  const currentWeek = Math.min(Math.max(weeksLived, 0), TOTAL_LIFE_WEEKS - 1);
  const eras: { endYear: number; weeks: number[]; isCurrent: boolean }[] = [];

  for (let startYear = 0; startYear < LIFE_EXPECTANCY_YEARS; startYear += 5) {
    const endYear = Math.min(startYear + 5, LIFE_EXPECTANCY_YEARS);
    const weeks = [];
    for (let week = startYear * WEEKS_PER_YEAR; week < endYear * WEEKS_PER_YEAR; week += 1) {
      weeks.push(week);
    }
    const isCurrent = weeks[0] <= currentWeek && currentWeek <= weeks[weeks.length - 1];
    eras.push({ endYear, weeks, isCurrent });
  }

  const weekBase = "aspect-square min-w-[3px] border border-[#2d2b27]";
  const livedCount = Math.min(Math.max(weeksLived, 0), TOTAL_LIFE_WEEKS);
  return (
    <div>
      <div
        role="img"
        aria-label={t("life_grid_aria")}
        className="grid gap-[clamp(12px,3vw,22px)] max-[390px]:gap-3"
      >
        {eras.map((era) => (
          <div
            className={`grid grid-cols-[1fr_22px] items-end gap-2 max-[390px]:grid-cols-[1fr_18px] max-[390px]:gap-[5px] ${
              era.isCurrent
                ? "-mx-1.5 rounded-[4px] px-1.5 py-1 shadow-[inset_0_0_0_1px_rgba(125,92,62,0.55)]"
                : ""
            }`}
            key={era.endYear}
          >
            <div className="grid grid-cols-[repeat(52,minmax(3px,1fr))] gap-[2px] max-[390px]:gap-px">
              {era.weeks.map((week) => {
                const className =
                  week < weeksLived
                    ? `${weekBase} bg-[#25231f]`
                    : week === currentWeek
                      ? `${weekBase} border-[#7d5c3e] bg-[#c5a16d] shadow-[0_0_0_1px_rgba(125,92,62,0.38)]`
                      : weekBase;
                return <span key={week} className={className} aria-hidden="true"></span>;
              })}
            </div>
            <span
              className={`translate-y-px font-serif text-[12px] leading-none ${
                era.isCurrent ? "font-[700] text-[#7d5c3e]" : "text-[#5d574c]"
              }`}
            >
              {era.endYear}
            </span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-center text-[12px] font-[650] text-[#5c5548]">
        {t("life_grid_summary", {
          lived: livedCount.toLocaleString(),
          total: TOTAL_LIFE_WEEKS.toLocaleString(),
        })}
      </p>
    </div>
  );
}
