import { useAdminT } from "../../lib/admin-i18n-context";
import { adminCard } from "../../lib/adminUi";

interface BreakdownBarsProps {
  title: string;
  rows: { label: string; value: number }[];
}

/**
 * Magnitude comparison across a few named categories: one hue, direct labels carry
 * identity, so color never has to.
 */
export function BreakdownBars({ title, rows }: BreakdownBarsProps) {
  const { formatNumber, t } = useAdminT();
  const max = Math.max(1, ...rows.map((row) => row.value));
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  return (
    <section className={adminCard} aria-label={title}>
      <h3 className="text-muted mb-3 text-[13px] font-[700]">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-soft text-[13px]">{t("admin_empty")}</p>
      ) : (
        <ul className="grid gap-2.5">
          {rows.map((row) => (
            <li key={row.label} className="grid grid-cols-[120px_1fr_64px] items-center gap-3">
              <span className="text-text truncate text-[13px]">{row.label}</span>
              <span className="h-2 overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
                <span
                  className="bg-gold block h-full rounded-full"
                  style={{ width: `${(row.value / max) * 100}%` }}
                />
              </span>
              <span className="text-text text-right text-[13px] tabular-nums">
                {formatNumber(row.value)}
                <span className="text-soft ml-1 text-[11px]">
                  {total ? Math.round((row.value / total) * 100) : 0}%
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
