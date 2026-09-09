import { useState } from "react";

import { useSaveBroadcast, useSegments } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import type {
  Broadcast,
  BroadcastCategory,
  BroadcastMessage,
  BroadcastInput,
} from "../../lib/adminTypes";
import {
  adminCard,
  adminInput,
  adminMuted,
  adminPrimaryButton,
  adminSelect,
  adminTextarea,
} from "../../lib/adminUi";
import { ApiError } from "../../lib/api";
import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES } from "../../lib/i18n";

const EMPTY_MESSAGE: BroadcastMessage = { text: "", buttonText: "", buttonUrl: "" };

function contentOf(broadcast?: Broadcast): Record<string, BroadcastMessage> {
  const content: Record<string, BroadcastMessage> = {};
  for (const language of SUPPORTED_LANGUAGES) {
    content[language] = broadcast?.content[language] ?? { ...EMPTY_MESSAGE };
  }
  return content;
}

/**
 * Compose or edit one broadcast: an internal title, the audience, and the message per
 * language. A language left empty is simply not sent; recipients fall back to English.
 */
export function BroadcastComposer({
  broadcast,
  onSaved,
}: {
  broadcast?: Broadcast;
  onSaved?: (saved: Broadcast) => void;
}) {
  const { t } = useAdminT();
  const segments = useSegments();
  const save = useSaveBroadcast();
  const [title, setTitle] = useState(broadcast?.title ?? "");
  const [category, setCategory] = useState<BroadcastCategory>(broadcast?.category ?? "marketing");
  const [segmentId, setSegmentId] = useState(broadcast?.segmentId ?? "");
  const [markdown, setMarkdown] = useState(broadcast?.markdown ?? true);
  const [content, setContent] = useState(contentOf(broadcast));
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const patch = (language: string, field: keyof BroadcastMessage, value: string) =>
    setContent((previous) => ({
      ...previous,
      [language]: { ...previous[language], [field]: value },
    }));

  const submit = () => {
    setError("");
    setNotice("");
    const input: BroadcastInput = {
      title: title.trim(),
      category,
      segmentId: segmentId || null,
      filters: {},
      // Drop empty languages so the backend does not reject a half-filled form.
      content: Object.fromEntries(
        Object.entries(content).filter(([, message]) => message.text.trim()),
      ),
      markdown,
    };
    save.mutate(
      { broadcastId: broadcast?.id ?? null, input },
      {
        onError: (reason) =>
          setError(reason instanceof ApiError ? reason.message : t("admin_error")),
        onSuccess: (saved) => {
          setNotice(t("admin_broadcast_saved"));
          onSaved?.(saved as Broadcast);
        },
      },
    );
  };

  return (
    <section className={`${adminCard} grid gap-4`}>
      <h2 className="text-[15px] font-[750]">
        {broadcast ? broadcast.title : t("admin_broadcast_new")}
      </h2>

      <div className="flex flex-wrap gap-2">
        <input
          className={`${adminInput} w-[280px]`}
          placeholder={t("admin_broadcast_title")}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <select
          className={adminSelect}
          value={category}
          onChange={(event) => setCategory(event.target.value as BroadcastCategory)}
          aria-label={t("admin_broadcast_category")}
        >
          <option value="marketing">{t("admin_broadcast_category_marketing")}</option>
          <option value="service">{t("admin_broadcast_category_service")}</option>
        </select>
        <select
          className={adminSelect}
          value={segmentId}
          onChange={(event) => setSegmentId(event.target.value)}
          aria-label={t("admin_broadcast_segment")}
        >
          <option value="">{t("admin_broadcast_pick_segment")}</option>
          {(segments.data ?? []).map((segment) => (
            <option key={segment.id} value={segment.id}>
              {segment.name} ({segment.size})
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-[13px]">
          <input
            type="checkbox"
            className="accent-gold h-4 w-4"
            checked={markdown}
            onChange={(event) => setMarkdown(event.target.checked)}
          />
          {t("admin_broadcast_markdown")}
        </label>
      </div>
      <p className={adminMuted}>{t("admin_broadcast_category_hint")}</p>

      {SUPPORTED_LANGUAGES.map((language) => (
        <div key={language} className="border-line grid gap-2 border-t pt-3">
          <p className="text-[13px] font-[650]">{LANGUAGE_NAMES[language]}</p>
          <textarea
            className={adminTextarea}
            rows={4}
            placeholder={t("admin_broadcast_text")}
            value={content[language]?.text ?? ""}
            onChange={(event) => patch(language, "text", event.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <input
              className={`${adminInput} w-[220px]`}
              placeholder={t("admin_broadcast_button_text")}
              value={content[language]?.buttonText ?? ""}
              onChange={(event) => patch(language, "buttonText", event.target.value)}
            />
            <input
              className={`${adminInput} w-[320px]`}
              placeholder={t("admin_broadcast_button_url")}
              value={content[language]?.buttonUrl ?? ""}
              onChange={(event) => patch(language, "buttonUrl", event.target.value)}
            />
          </div>
        </div>
      ))}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className={adminPrimaryButton}
          disabled={!title.trim() || !segmentId || save.isPending}
          onClick={submit}
        >
          {t("admin_broadcast_save")}
        </button>
        {notice ? <span className="text-gold text-[13px]">{notice}</span> : null}
        {error ? <span className="text-danger text-[13px]">{error}</span> : null}
      </div>
    </section>
  );
}
