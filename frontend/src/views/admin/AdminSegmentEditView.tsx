import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import { SegmentFilterEditor } from "../../components/admin/SegmentFilterEditor";
import {
  useCan,
  useSaveSegment,
  useSegment,
  useSegmentFilters,
  useSegmentPreview,
} from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import type { Segment, SegmentFilters, SegmentKind } from "../../lib/adminTypes";
import {
  adminButton,
  adminCard,
  adminChip,
  adminInput,
  adminLink,
  adminMuted,
  adminPrimaryButton,
  adminSelect,
  adminTextarea,
} from "../../lib/adminUi";
import { ApiError } from "../../lib/api";

const route = getRouteApi("/admin/segments/$segmentId");

interface Draft {
  name: string;
  description: string;
  kind: SegmentKind;
  filters: SegmentFilters;
  ids: string;
}

const EMPTY: Draft = { name: "", description: "", kind: "dynamic", filters: {}, ids: "" };

function toDraft(segment: Segment): Draft {
  return {
    name: segment.name,
    description: segment.description,
    kind: segment.kind,
    filters: segment.filters,
    ids: segment.userIds.join(", "),
  };
}

function parseIds(raw: string): number[] {
  return raw
    .split(/[\s,;]+/)
    .map((item) => Number(item.trim()))
    .filter((id) => Number.isFinite(id) && id > 0);
}

/** `/admin/segments/new`: an empty audience definition. */
export function AdminSegmentNewView() {
  return <SegmentForm segmentId={null} draft={EMPTY} />;
}

/** `/admin/segments/$segmentId`: the same form, seeded with the saved definition. */
export function AdminSegmentEditView() {
  const { t } = useAdminT();
  const { segmentId } = route.useParams();
  const segment = useSegment(segmentId);

  if (segment.isPending) return <p className="text-muted">{t("admin_loading")}</p>;
  if (segment.isError || !segment.data) return <p className="text-danger">{t("admin_error")}</p>;
  // `key` remounts the form when another segment is opened, so the draft starts fresh.
  return <SegmentForm key={segmentId} segmentId={segmentId} draft={toDraft(segment.data)} />;
}

function SegmentForm({ segmentId, draft: initial }: { segmentId: string | null; draft: Draft }) {
  const { t, formatNumber } = useAdminT();
  const navigate = useNavigate();
  const can = useCan();
  const canEdit = can("segments.edit");
  const specs = useSegmentFilters();
  const save = useSaveSegment();
  const preview = useSegmentPreview();
  const [draft, setDraft] = useState<Draft>(initial);
  const [error, setError] = useState("");

  const input = () => ({
    name: draft.name.trim(),
    description: draft.description.trim(),
    kind: draft.kind,
    filters: draft.kind === "dynamic" ? draft.filters : {},
    userIds: draft.kind === "static" ? parseIds(draft.ids) : [],
  });

  const fail = (reason: unknown) =>
    setError(reason instanceof ApiError ? reason.message : t("admin_error"));

  return (
    <div className="grid gap-4">
      <Link to="/admin/segments" className={`${adminLink} text-[13px]`}>
        ← {t("admin_nav_segments")}
      </Link>

      <section className={`${adminCard} grid gap-4`}>
        <h2 className="text-[15px] font-[750]">
          {segmentId ? t("admin_segment_edit") : t("admin_segments_new")}
        </h2>

        <div className="flex flex-wrap gap-2">
          <input
            className={`${adminInput} w-[260px]`}
            placeholder={t("admin_segment_name")}
            value={draft.name}
            onChange={(event) => setDraft({ ...draft, name: event.target.value })}
          />
          <select
            className={adminSelect}
            value={draft.kind}
            onChange={(event) => setDraft({ ...draft, kind: event.target.value as SegmentKind })}
            aria-label={t("admin_segment_kind")}
          >
            <option value="dynamic">{t("admin_segment_kind_dynamic")}</option>
            <option value="static">{t("admin_segment_kind_static")}</option>
          </select>
        </div>
        <textarea
          className={adminTextarea}
          rows={2}
          placeholder={t("admin_segment_description")}
          value={draft.description}
          onChange={(event) => setDraft({ ...draft, description: event.target.value })}
        />

        {draft.kind === "dynamic" ? (
          specs.data ? (
            <SegmentFilterEditor
              specs={specs.data}
              value={draft.filters}
              onChange={(filters) => setDraft({ ...draft, filters })}
            />
          ) : (
            <p className="text-muted text-[13px]">{t("admin_loading")}</p>
          )
        ) : (
          <div className="grid gap-1">
            <textarea
              className={adminTextarea}
              rows={4}
              placeholder={t("admin_segment_ids")}
              value={draft.ids}
              onChange={(event) => setDraft({ ...draft, ids: event.target.value })}
            />
            <p className={adminMuted}>{t("admin_segment_ids_hint")}</p>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className={adminButton}
            disabled={preview.isPending}
            onClick={() => {
              setError("");
              preview.mutate(
                { kind: draft.kind, filters: input().filters, userIds: input().userIds },
                { onError: fail },
              );
            }}
          >
            {t("admin_segment_preview_run")}
          </button>
          <button
            type="button"
            className={adminPrimaryButton}
            disabled={!canEdit || !draft.name.trim() || save.isPending}
            onClick={() => {
              setError("");
              save.mutate(
                { segmentId, input: input() },
                { onError: fail, onSuccess: () => navigate({ to: "/admin/segments" }) },
              );
            }}
          >
            {t("admin_segment_save")}
          </button>
          {error ? <span className="text-danger text-[13px]">{error}</span> : null}
        </div>

        {preview.data ? (
          <div className="border-line grid gap-2 border-t pt-3">
            <p className="text-[14px] font-[750]">
              {t("admin_segment_preview")}: {formatNumber(preview.data.size)}
            </p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(preview.data.byLanguage).map(([language, count]) => (
                <span key={language} className={adminChip}>
                  {language || "—"}: {formatNumber(count)}
                </span>
              ))}
            </div>
            {preview.data.sample.length ? (
              <p className={adminMuted}>
                {t("admin_segment_sample")}:{" "}
                {preview.data.sample
                  .map((user) => `${user.name || user.id} (${user.plan})`)
                  .join(", ")}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
