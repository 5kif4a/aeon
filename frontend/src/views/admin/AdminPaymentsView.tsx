import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";

import { Pagination } from "../../components/admin/Pagination";
import { useAdminPayments } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { adminCard, adminLink, adminTable, adminTd, adminTh } from "../../lib/adminUi";

const route = getRouteApi("/admin/payments");

export function AdminPaymentsView() {
  const { t, formatDate, formatDateTime } = useAdminT();
  const { page } = route.useSearch();
  const navigate = useNavigate({ from: "/admin/payments" });
  const payments = useAdminPayments(page);

  return (
    <div className="grid gap-4">
      <h1 className="text-[22px] font-[750] tracking-[-0.02em]">{t("admin_nav_payments")}</h1>
      <section className={`${adminCard} overflow-x-auto p-0`}>
        {payments.isPending ? <p className="text-muted p-5">{t("admin_loading")}</p> : null}
        {payments.isError ? <p className="text-danger p-5">{t("admin_error")}</p> : null}
        {payments.data ? (
          <table className={adminTable}>
            <thead>
              <tr>
                <th className={adminTh}>{t("admin_col_date")}</th>
                <th className={adminTh}>{t("admin_col_user")}</th>
                <th className={`${adminTh} text-right`}>{t("admin_col_amount")}</th>
                <th className={adminTh}>{t("admin_col_status")}</th>
                <th className={adminTh}>{t("admin_col_until")}</th>
              </tr>
            </thead>
            <tbody>
              {payments.data.items.map((payment) => (
                <tr key={payment.id}>
                  <td className={`${adminTd} text-muted whitespace-nowrap`}>
                    {formatDateTime(payment.createdAt)}
                  </td>
                  <td className={adminTd}>
                    <Link
                      to="/admin/users/$userId"
                      params={{ userId: String(payment.userId) }}
                      className={adminLink}
                    >
                      {payment.userId}
                    </Link>
                    <div className="text-soft text-[11px]">
                      {payment.userLanguage}
                      {payment.userCountry ? ` · ${payment.userCountry}` : ""}
                    </div>
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
              {payments.data.items.length === 0 ? (
                <tr>
                  <td className={`${adminTd} text-soft text-center`} colSpan={5}>
                    {t("admin_empty")}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        ) : null}
        {payments.data ? (
          <div className="px-4 pb-3">
            <Pagination
              page={page}
              total={payments.data.total}
              onPage={(next) => navigate({ search: { page: next } })}
            />
          </div>
        ) : null}
      </section>
    </div>
  );
}
