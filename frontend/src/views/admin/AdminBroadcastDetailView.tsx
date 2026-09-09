import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { Modal } from "../../components/admin/Modal";
import {
  useBroadcast,
  useBroadcastAudience,
  useBroadcastDeliveries,
  useCancelBroadcast,
  useCan,
  useDeleteBroadcast,
  useScheduleBroadcast,
  useTestBroadcast,
} from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import {
  adminButton,
  adminCard,
  adminChip,
  adminDangerButton,
  adminLink,
  adminMuted,
  adminPrimaryButton,
  adminSelect,
  adminTable,
  adminTableScroll,
  adminTd,
  adminTh,
} from "../../lib/adminUi";
import { ApiError } from "../../lib/api";
import { BROADCAST_STATUS_LABEL, broadcastChipClass } from "../../lib/adminFormat";
import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES, type Lang } from "../../lib/i18n";

const route = getRouteApi("/admin/broadcasts/$broadcastId");
// Mirrors `broadcasts.EDITABLE` on the backend: a scheduled campaign has to be canceled
// before it can be edited, so the Edit link is not offered for it.
const EDITABLE = ["draft", "canceled", "failed"];

/** One broadcast: audience, actions (test, send, schedule, cancel) and the delivery log. */
export function AdminBroadcastDetailView() {
  const { t, formatDateTime, formatNumber } = useAdminT();
  const { broadcastId } = route.useParams();
  const navigate = useNavigate();
  const can = useCan();
  const broadcast = useBroadcast(broadcastId);
  const audience = useBroadcastAudience(broadcastId);
  const schedule = useScheduleBroadcast();
  const cancel = useCancelBroadcast();
  const remove = useDeleteBroadcast();
  const test = useTestBroadcast();
  const [language, setLanguage] = useState<Lang>("ru");
  const [startAt, setStartAt] = useState("");
  const [deliveryFilter, setDeliveryFilter] = useState("");
  // One dialog for the three irreversible actions; the value decides its copy and button.
  const [confirming, setConfirming] = useState<"send" | "cancel" | "delete" | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const deliveries = useBroadcastDeliveries(broadcastId, deliveryFilter);

  const fail = (reason: unknown) => {
    setNotice("");
    setError(reason instanceof ApiError ? reason.message : t("admin_error"));
  };
  const done = (message: string) => () => {
    setError("");
    setNotice(message);
  };

  if (broadcast.isPending) return <p className="text-muted">{t("admin_loading")}</p>;
  if (broadcast.isError || !broadcast.data)
    return <p className="text-danger">{t("admin_error")}</p>;

  const row = broadcast.data;
  const sendable =
    can("broadcasts.send") && ["draft", "scheduled", "canceled", "failed"].includes(row.status);

  return (
    <div className="grid gap-4">
      <header className="grid gap-2">
        <Link to="/admin/broadcasts" className={`${adminLink} text-[13px]`}>
          ← {t("admin_broadcast_back")}
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-[22px] font-[750] tracking-[-0.02em]">{row.title}</h1>
          <span className={`${adminChip} ${broadcastChipClass(row.status)}`}>
            {t(BROADCAST_STATUS_LABEL[row.status])}
          </span>
          <span className={adminChip}>
            {row.category === "marketing"
              ? t("admin_broadcast_category_marketing")
              : t("admin_broadcast_category_service")}
          </span>
        </div>
      </header>

      <section className={`${adminCard} grid gap-3`}>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Stat label={t("admin_broadcast_recipients")} value={formatNumber(row.totalRecipients)} />
          <Stat label={t("admin_broadcast_sent")} value={formatNumber(row.sentCount)} />
          <Stat label={t("admin_broadcast_pending")} value={formatNumber(row.pendingCount)} />
          <Stat label={t("admin_broadcast_blocked")} value={formatNumber(row.blockedCount)} />
          <Stat label={t("admin_broadcast_failed")} value={formatNumber(row.failedCount)} />
        </div>
        <p className={adminMuted}>
          {t("admin_broadcast_segment")}: {row.segmentName || "—"}
          {row.scheduledAt
            ? ` · ${t("admin_broadcast_scheduled_at")}: ${formatDateTime(row.scheduledAt)}`
            : ""}
          {row.finishedAt ? ` · ${formatDateTime(row.finishedAt)}` : ""}
        </p>
        {audience.data ? (
          <p className={adminMuted}>
            {t("admin_broadcast_audience")}: {formatNumber(audience.data.size)}
          </p>
        ) : null}
        {audience.isError ? (
          <p className="text-danger text-[13px]">
            {audience.error instanceof ApiError ? audience.error.message : t("admin_error")}
          </p>
        ) : null}

        <div className="border-line flex flex-wrap items-center gap-2 border-t pt-3">
          <select
            className={adminSelect}
            value={language}
            onChange={(event) => setLanguage(event.target.value as Lang)}
            aria-label={t("admin_broadcast_language")}
          >
            {SUPPORTED_LANGUAGES.map((code) => (
              <option key={code} value={code}>
                {LANGUAGE_NAMES[code]}
              </option>
            ))}
          </select>
          <button
            type="button"
            className={adminButton}
            disabled={test.isPending}
            onClick={() =>
              test.mutate(
                { broadcastId, language },
                { onError: fail, onSuccess: done(t("admin_broadcast_test_sent")) },
              )
            }
          >
            {t("admin_broadcast_test")}
          </button>

          {sendable ? (
            <>
              <button
                type="button"
                className={adminPrimaryButton}
                disabled={schedule.isPending}
                onClick={() => setConfirming("send")}
              >
                {t("admin_broadcast_send_now")}
              </button>
              <input
                className={adminSelect}
                type="datetime-local"
                value={startAt}
                onChange={(event) => setStartAt(event.target.value)}
                aria-label={t("admin_broadcast_scheduled_at")}
              />
              <button
                type="button"
                className={adminButton}
                disabled={!startAt || schedule.isPending}
                onClick={() =>
                  schedule.mutate(
                    // The input is local time; send it as an instant the backend reads as UTC.
                    { broadcastId, scheduledAt: new Date(startAt).toISOString() },
                    { onError: fail, onSuccess: done(t("admin_broadcast_status_scheduled")) },
                  )
                }
              >
                {t("admin_broadcast_schedule")}
              </button>
            </>
          ) : null}

          {can("broadcasts.send") && ["scheduled", "sending"].includes(row.status) ? (
            <button
              type="button"
              className={adminButton}
              disabled={cancel.isPending}
              onClick={() => setConfirming("cancel")}
            >
              {t("admin_broadcast_cancel")}
            </button>
          ) : null}

          {can("broadcasts.edit") && EDITABLE.includes(row.status) ? (
            <Link
              to="/admin/broadcasts/$broadcastId/edit"
              params={{ broadcastId }}
              className={adminButton}
            >
              {t("admin_edit")}
            </Link>
          ) : null}

          {can("broadcasts.edit") && row.status !== "sending" ? (
            <button
              type="button"
              className="text-soft hover:text-danger cursor-pointer text-[12px]"
              onClick={() => setConfirming("delete")}
            >
              {t("admin_broadcast_delete")}
            </button>
          ) : null}

          {notice ? <span className="text-gold text-[13px]">{notice}</span> : null}
          {error ? <span className="text-danger text-[13px]">{error}</span> : null}
        </div>
      </section>

      <Modal
        open={confirming !== null}
        title={
          confirming === "send"
            ? t("admin_broadcast_send_now")
            : confirming === "cancel"
              ? t("admin_broadcast_cancel")
              : t("admin_broadcast_delete")
        }
        onClose={() => setConfirming(null)}
        footer={
          <button
            type="button"
            className={confirming === "send" ? adminPrimaryButton : adminDangerButton}
            disabled={schedule.isPending || cancel.isPending || remove.isPending}
            onClick={() => {
              if (confirming === "send") {
                schedule.mutate(
                  { broadcastId, scheduledAt: null },
                  { onError: fail, onSuccess: done(t("admin_broadcast_status_scheduled")) },
                );
              } else if (confirming === "cancel") {
                cancel.mutate(broadcastId, {
                  onError: fail,
                  onSuccess: done(t("admin_broadcast_status_canceled")),
                });
              } else if (confirming === "delete") {
                remove.mutate(broadcastId, {
                  onError: fail,
                  onSuccess: () => navigate({ to: "/admin/broadcasts" }),
                });
              }
              setConfirming(null);
            }}
          >
            {confirming === "send"
              ? t("admin_broadcast_send_now")
              : confirming === "cancel"
                ? t("admin_broadcast_cancel")
                : t("admin_broadcast_delete")}
          </button>
        }
      >
        <p className="text-muted text-[13px]">
          {confirming === "send"
            ? t("admin_broadcast_send_confirm", { count: audience.data?.size ?? 0 })
            : confirming === "cancel"
              ? t("admin_broadcast_cancel_confirm")
              : t("admin_broadcast_delete_confirm")}
        </p>
      </Modal>

      <section className={`${adminCard} p-0`}>
        <div className="flex items-center justify-between gap-2 px-5 pt-4">
          <h2 className="text-[15px] font-[750]">{t("admin_broadcast_deliveries")}</h2>
          <select
            className={adminSelect}
            value={deliveryFilter}
            onChange={(event) => setDeliveryFilter(event.target.value)}
            aria-label={t("admin_col_status")}
          >
            <option value="">{t("admin_filter_all_statuses")}</option>
            <option value="pending">{t("admin_broadcast_pending")}</option>
            <option value="sent">{t("admin_broadcast_sent")}</option>
            <option value="blocked">{t("admin_broadcast_blocked")}</option>
            <option value="failed">{t("admin_broadcast_failed")}</option>
          </select>
        </div>
        {deliveries.data ? (
          <div className={`${adminTableScroll} mt-3`}>
            <table className={adminTable}>
              <thead>
                <tr>
                  <th className={adminTh}>{t("admin_col_user")}</th>
                  <th className={adminTh}>{t("admin_col_status")}</th>
                  <th className={adminTh}>{t("admin_col_date")}</th>
                  <th className={adminTh}>{t("admin_error")}</th>
                </tr>
              </thead>
              <tbody>
                {deliveries.data.map((delivery) => (
                  <tr key={delivery.userId}>
                    <td className={adminTd}>
                      <Link
                        to="/admin/users/$userId"
                        params={{ userId: String(delivery.userId) }}
                        className={adminLink}
                      >
                        {delivery.name || delivery.userId}
                      </Link>
                      <div className="text-soft text-[11px]">
                        {delivery.userId} · {delivery.language}
                      </div>
                    </td>
                    <td className={adminTd}>{delivery.status}</td>
                    <td className={`${adminTd} text-muted whitespace-nowrap`}>
                      {formatDateTime(delivery.sentAt)}
                    </td>
                    <td className={`${adminTd} text-soft`}>{delivery.error || "—"}</td>
                  </tr>
                ))}
                {deliveries.data.length === 0 ? (
                  <tr>
                    <td className={`${adminTd} text-soft text-center`} colSpan={4}>
                      {t("admin_empty")}
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

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-soft text-[11px] tracking-[0.08em] uppercase">{label}</p>
      <p className="text-[18px] font-[750] tabular-nums">{value}</p>
    </div>
  );
}
