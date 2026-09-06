import { getRouteApi, Link } from "@tanstack/react-router";
import { useState } from "react";

import { useAdminUser, useGrantPro } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { agentLabel, planChipClass } from "../../lib/adminFormat";
import {
  adminButton,
  adminCard,
  adminChip,
  adminInput,
  adminLink,
  adminMuted,
  adminPrimaryButton,
  adminTable,
  adminTd,
  adminTh,
} from "../../lib/adminUi";

const route = getRouteApi("/admin/users/$userId");
const GRANT_OPTIONS = [7, 30, 90];

export function AdminUserDetailView() {
  const { t, lang, formatDate, formatDateTime, formatNumber } = useAdminT();
  const { userId } = route.useParams();
  const id = Number(userId);
  const detail = useAdminUser(id);
  const grant = useGrantPro(id);
  const [days, setDays] = useState(30);

  if (detail.isPending) return <p className="text-muted">{t("admin_loading")}</p>;
  if (detail.isError || !detail.data) return <p className="text-danger">{t("admin_error")}</p>;

  const { user, usage30d, payments, conversations, events } = detail.data;
  const facts: [string, string][] = [
    [t("admin_col_plan"), user.plan],
    [t("admin_user_language"), user.language],
    [t("admin_col_country"), user.country || "—"],
    [t("admin_user_birth_date"), formatDate(user.birthDate)],
    [t("admin_user_activity"), user.activity || "—"],
    [t("admin_col_created"), formatDateTime(user.createdAt)],
    [t("admin_user_pro_until"), formatDateTime(user.proExpiresAt)],
    [t("admin_user_trial_until"), formatDateTime(user.trialExpiresAt)],
    [t("admin_user_auto_renew"), user.proAutoRenew ? t("admin_yes") : t("admin_no")],
  ];

  return (
    <div className="grid gap-4">
      <Link
        to="/admin/users"
        search={{ q: "", plan: "", page: 1 }}
        className={`${adminLink} text-[12px]`}
      >
        ← {t("admin_nav_users")}
      </Link>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-[750] tracking-[-0.02em]">
            {user.name || t("admin_user_unnamed")}{" "}
            <span className={`${adminChip} ${planChipClass(user.plan)} ml-2 align-middle`}>
              {user.plan}
            </span>
          </h1>
          <p className={adminMuted}>ID {user.id}</p>
        </div>
        <form
          className="flex items-center gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            grant.mutate(days);
          }}
        >
          <label className="text-muted text-[12px]" htmlFor="grant-days">
            {t("admin_grant_days")}
          </label>
          <input
            id="grant-days"
            type="number"
            min={1}
            max={365}
            className={`${adminInput} w-[80px]`}
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          />
          {GRANT_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              className={adminButton}
              onClick={() => setDays(option)}
            >
              {option}
            </button>
          ))}
          <button
            type="submit"
            className={adminPrimaryButton}
            disabled={grant.isPending || days < 1}
          >
            {t("admin_grant_pro")}
          </button>
        </form>
      </header>
      {grant.isSuccess ? <p className="text-success text-[13px]">{t("admin_grant_done")}</p> : null}
      {grant.isError ? <p className="text-danger text-[13px]">{t("admin_error")}</p> : null}

      <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <article className={adminCard}>
          <h2 className="text-muted mb-3 text-[13px] font-[700]">{t("admin_user_profile")}</h2>
          <dl className="grid grid-cols-[140px_1fr] gap-x-3 gap-y-2 text-[13px]">
            {facts.map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-soft">{label}</dt>
                <dd className="text-text">{value}</dd>
              </div>
            ))}
          </dl>
          {user.mainGoal ? (
            <p className="border-line text-muted mt-4 border-t pt-3 text-[13px] leading-relaxed">
              <span className="text-soft">{t("admin_user_goal")}: </span>
              {user.mainGoal}
            </p>
          ) : null}
        </article>
        <article className={adminCard}>
          <h2 className="text-muted mb-3 text-[13px] font-[700]">{t("admin_user_usage_30d")}</h2>
          <div className="grid grid-cols-3 gap-3">
            {(
              [
                ["admin_mode_prompt", usage30d.prompt],
                ["admin_mode_rag", usage30d.rag],
                ["admin_mode_council", usage30d.council],
              ] as const
            ).map(([key, value]) => (
              <div key={key}>
                <p className="text-soft text-[11px]">{t(key)}</p>
                <p className="text-[24px] font-[750] tabular-nums">{formatNumber(value)}</p>
              </div>
            ))}
          </div>
          <p className={`${adminMuted} mt-4`}>
            {t("admin_col_stars")}: {formatNumber(user.paymentsStars)} ★
          </p>
        </article>
      </section>

      <section className={`${adminCard} overflow-x-auto p-0`}>
        <h2 className="text-muted px-5 pt-4 text-[13px] font-[700]">
          {t("admin_nav_conversations")}
        </h2>
        <table className={`${adminTable} mt-2`}>
          <thead>
            <tr>
              <th className={adminTh}>{t("admin_col_agent")}</th>
              <th className={adminTh}>{t("admin_col_title")}</th>
              <th className={adminTh}>{t("admin_col_status")}</th>
              <th className={`${adminTh} text-right`}>{t("admin_col_messages")}</th>
              <th className={adminTh}>{t("admin_col_updated")}</th>
            </tr>
          </thead>
          <tbody>
            {conversations.map((conversation) => (
              <tr key={conversation.id}>
                <td className={adminTd}>{agentLabel(conversation.agentId, lang)}</td>
                <td className={adminTd}>
                  <Link
                    to="/admin/conversations/$conversationId"
                    params={{ conversationId: conversation.id }}
                    className={adminLink}
                  >
                    {conversation.title || t("admin_conversation_untitled")}
                  </Link>
                </td>
                <td className={adminTd}>
                  {t(
                    conversation.status === "active"
                      ? "admin_status_active"
                      : "admin_status_closed",
                  )}
                </td>
                <td className={`${adminTd} text-right tabular-nums`}>
                  {conversation.messageCount}
                </td>
                <td className={`${adminTd} text-muted whitespace-nowrap`}>
                  {formatDateTime(conversation.updatedAt)}
                </td>
              </tr>
            ))}
            {conversations.length === 0 ? (
              <tr>
                <td className={`${adminTd} text-soft text-center`} colSpan={5}>
                  {t("admin_empty")}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className={`${adminCard} overflow-x-auto`}>
          <h2 className="text-muted mb-2 text-[13px] font-[700]">{t("admin_nav_payments")}</h2>
          <table className="w-full text-[13px]">
            <thead>
              <tr>
                <th className={adminTh}>{t("admin_col_date")}</th>
                <th className={`${adminTh} text-right`}>{t("admin_col_amount")}</th>
                <th className={adminTh}>{t("admin_col_status")}</th>
                <th className={adminTh}>{t("admin_col_until")}</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((payment) => (
                <tr key={payment.id}>
                  <td className={`${adminTd} text-muted whitespace-nowrap`}>
                    {formatDateTime(payment.createdAt)}
                  </td>
                  <td className={`${adminTd} text-right tabular-nums`}>
                    {payment.amount} {payment.currency === "XTR" ? "★" : payment.currency}
                  </td>
                  <td className={adminTd}>
                    {payment.status}
                    {payment.isRecurring ? ` · ${t("admin_payment_recurring")}` : ""}
                  </td>
                  <td className={`${adminTd} text-muted whitespace-nowrap`}>
                    {formatDate(payment.subscriptionExpiresAt)}
                  </td>
                </tr>
              ))}
              {payments.length === 0 ? (
                <tr>
                  <td className={`${adminTd} text-soft text-center`} colSpan={4}>
                    {t("admin_empty")}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </article>
        <article className={adminCard}>
          <h2 className="text-muted mb-2 text-[13px] font-[700]">{t("admin_user_events")}</h2>
          <ul className="grid max-h-[360px] gap-2 overflow-auto text-[12px]">
            {events.map((event) => (
              <li
                key={event.id}
                className="border-line grid grid-cols-[150px_1fr] gap-2 border-b pb-2 last:border-b-0"
              >
                <span className="text-soft whitespace-nowrap">
                  {formatDateTime(event.createdAt)}
                </span>
                <span>
                  <span className="text-text font-[700]">{event.type}</span>
                  {Object.keys(event.payload).length ? (
                    <span className="text-muted ml-2 break-all">
                      {JSON.stringify(event.payload)}
                    </span>
                  ) : null}
                </span>
              </li>
            ))}
            {events.length === 0 ? <li className="text-soft">{t("admin_empty")}</li> : null}
          </ul>
        </article>
      </section>
    </div>
  );
}
