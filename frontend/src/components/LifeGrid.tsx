import { useT } from "../lib/i18n-context";
import { LIFE_EXPECTANCY_YEARS, TOTAL_LIFE_WEEKS, WEEKS_PER_YEAR } from "../lib/life";

export function LifeGrid({ weeksLived }: { weeksLived: number }) {
  const { t } = useT();
  const currentWeek = Math.min(Math.max(weeksLived, 0), TOTAL_LIFE_WEEKS - 1);
  const eras: { endYear: number; weeks: number[] }[] = [];

  for (let startYear = 0; startYear < LIFE_EXPECTANCY_YEARS; startYear += 5) {
    const endYear = Math.min(startYear + 5, LIFE_EXPECTANCY_YEARS);
    const weeks = [];
    for (let week = startYear * WEEKS_PER_YEAR; week < endYear * WEEKS_PER_YEAR; week += 1) {
      weeks.push(week);
    }
    eras.push({ endYear, weeks });
  }

  const weekBase = "aspect-square min-w-[3px] border border-[#2d2b27]";
  return (
    <div
      aria-label={t("life_grid_aria")}
      className="grid gap-[clamp(12px,3vw,22px)] max-[390px]:gap-3"
    >
      {eras.map((era) => (
        <div
          className="grid grid-cols-[1fr_22px] items-end gap-2 max-[390px]:grid-cols-[1fr_18px] max-[390px]:gap-[5px]"
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
              const year = Math.floor(week / WEEKS_PER_YEAR) + 1;
              const weekInYear = (week % WEEKS_PER_YEAR) + 1;
              return (
                <span
                  key={week}
                  className={className}
                  title={t("life_week_title", { year, week: weekInYear })}
                ></span>
              );
            })}
          </div>
          <span className="translate-y-px font-serif text-[12px] leading-none text-[#5d574c]">
            {era.endYear}
          </span>
        </div>
      ))}
    </div>
  );
}
