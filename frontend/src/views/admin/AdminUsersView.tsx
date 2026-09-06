import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { Pagination } from "../../components/admin/Pagination";
import { useAdminUsers } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { planChipClass } from "../../lib/adminFormat";
import {
  adminCard,
  adminChip,
  adminInput,
  adminLink,
  adminSelect,
  adminTable,
  adminTableScroll,
  adminTd,
  adminTh,
} from "../../lib/adminUi";

const route = getRouteApi("/admin/users");
const PLANS = ["", "Free", "Trial", "Pro"] as const;

export function AdminUsersView() {
  const { t, formatDateTime, formatNumber } = useAdminT();
  const search = route.useSearch();
  const navigate = useNavigate({ from: "/admin/users" });
  const users = useAdminUsers(search);
  const [draft, setDraft] = useState(search.q);

  useEffect(() => setDraft(search.q), [search.q]);

  const update = (patch: Partial<typeof search>) =>
    navigate({ search: (previous) => ({ ...previous, ...patch }) });

  return (
    <div className="grid gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-[22px] font-[750] tracking-[-0.02em]">{t("admin_nav_users")}</h1>
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            update({ q: draft.trim(), page: 1 });
          }}
        >
          <input
            className={`${adminInput} w-[260px]`}
            placeholder={t("admin_users_search_placeholder")}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          <select
            className={adminSelect}
            value={search.plan}
            onChange={(event) => update({ plan: event.target.value, page: 1 })}
            aria-label={t("admin_col_plan")}
          >
            {PLANS.map((plan) => (
              <option key={plan} value={plan}>
                {plan || t("admin_filter_all_plans")}
              </option>
            ))}
          </select>
        </form>
      </header>

      <section className={`${adminCard} p-0`}>
        {users.isPending ? <p className="text-muted p-5">{t("admin_loading")}</p> : null}
        {users.isError ? <p className="text-danger p-5">{t("admin_error")}</p> : null}
        {users.data ? (
          <div className={adminTableScroll}>
            <table className={adminTable}>
              <thead>
                <tr>
                  <th className={adminTh}>{t("admin_col_user")}</th>
                  <th className={adminTh}>{t("admin_col_plan")}</th>
                  <th className={adminTh}>{t("admin_col_country")}</th>
                  <th className={`${adminTh} text-right`}>{t("admin_col_questions")}</th>
                  <th className={`${adminTh} text-right`}>{t("admin_col_conversations")}</th>
                  <th className={`${adminTh} text-right`}>{t("admin_col_stars")}</th>
                  <th className={adminTh}>{t("admin_col_last_active")}</th>
                  <th className={adminTh}>{t("admin_col_created")}</th>
                </tr>
              </thead>
              <tbody>
                {users.data.items.map((user) => (
                  <tr key={user.id} className="hover:bg-[rgba(255,255,255,0.02)]">
                    <td className={adminTd}>
                      <Link
                        to="/admin/users/$userId"
                        params={{ userId: String(user.id) }}
                        className={adminLink}
                      >
                        {user.name || t("admin_user_unnamed")}
                      </Link>
                      <div className="text-soft text-[11px]">
                        {user.id} · {user.language}
                      </div>
                    </td>
                    <td className={adminTd}>
                      <span className={`${adminChip} ${planChipClass(user.plan)}`}>
                        {user.plan}
                      </span>
                    </td>
                    <td className={adminTd}>{user.country || "—"}</td>
                    <td className={`${adminTd} text-right tabular-nums`}>
                      {formatNumber(user.questionsTotal)}
                    </td>
                    <td className={`${adminTd} text-right tabular-nums`}>
                      {formatNumber(user.conversations)}
                    </td>
                    <td className={`${adminTd} text-right tabular-nums`}>
                      {formatNumber(user.paymentsStars)}
                    </td>
                    <td className={`${adminTd} text-muted whitespace-nowrap`}>
                      {formatDateTime(user.lastActiveAt)}
                    </td>
                    <td className={`${adminTd} text-muted whitespace-nowrap`}>
                      {formatDateTime(user.createdAt)}
                    </td>
                  </tr>
                ))}
                {users.data.items.length === 0 ? (
                  <tr>
                    <td className={`${adminTd} text-soft text-center`} colSpan={8}>
                      {t("admin_empty")}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
        {users.data ? (
          <div className="px-4 pb-3">
            <Pagination
              page={search.page}
              total={users.data.total}
              onPage={(page) => update({ page })}
            />
          </div>
        ) : null}
      </section>
    </div>
  );
}
