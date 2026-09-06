import { Skeleton } from "./Skeleton";
import { useBillingStatus } from "../hooks/queries";
import { useT } from "../lib/i18n-context";

/**
 * Brand row shown above every screen: the Sisyphus mark, the wordmark, and the
 * plan/answers-left chip. The chip keeps one box across loading, data and error
 * so the row never shifts.
 */
export function TopBar() {
  const { t } = useT();
  const { data: billing, isPending } = useBillingStatus();
  const planLabel = billing
    ? t(billing.plan === "Pro" ? "plan_pro" : billing.plan === "Trial" ? "plan_trial" : "plan_free")
    : "";

  return (
    <header className="flex min-h-[52px] items-center justify-between gap-3 pt-[18px] pb-1">
      {/* The line art is white on black, so it composites onto the page with no matte. */}
      <span className="flex min-w-0 items-center gap-2">
        <img
          src="/assets/sisyphus-mark.webp"
          alt=""
          aria-hidden="true"
          width={147}
          height={160}
          fetchPriority="high"
          className="h-11 w-auto shrink-0 opacity-90"
        />
        <strong className="font-serif text-[18px] font-normal tracking-[0.18em]">AEON</strong>
      </span>

      <span className="border-line bg-surface/80 text-muted inline-flex min-h-9 min-w-[148px] items-center justify-end gap-2 rounded-[8px] border px-3 text-[12px]">
        {isPending ? (
          <Skeleton className="h-3 w-[108px]" />
        ) : billing ? (
          <>
            <b className="text-text font-[750]">{planLabel}</b>
            <i className="bg-soft h-1 w-1 rounded-full" />
            {t("home_answers_left", { count: billing.dailyRemaining })}
          </>
        ) : (
          <span aria-hidden="true">—</span>
        )}
      </span>
    </header>
  );
}
