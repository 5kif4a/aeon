import { Link } from "@tanstack/react-router";

import { useBroadcasts, useCan } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { BROADCAST_STATUS_LABEL, broadcastChipClass } from "../../lib/adminFormat";
import {
  adminPageFill,
  adminTableCard,
  adminTableFill,
  adminChip,
  adminLink,
  adminPrimaryButton,
  adminTable,
  adminTd,
  adminTh,
} from "../../lib/adminUi";

/** Broadcast list plus the composer for a new one. Sending happens on the detail screen. */
export function AdminBroadcastsView() {
  const { t, formatDateTime, formatNumber } = useAdminT();
  const can = useCan();
  const broadcasts = useBroadcasts();

  return (
    <div className={adminPageFill}>
      <div className="flex justify-end">
        {can("broadcasts.edit") ? (
          <Link to="/admin/broadcasts/new" className={`${adminPrimaryButton} leading-9`}>
            {t("admin_broadcast_new")}
          </Link>
        ) : null}
      </div>

      <section className={adminTableCard}>
        {broadcasts.isPending ? <p className="text-muted p-5">{t("admin_loading")}</p> : null}
        {broadcasts.isError ? <p className="text-danger p-5">{t("admin_error")}</p> : null}
        {broadcasts.data ? (
          <div className={adminTableFill}>
            <table className={adminTable}>
              <thead>
                <tr>
                  <th className={adminTh}>{t("admin_col_title")}</th>
                  <th className={adminTh}>{t("admin_broadcast_category")}</th>
                  <th className={adminTh}>{t("admin_broadcast_segment")}</th>
                  <th className={adminTh}>{t("admin_col_status")}</th>
                  <th className={`${adminTh} text-right`}>{t("admin_broadcast_sent")}</th>
                  <th className={`${adminTh} text-right`}>{t("admin_broadcast_recipients")}</th>
                  <th className={adminTh}>{t("admin_col_created")}</th>
                </tr>
              </thead>
              <tbody>
                {broadcasts.data.map((broadcast) => (
                  <tr key={broadcast.id} className="hover:bg-[rgba(255,255,255,0.02)]">
                    <td className={adminTd}>
                      <Link
                        to="/admin/broadcasts/$broadcastId"
                        params={{ broadcastId: broadcast.id }}
                        className={adminLink}
                      >
                        {broadcast.title}
                      </Link>
                    </td>
                    <td className={adminTd}>
                      {broadcast.category === "marketing"
                        ? t("admin_broadcast_category_marketing")
                        : t("admin_broadcast_category_service")}
                    </td>
                    <td className={adminTd}>{broadcast.segmentName || "—"}</td>
                    <td className={adminTd}>
                      <span className={`${adminChip} ${broadcastChipClass(broadcast.status)}`}>
                        {t(BROADCAST_STATUS_LABEL[broadcast.status])}
                      </span>
                    </td>
                    <td className={`${adminTd} text-right tabular-nums`}>
                      {formatNumber(broadcast.sentCount)}
                    </td>
                    <td className={`${adminTd} text-right tabular-nums`}>
                      {formatNumber(broadcast.totalRecipients)}
                    </td>
                    <td className={`${adminTd} text-muted whitespace-nowrap`}>
                      {formatDateTime(broadcast.createdAt)}
                    </td>
                  </tr>
                ))}
                {broadcasts.data.length === 0 ? (
                  <tr>
                    <td className={`${adminTd} text-soft text-center`} colSpan={7}>
                      {t("admin_broadcast_empty")}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}
