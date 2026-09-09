import { Link } from "@tanstack/react-router";
import { useState } from "react";

import { Modal } from "../../components/admin/Modal";
import { useCan, useDeleteSegment, useSegments } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import {
  adminChip,
  adminDangerButton,
  adminLink,
  adminPageFill,
  adminPrimaryButton,
  adminTable,
  adminTableCard,
  adminTableFill,
  adminTd,
  adminTh,
} from "../../lib/adminUi";
import { ApiError } from "../../lib/api";

/** Saved audiences. The definition itself is edited on its own screen. */
export function AdminSegmentsView() {
  const { t, formatNumber } = useAdminT();
  const can = useCan();
  const canEdit = can("segments.edit");
  const segments = useSegments();
  const remove = useDeleteSegment();
  const [error, setError] = useState("");
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);

  return (
    <div className={adminPageFill}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        {error ? <span className="text-danger text-[13px]">{error}</span> : <span />}
        {canEdit ? (
          <Link to="/admin/segments/new" className={`${adminPrimaryButton} leading-9`}>
            {t("admin_segments_new")}
          </Link>
        ) : null}
      </div>

      <section className={adminTableCard}>
        {segments.isPending ? <p className="text-muted p-5">{t("admin_loading")}</p> : null}
        {segments.isError ? <p className="text-danger p-5">{t("admin_error")}</p> : null}
        {segments.data ? (
          <div className={adminTableFill}>
            <table className={adminTable}>
              <thead>
                <tr>
                  <th className={adminTh}>{t("admin_segment_name")}</th>
                  <th className={adminTh}>{t("admin_segment_kind")}</th>
                  <th className={`${adminTh} text-right`}>{t("admin_segment_size")}</th>
                  <th className={adminTh} />
                </tr>
              </thead>
              <tbody>
                {segments.data.map((segment) => (
                  <tr key={segment.id} className="hover:bg-[rgba(255,255,255,0.02)]">
                    <td className={adminTd}>
                      <Link
                        to="/admin/segments/$segmentId"
                        params={{ segmentId: segment.id }}
                        className={adminLink}
                      >
                        {segment.name}
                      </Link>
                      <div className="text-soft text-[11px]">{segment.description || "—"}</div>
                    </td>
                    <td className={adminTd}>
                      <span className={adminChip}>
                        {segment.kind === "static"
                          ? t("admin_segment_kind_static")
                          : t("admin_segment_kind_dynamic")}
                      </span>
                    </td>
                    <td className={`${adminTd} text-right tabular-nums`}>
                      {formatNumber(segment.size)}
                    </td>
                    <td className={`${adminTd} text-right`}>
                      <button
                        type="button"
                        className="text-soft hover:text-danger cursor-pointer text-[12px] disabled:cursor-default disabled:opacity-40"
                        disabled={!canEdit}
                        onClick={() => setPendingDelete({ id: segment.id, name: segment.name })}
                      >
                        {t("admin_segment_delete")}
                      </button>
                    </td>
                  </tr>
                ))}
                {segments.data.length === 0 ? (
                  <tr>
                    <td className={`${adminTd} text-soft text-center`} colSpan={4}>
                      {t("admin_segment_empty")}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <Modal
        open={pendingDelete !== null}
        title={`${t("admin_segment_delete")}: ${pendingDelete?.name ?? ""}`}
        onClose={() => setPendingDelete(null)}
        footer={
          <button
            type="button"
            className={adminDangerButton}
            disabled={remove.isPending}
            onClick={() => {
              if (!pendingDelete) return;
              setError("");
              remove.mutate(pendingDelete.id, {
                onError: (reason) =>
                  setError(reason instanceof ApiError ? reason.message : t("admin_error")),
                onSettled: () => setPendingDelete(null),
              });
            }}
          >
            {t("admin_segment_delete")}
          </button>
        }
      >
        <p className="text-muted text-[13px]">{t("admin_segment_delete_confirm")}</p>
      </Modal>
    </div>
  );
}
