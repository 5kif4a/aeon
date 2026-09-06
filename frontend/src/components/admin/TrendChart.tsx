import { useId, useMemo, useState } from "react";

import { useAdminT } from "../../lib/admin-i18n-context";
import { adminCard, adminMuted } from "../../lib/adminUi";

export interface TrendPoint {
  day: string;
  value: number;
}

interface TrendChartProps {
  title: string;
  points: TrendPoint[];
  /** Shown top-right: the sum (or a caller-provided headline) for the range. */
  headline: string;
  unit?: string;
}

const WIDTH = 560;
const HEIGHT = 160;
const PAD = { top: 12, right: 12, bottom: 22, left: 34 };

/**
 * Single-series area chart: one hue, 2px line, recessive grid, hover crosshair with a
 * tooltip, and a table view for accessibility. One series needs no legend; the title
 * names it.
 */
export function TrendChart({ title, points, headline, unit = "" }: TrendChartProps) {
  const { t, formatDate, formatNumber } = useAdminT();
  const [hover, setHover] = useState<number | null>(null);
  const [asTable, setAsTable] = useState(false);
  const gradientId = useId();

  const geometry = useMemo(() => {
    const innerWidth = WIDTH - PAD.left - PAD.right;
    const innerHeight = HEIGHT - PAD.top - PAD.bottom;
    const max = Math.max(1, ...points.map((point) => point.value));
    // Round the axis top to a friendly number so gridlines land on integers.
    const magnitude = 10 ** Math.floor(Math.log10(max));
    const top = Math.ceil(max / magnitude) * magnitude;
    const step = points.length > 1 ? innerWidth / (points.length - 1) : 0;
    const x = (index: number) => PAD.left + (points.length > 1 ? index * step : innerWidth / 2);
    const y = (value: number) => PAD.top + innerHeight - (value / top) * innerHeight;
    const line = points.map((point, index) => `${x(index)},${y(point.value)}`).join(" ");
    const baseline = PAD.top + innerHeight;
    const area = points.length
      ? `M${x(0)},${baseline} L${line.split(" ").join(" L")} L${x(points.length - 1)},${baseline} Z`
      : "";
    const ticks = [0, top / 2, top];
    return { x, y, line, area, baseline, ticks, top, step, innerWidth };
  }, [points]);

  const onMove = (event: React.MouseEvent<SVGSVGElement>) => {
    if (!points.length) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * WIDTH;
    const index = geometry.step ? Math.round((px - PAD.left) / geometry.step) : 0;
    setHover(Math.min(points.length - 1, Math.max(0, index)));
  };

  const hovered = hover !== null ? points[hover] : null;

  return (
    <section className={adminCard} aria-label={title}>
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-muted text-[13px] font-[700]">{title}</h3>
          <p className="text-text text-[22px] font-[750] tracking-[-0.02em]">
            {headline}
            {unit ? <span className="text-muted ml-1 text-[14px]">{unit}</span> : null}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setAsTable((value) => !value)}
          className="border-line text-muted hover:text-text h-7 cursor-pointer rounded-[6px] border px-2 text-[11px] font-[650]"
        >
          {asTable ? t("admin_chart_show_chart") : t("admin_chart_show_table")}
        </button>
      </header>

      {asTable ? (
        <div className="max-h-[200px] overflow-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-soft text-left">
                <th className="py-1 font-[600]">{t("admin_chart_day")}</th>
                <th className="py-1 text-right font-[600]">{title}</th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.day} className="border-line border-t">
                  <td className="text-muted py-1">{formatDate(point.day)}</td>
                  <td className="text-text py-1 text-right">{formatNumber(point.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="relative">
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className="h-auto w-full"
            role="img"
            aria-label={`${title}: ${headline}${unit}`}
            onMouseMove={onMove}
            onMouseLeave={() => setHover(null)}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0" stopColor="var(--color-gold)" stopOpacity="0.28" />
                <stop offset="1" stopColor="var(--color-gold)" stopOpacity="0.02" />
              </linearGradient>
            </defs>
            {geometry.ticks.map((tick) => (
              <g key={tick}>
                <line
                  x1={PAD.left}
                  x2={WIDTH - PAD.right}
                  y1={geometry.y(tick)}
                  y2={geometry.y(tick)}
                  stroke="var(--color-line)"
                  strokeWidth="1"
                />
                <text
                  x={PAD.left - 6}
                  y={geometry.y(tick) + 3.5}
                  textAnchor="end"
                  fontSize="10"
                  fill="var(--color-soft)"
                >
                  {formatNumber(tick)}
                </text>
              </g>
            ))}
            {points.length > 1 ? (
              <>
                <path d={geometry.area} fill={`url(#${gradientId})`} />
                <polyline
                  points={geometry.line}
                  fill="none"
                  stroke="var(--color-gold)"
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              </>
            ) : null}
            {points.length ? (
              <>
                <text
                  x={geometry.x(0)}
                  y={HEIGHT - 6}
                  fontSize="10"
                  fill="var(--color-soft)"
                  textAnchor="start"
                >
                  {formatDate(points[0].day)}
                </text>
                <text
                  x={geometry.x(points.length - 1)}
                  y={HEIGHT - 6}
                  fontSize="10"
                  fill="var(--color-soft)"
                  textAnchor="end"
                >
                  {formatDate(points[points.length - 1].day)}
                </text>
              </>
            ) : null}
            {hovered && hover !== null ? (
              <g>
                <line
                  x1={geometry.x(hover)}
                  x2={geometry.x(hover)}
                  y1={PAD.top}
                  y2={geometry.baseline}
                  stroke="var(--color-muted)"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                />
                <circle
                  cx={geometry.x(hover)}
                  cy={geometry.y(hovered.value)}
                  r="5"
                  fill="var(--color-gold)"
                  stroke="var(--color-surface)"
                  strokeWidth="2"
                />
              </g>
            ) : null}
          </svg>
          {hovered && hover !== null ? (
            <div
              className="border-line bg-surface-strong text-text pointer-events-none absolute top-1 rounded-[6px] border px-2 py-1 text-[11px] shadow-lg"
              style={{
                left: `${(geometry.x(hover) / WIDTH) * 100}%`,
                transform: hover > points.length / 2 ? "translateX(-105%)" : "translateX(6px)",
              }}
            >
              <div className={adminMuted}>{formatDate(hovered.day)}</div>
              <div className="font-[700]">
                {formatNumber(hovered.value)}
                {unit}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
