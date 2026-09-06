import { useState } from "react";

import {
  usePromptPreview,
  useResetSetting,
  useSaveSetting,
  useAdminSettings,
} from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { agentLabel } from "../../lib/adminFormat";
import type { AdminSetting, AdminSettingValue } from "../../lib/adminTypes";
import {
  adminButton,
  adminCard,
  adminChip,
  adminInput,
  adminMuted,
  adminPrimaryButton,
  adminSelect,
  adminTextarea,
} from "../../lib/adminUi";
import { AGENT_IDS, DEFAULT_AGENT_ID } from "../../lib/agents";
import { ApiError } from "../../lib/api";
import {
  LANGUAGE_NAMES,
  SUPPORTED_LANGUAGES,
  type Lang,
  type TranslationKey,
} from "../../lib/i18n";

const AGENT_PROMPT_PREFIX = "agent_prompt.";
const SETTING_LABELS: Record<string, TranslationKey> = {
  response_style: "admin_setting_response_style",
  temperature: "admin_setting_temperature",
  history_turns: "admin_setting_history_turns",
  max_output_tokens: "admin_setting_max_output_tokens",
};

type Notice = { key: string; kind: "saved" | "error"; detail?: string };

function effectiveValue(setting: AdminSetting): AdminSettingValue {
  return setting.value ?? setting.default;
}

/** Turns the raw input into a value the API accepts, or null when it is invalid. */
function parseDraft(setting: AdminSetting, raw: string): AdminSettingValue | null {
  if (setting.kind === "text") return raw.trim() ? raw : null;
  if (!raw.trim()) return null;
  const number = Number(raw);
  if (!Number.isFinite(number)) return null;
  if (setting.kind === "int" && !Number.isInteger(number)) return null;
  if (setting.min !== null && number < setting.min) return null;
  if (setting.max !== null && number > setting.max) return null;
  return number;
}

function errorDetail(error: unknown): string {
  return error instanceof ApiError ? error.message : String(error);
}

export function AdminSettingsView() {
  const { t, lang } = useAdminT();
  const settings = useAdminSettings();
  const save = useSaveSetting();
  const reset = useResetSetting();
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState<Notice | null>(null);

  const label = (setting: AdminSetting) => {
    if (setting.key.startsWith(AGENT_PROMPT_PREFIX)) {
      const agentId = setting.key.slice(AGENT_PROMPT_PREFIX.length);
      return t("admin_setting_agent_prompt", { agent: agentLabel(agentId, lang) });
    }
    const key = SETTING_LABELS[setting.key];
    return key ? t(key) : setting.key;
  };

  const draftOf = (setting: AdminSetting) => drafts[setting.key] ?? String(effectiveValue(setting));
  const isDirty = (setting: AdminSetting) =>
    setting.key in drafts && drafts[setting.key] !== String(effectiveValue(setting));

  const clearDraft = (key: string) =>
    setDrafts((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });

  const onSave = (setting: AdminSetting) => {
    const value = parseDraft(setting, draftOf(setting));
    if (value === null) return;
    save.mutate(
      { key: setting.key, value },
      {
        onSuccess: () => {
          clearDraft(setting.key);
          setNotice({ key: setting.key, kind: "saved" });
        },
        onError: (error) =>
          setNotice({ key: setting.key, kind: "error", detail: errorDetail(error) }),
      },
    );
  };

  const onReset = (setting: AdminSetting) => {
    reset.mutate(setting.key, {
      onSuccess: () => {
        clearDraft(setting.key);
        setNotice({ key: setting.key, kind: "saved" });
      },
      onError: (error) =>
        setNotice({ key: setting.key, kind: "error", detail: errorDetail(error) }),
    });
  };

  if (settings.isPending) return <p className="text-muted">{t("admin_loading")}</p>;
  if (settings.isError || !settings.data) return <p className="text-danger">{t("admin_error")}</p>;

  const items = settings.data;
  const prompts = items.filter((setting) => setting.kind === "text");
  const generation = items.filter((setting) => setting.kind !== "text");

  // Unsaved, valid drafts are what the preview runs against.
  const dirtyOverrides: Record<string, AdminSettingValue> = {};
  for (const setting of items) {
    if (!isDirty(setting)) continue;
    const value = parseDraft(setting, draftOf(setting));
    if (value !== null) dirtyOverrides[setting.key] = value;
  }

  const renderCard = (setting: AdminSetting) => (
    <SettingCard
      key={setting.key}
      setting={setting}
      title={label(setting)}
      draft={draftOf(setting)}
      dirty={isDirty(setting)}
      valid={parseDraft(setting, draftOf(setting)) !== null}
      busy={
        (save.isPending && save.variables?.key === setting.key) ||
        (reset.isPending && reset.variables === setting.key)
      }
      notice={notice?.key === setting.key ? notice : null}
      onChange={(raw) => setDrafts((current) => ({ ...current, [setting.key]: raw }))}
      onDiscard={() => clearDraft(setting.key)}
      onSave={() => onSave(setting)}
      onReset={() => onReset(setting)}
    />
  );

  return (
    <div className="grid gap-4">
      <header>
        <h1 className="text-[22px] font-[750] tracking-[-0.02em]">{t("admin_nav_settings")}</h1>
        <p className={adminMuted}>{t("admin_settings_intro")}</p>
      </header>
      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_400px]">
        <div className="grid gap-6">
          <section className="grid gap-3">
            <h2 className="text-soft text-[11px] font-[700] tracking-[0.08em] uppercase">
              {t("admin_settings_group_generation")}
            </h2>
            <div className="grid gap-3 md:grid-cols-3">{generation.map(renderCard)}</div>
          </section>
          <section className="grid gap-3">
            <h2 className="text-soft text-[11px] font-[700] tracking-[0.08em] uppercase">
              {t("admin_settings_group_prompts")}
            </h2>
            {prompts.map(renderCard)}
          </section>
        </div>
        <PreviewPanel overrides={dirtyOverrides} />
      </div>
    </div>
  );
}

function SettingCard({
  setting,
  title,
  draft,
  dirty,
  valid,
  busy,
  notice,
  onChange,
  onDiscard,
  onSave,
  onReset,
}: {
  setting: AdminSetting;
  title: string;
  draft: string;
  dirty: boolean;
  valid: boolean;
  busy: boolean;
  notice: Notice | null;
  onChange: (raw: string) => void;
  onDiscard: () => void;
  onSave: () => void;
  onReset: () => void;
}) {
  const { t, formatDateTime } = useAdminT();
  const overridden = setting.value !== null;
  const inputId = `setting-${setting.key}`;
  const isText = setting.kind === "text";

  return (
    <article className={`${adminCard} grid gap-3`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <label htmlFor={inputId} className="text-[14px] font-[700]">
            {title}
          </label>
          <p className={adminMuted}>{setting.description}</p>
        </div>
        <span className={`${adminChip} ${overridden ? "border-gold text-gold" : "text-muted"}`}>
          {overridden ? t("admin_setting_overridden") : t("admin_setting_default_label")}
        </span>
      </div>
      {isText ? (
        <textarea
          id={inputId}
          className={adminTextarea}
          rows={setting.key.startsWith(AGENT_PROMPT_PREFIX) ? 14 : 8}
          value={draft}
          onChange={(event) => onChange(event.target.value)}
          spellCheck={false}
        />
      ) : (
        <div className="flex items-center gap-3">
          <input
            id={inputId}
            type="number"
            className={`${adminInput} w-32`}
            value={draft}
            min={setting.min ?? undefined}
            max={setting.max ?? undefined}
            step={setting.kind === "float" ? 0.05 : 1}
            onChange={(event) => onChange(event.target.value)}
          />
          {setting.min !== null && setting.max !== null ? (
            <span className={adminMuted}>
              {t("admin_setting_bounds", { min: setting.min, max: setting.max })}
            </span>
          ) : null}
        </div>
      )}
      {overridden ? (
        <details>
          <summary className="text-muted hover:text-text cursor-pointer text-[12px]">
            {t("admin_setting_show_default")}
          </summary>
          <pre className="text-muted mt-2 max-h-72 overflow-auto rounded-[8px] bg-[rgba(0,0,0,0.24)] p-3 text-[12px] leading-relaxed whitespace-pre-wrap">
            {String(setting.default)}
          </pre>
        </details>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className={adminPrimaryButton}
          disabled={!dirty || !valid || busy}
          onClick={onSave}
        >
          {t("admin_setting_save")}
        </button>
        {dirty ? (
          <button type="button" className={adminButton} disabled={busy} onClick={onDiscard}>
            {t("admin_setting_discard")}
          </button>
        ) : null}
        {overridden ? (
          <button type="button" className={adminButton} disabled={busy} onClick={onReset}>
            {t("admin_setting_reset")}
          </button>
        ) : null}
        {dirty && !valid ? (
          <span className="text-danger text-[12px]">{t("admin_setting_invalid")}</span>
        ) : null}
        {notice?.kind === "saved" && !dirty ? (
          <span className="text-success text-[12px]">{t("admin_setting_saved")}</span>
        ) : null}
        {notice?.kind === "error" ? (
          <span className="text-danger text-[12px]">{notice.detail ?? t("admin_error")}</span>
        ) : null}
      </div>
      {setting.updatedAt ? (
        <p className="text-soft text-[11px]">
          {t("admin_setting_updated", {
            date: formatDateTime(setting.updatedAt),
            admin: setting.updatedBy ?? "—",
          })}
        </p>
      ) : null}
    </article>
  );
}

function PreviewPanel({ overrides }: { overrides: Record<string, AdminSettingValue> }) {
  const { t, lang } = useAdminT();
  const preview = usePromptPreview();
  const [agentId, setAgentId] = useState(DEFAULT_AGENT_ID);
  const [language, setLanguage] = useState<Lang>(lang);
  const [message, setMessage] = useState("");
  const draftCount = Object.keys(overrides).length;

  return (
    <aside className={`${adminCard} grid gap-3 xl:sticky xl:top-6`}>
      <div>
        <h2 className="text-[14px] font-[700]">{t("admin_preview_title")}</h2>
        <p className={adminMuted}>{t("admin_preview_intro")}</p>
      </div>
      <form
        className="grid gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (!message.trim()) return;
          preview.mutate({ agentId, language, message: message.trim(), overrides });
        }}
      >
        <div className="grid grid-cols-2 gap-2">
          <label className="grid gap-1 text-[12px]">
            <span className="text-muted">{t("admin_preview_agent")}</span>
            <select
              className={adminSelect}
              value={agentId}
              onChange={(event) => setAgentId(event.target.value)}
            >
              {AGENT_IDS.map((id) => (
                <option key={id} value={id}>
                  {agentLabel(id, lang)}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-[12px]">
            <span className="text-muted">{t("admin_preview_language")}</span>
            <select
              className={adminSelect}
              value={language}
              onChange={(event) => setLanguage(event.target.value as Lang)}
            >
              {SUPPORTED_LANGUAGES.map((code) => (
                <option key={code} value={code}>
                  {LANGUAGE_NAMES[code]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="grid gap-1 text-[12px]">
          <span className="text-muted">{t("admin_preview_message")}</span>
          <textarea
            className={adminTextarea}
            rows={4}
            value={message}
            placeholder={t("admin_preview_message_placeholder")}
            onChange={(event) => setMessage(event.target.value)}
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            className={adminPrimaryButton}
            disabled={preview.isPending || !message.trim()}
          >
            {preview.isPending ? t("admin_preview_running") : t("admin_preview_run")}
          </button>
          <span className={adminMuted}>{t("admin_preview_drafts", { count: draftCount })}</span>
        </div>
      </form>
      {preview.isError ? (
        <p className="text-danger text-[12px]">
          {t("admin_preview_failed", { detail: errorDetail(preview.error) })}
        </p>
      ) : null}
      {preview.data ? (
        <div className="grid gap-1">
          <span className="text-soft text-[11px] font-[700] tracking-[0.08em] uppercase">
            {t("admin_preview_result")}
          </span>
          <div className="text-text max-h-[60vh] overflow-auto rounded-[8px] bg-[rgba(0,0,0,0.24)] p-3 text-[13px] leading-relaxed whitespace-pre-wrap">
            {preview.data.text}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
