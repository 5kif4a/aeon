import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";

import { Pagination } from "../../components/admin/Pagination";
import { SortableTh } from "../../components/admin/SortableTh";
import { useAdminPayments } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import type { SortOrder } from "../../lib/adminFormat";
import {
  adminPageFill,
  adminTableCard,
  adminTableFill,
  adminLink,
  adminTable,
  adminTd,
} from "../../lib/adminUi";
import type { TranslationKey } from "../../lib/i18n";

const route = getRouteApi("/admin/payments");

/** Columns in render order; `field` is the sort key `services/admin.list_payments` knows. */
const COLUMNS: { field: string; label: TranslationKey; align?: "left" | "right" }[] = [
  { field: "date", label: "admin_col_date" },
  { field: "user", label: "admin_col_user" },
  { field: "amount", label: "admin_col_amount", align: "right" },
  { field: "status", label: "admin_col_status" },
  { field: "until", label: "admin_col_until" },
];

export function AdminPaymentsView() {
  const { t, formatDate, formatDateTime } = useAdminT();
  const search = route.useSearch();
  const navigate = useNavigate({ from: "/admin/payments" });
  const payments = useAdminPayments(search);

  const update = (patch: Partial<typeof search>) =>
    navigate({ search: (previous) => ({ ...previous, ...patch }) });

  // A new sort reshuffles every page, so page 5 of the old order means nothing in the new one.
  const sortBy = (sort: string, order: SortOrder) => update({ sort, order, page: 1 });

  return (
    <div className={adminPageFill}>
      <section className={adminTableCard}>
        {payments.isPending ? <p className="text-muted p-5">{t("admin_loading")}</p> : null}
        {payments.isError ? <p className="text-danger p-5">{t("admin_error")}</p> : null}
        {payments.data ? (
          <div className={adminTableFill}>
            <table className={adminTable}>
              <thead>
                <tr>
                  {COLUMNS.map((column) => (
                    <SortableTh
                      key={column.field}
                      label={t(column.label)}
                      field={column.field}
                      align={column.align}
                      sort={search.sort || "date"}
                      order={search.order}
                      onSort={sortBy}
                    />
                  ))}
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
                    <td className={`${adminTd} text-soft text-center`} colSpan={COLUMNS.length}>
                      {t("admin_empty")}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
        {payments.data ? (
          <div className="shrink-0 px-4 pb-3">
            <Pagination
              page={search.page}
              total={payments.data.total}
              onPage={(page) => update({ page })}
            />
          </div>
        ) : null}
      </section>
    </div>
  );
}
