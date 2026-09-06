import { getRouteApi, Link } from "@tanstack/react-router";

import { BreakdownBars } from "../../components/admin/BreakdownBars";
import { TrendChart } from "../../components/admin/TrendChart";
import { useAdminStats } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { adminCard } from "../../lib/adminUi";
import { agentLabel, STATS_RANGES } from "../../lib/adminFormat";
import type { TranslationKey } from "../../lib/i18n";

const route = getRouteApi("/admin/");

interface Tile {
  key: TranslationKey;
  value: number;
  hint?: string;
}

export function AdminDashboardView() {
  const { t, formatNumber, lang } = useAdminT();
  const { days } = route.useSearch();
  const stats = useAdminStats(days);

  if (stats.isPending) return <p className="text-muted">{t("admin_loading")}</p>;
  if (stats.isError || !stats.data) return <p className="text-danger">{t("admin_error")}</p>;

  const { totals, series } = stats.data;
  const questions = totals.promptQuestions + totals.ragQuestions + totals.councilQuestions;

  const tiles: Tile[] = [
    {
      key: "admin_stat_new_users",
      value: totals.newUsers,
      hint: `${t("admin_stat_onboarded")} ${formatNumber(totals.onboardingCompleted)}`,
    },
    {
      key: "admin_stat_active_users",
      value: totals.activeUsers,
      hint: `${t("admin_stat_total_users")} ${formatNumber(totals.usersTotal)}`,
    },
    {
      key: "admin_stat_questions",
      value: questions,
      hint: `${t("admin_stat_limit_hits")} ${formatNumber(totals.limitHits)}`,
    },
    {
      key: "admin_stat_revenue",
      value: totals.paymentsStars,
      hint: `${t("admin_stat_payments")} ${formatNumber(totals.paymentsCount)}`,
    },
    {
      key: "admin_stat_pro_active",
      value: totals.proActive,
      hint: `${t("admin_stat_expiring")} ${formatNumber(totals.proExpiringSoon)} · ${t("admin_stat_not_renewing")} ${formatNumber(totals.proNotRenewing)}`,
    },
    {
      key: "admin_stat_trial_active",
      value: totals.trialActive,
      hint: `${t("admin_stat_trials_started")} ${formatNumber(totals.trialsStarted)} · ${t("admin_stat_canceled")} ${formatNumber(totals.subscriptionsCanceled)}`,
    },
  ];

  const agentRows = Object.entries(totals.conversationsByAgent).map(([agentId, value]) => ({
    label: agentLabel(agentId, lang),
    value,
  }));
  const modeRows = [
    { label: t("admin_mode_prompt"), value: totals.promptQuestions },
    { label: t("admin_mode_rag"), value: totals.ragQuestions },
    { label: t("admin_mode_council"), value: totals.councilQuestions },
  ];

  return (
    <div className="grid gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-[750] tracking-[-0.02em]">{t("admin_nav_dashboard")}</h1>
          <p className="text-soft text-[12px]">{stats.data.window.label}</p>
        </div>
        <div className="border-line flex gap-1 rounded-[8px] border p-1" role="tablist">
          {STATS_RANGES.map((range) => (
            <Link
              key={range}
              to="/admin"
              search={{ days: range }}
              role="tab"
              aria-selected={range === days}
              className={`rounded-[6px] px-3 py-1.5 text-[12px] font-[700] ${
                range === days ? "bg-surface-strong text-text" : "text-muted hover:text-text"
              }`}
            >
              {t("admin_range_days", { days: range })}
            </Link>
          ))}
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {tiles.map((tile) => (
          <article key={tile.key} className={adminCard}>
            <p className="text-muted text-[12px] font-[700]">{t(tile.key)}</p>
            <p className="mt-1 text-[28px] font-[750] tracking-[-0.03em] tabular-nums">
              {formatNumber(tile.value)}
              {tile.key === "admin_stat_revenue" ? (
                <span className="text-gold ml-1 text-[16px]">★</span>
              ) : null}
            </p>
            {tile.hint ? <p className="text-soft mt-1 text-[11px]">{tile.hint}</p> : null}
          </article>
        ))}
        {totals.generationFailures > 0 ? (
          <article className={`${adminCard} border-danger/40`}>
            <p className="text-danger text-[12px] font-[700]">{t("admin_stat_failures")}</p>
            <p className="mt-1 text-[28px] font-[750] tracking-[-0.03em] tabular-nums">
              {formatNumber(totals.generationFailures)}
            </p>
          </article>
        ) : null}
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <TrendChart
          title={t("admin_stat_new_users")}
          headline={formatNumber(totals.newUsers)}
          points={series.map((point) => ({ day: point.day, value: point.newUsers }))}
        />
        <TrendChart
          title={t("admin_stat_active_users")}
          headline={formatNumber(totals.activeUsers)}
          points={series.map((point) => ({ day: point.day, value: point.activeUsers }))}
        />
        <TrendChart
          title={t("admin_stat_questions")}
          headline={formatNumber(questions)}
          points={series.map((point) => ({ day: point.day, value: point.questions }))}
        />
        <TrendChart
          title={t("admin_stat_revenue")}
          headline={formatNumber(totals.paymentsStars)}
          unit="★"
          points={series.map((point) => ({ day: point.day, value: point.paymentsStars }))}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <BreakdownBars title={t("admin_breakdown_modes")} rows={modeRows} />
        <BreakdownBars title={t("admin_breakdown_agents")} rows={agentRows} />
      </section>
    </div>
  );
}
