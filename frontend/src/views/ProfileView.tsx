import { useState } from "react";

import { AboutForm } from "../components/AboutForm";
import { Modal } from "../components/Modal";
import { ProfileSheet } from "../components/ProfileSheet";
import { useProfile, useUpdateProfile } from "../hooks/queries";
import { useT } from "../lib/i18n-context";
import { LANGUAGE_NAMES, SUPPORTED_LANGUAGES, type TranslationKey } from "../lib/i18n";
import type { Profile } from "../lib/types";
import { cardPanel, goldButton } from "../lib/ui";

type SheetName = "about" | "language" | "pro" | null;

const PRO_FEATURES: TranslationKey[] = [
  "pro_feat_memory",
  "pro_feat_three_minds",
  "pro_feat_deep",
  "pro_feat_history",
  "pro_feat_voice",
];

/** Verified badge next to the assistant name. */
const badge =
  "inline-grid h-[17px] w-[17px] place-items-center rounded-[6px] bg-[linear-gradient(135deg,#dcc09a,#8a6544)] text-[11px] text-[#1b1410]";
/** Row inside the grouped settings card. */
const settingRow =
  "grid w-full min-h-[58px] grid-cols-[34px_1fr_auto_18px] items-center gap-[10px] border-b border-line px-[14px] text-left text-text cursor-pointer last:border-b-0";
const settingIcon =
  "grid h-[34px] w-[34px] place-items-center rounded-[12px] bg-[rgba(225,195,150,0.1)] text-gold-strong";
/** Small pill/action in a panel title bar. */
const panelAction =
  "rounded-[12px] bg-[rgba(225,195,150,0.11)] px-[10px] py-2 text-[13px] font-[750] text-gold-strong cursor-pointer";
/** Neutral full-width option button inside a sheet. */
const sheetOption =
  "min-h-[46px] w-full rounded-[14px] bg-[rgba(255,255,255,0.06)] font-[650] text-text cursor-pointer";
const sheetPrimary = `${goldButton} min-h-[46px] w-full font-extrabold`;
const sheetCopy = "text-[#d7cebf] leading-[1.45]";

export function ProfileView() {
  const { t, lang, setLang } = useT();
  const { data: profile } = useProfile();
  const updateProfile = useUpdateProfile();
  const [sheet, setSheet] = useState<SheetName>(null);

  const completion = profile ? profileCompletion(profile) : 0;
  const plan = profile?.plan ?? "Basic";
  const closeSheet = () => setSheet(null);

  return (
    <section className="block animate-view-in" aria-label={t("cabinet_title")}>
      <header className="flex min-h-[98px] items-center justify-between pt-[22px]">
        <div>
          <h2 className="flex items-center gap-[7px] text-[23px]">
            Marcus Aurelius <span className={badge}>✓</span>
          </h2>
          <p className="mt-1 text-[13px] text-muted">{t("cabinet_title")}</p>
        </div>
      </header>

      <section className="mt-2 overflow-hidden rounded-[18px] border border-line bg-[linear-gradient(180deg,rgba(29,28,27,0.96),rgba(18,17,16,0.96))]">
        <button type="button" className={settingRow} onClick={() => setSheet("language")}>
          <span className={settingIcon}>◐</span>
          <strong>{t("language_label")}</strong>
          <em className="not-italic font-[750] text-gold">{LANGUAGE_NAMES[lang]}</em>
          <i className="not-italic text-[22px] text-muted">›</i>
        </button>
        <button type="button" className={settingRow} onClick={() => setSheet("pro")}>
          <span className={settingIcon}>♜</span>
          <strong>{t("plan_label")}</strong>
          <em className="not-italic font-[750] text-gold">{plan}</em>
          <i className="not-italic text-[22px] text-muted">›</i>
        </button>
      </section>

      <section className={`${cardPanel} mt-3 p-4`}>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h3 className="font-serif text-[21px]">{t("about_title")}</h3>
          <button type="button" className={panelAction} onClick={() => setSheet("about")}>
            {t("about_edit")}
          </button>
        </div>
        <div className="mb-[14px] rounded-[16px] border border-[rgba(255,255,255,0.06)] bg-[rgba(0,0,0,0.24)] p-3">
          <div className="mb-[10px] flex items-center justify-between">
            <span className="text-[13px] text-muted">{t("profile_completion")}</span>
            <strong className="text-gold-strong">{completion}%</strong>
          </div>
          <div className="h-[9px] overflow-hidden rounded-full bg-[#252525]">
            <i
              className="block h-full rounded-[inherit] bg-[linear-gradient(90deg,#8a6544,#e1c396)]"
              style={{ width: `${completion}%` }}
            ></i>
          </div>
        </div>
        <div className="grid gap-4">
          {memoryRows(profile).map(([labelKey, value]) => (
            <article key={labelKey} className="grid gap-[2px]">
              <span className="text-[12px] text-muted">{t(labelKey)}</span>
              <strong className="text-[16px] leading-[1.28] text-text">
                {value || t("not_specified")}
              </strong>
              {!value && <small className="text-[12px] text-gold">{t("memory_hint")}</small>}
            </article>
          ))}
        </div>
      </section>

      {sheet === "about" && (
        <ProfileSheet title={t("about_title")} onClose={closeSheet}>
          <AboutForm profile={profile} onSaved={closeSheet} />
        </ProfileSheet>
      )}
      {sheet === "language" && (
        <ProfileSheet title={t("sheet_language_title")} onClose={closeSheet}>
          <div className="grid gap-3">
            <p className={sheetCopy}>{t("sheet_language_choose")}</p>
            {SUPPORTED_LANGUAGES.map((code) => (
              <button
                key={code}
                className={code === lang ? sheetPrimary : sheetOption}
                type="button"
                onClick={() => {
                  setLang(code);
                  closeSheet();
                }}
              >
                {LANGUAGE_NAMES[code]}
              </button>
            ))}
          </div>
        </ProfileSheet>
      )}
      {sheet === "pro" && (
        <Modal title={t("pro_title")} onClose={closeSheet}>
          <div className="grid gap-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[13px] text-muted">{t("sheet_current_plan", { plan })}</span>
              <span className={panelAction}>{plan}</span>
            </div>
            <p className={sheetCopy}>{t("pro_desc")}</p>
            <ul className="grid list-none gap-2 p-0">
              {PRO_FEATURES.map((key) => (
                <li
                  key={key}
                  className="text-[#d7cebf] before:mr-2 before:text-gold before:content-['✦']"
                >
                  {t(key)}
                </li>
              ))}
            </ul>
            <button
              type="button"
              className={sheetPrimary}
              disabled={updateProfile.isPending}
              onClick={() => updateProfile.mutate({ plan: "Pro" }, { onSuccess: closeSheet })}
            >
              {t("pro_upgrade")}
            </button>
          </div>
        </Modal>
      )}
    </section>
  );
}

function profileCompletion(profile: Profile): number {
  const fields = [
    profile.name,
    profile.gender,
    profile.age != null ? String(profile.age) : "",
    profile.birthDate ?? "",
    profile.location || profile.country,
    profile.activity,
    profile.interests,
    profile.mainGoal,
    profile.currentProblem,
  ];
  const filled = fields.filter(Boolean).length;
  return Math.round((filled / fields.length) * 100);
}

function memoryRows(profile: Profile | undefined): [TranslationKey, string][] {
  return [
    ["memory_name", profile?.name ?? ""],
    ["memory_gender", profile?.gender ?? ""],
    ["memory_age", profile?.age != null ? String(profile.age) : ""],
    ["memory_birthdate", profile?.birthDate ?? ""],
    ["memory_location", profile?.location || profile?.country || ""],
    ["memory_activity", profile?.activity ?? ""],
    ["memory_interests", profile?.interests ?? ""],
    ["memory_main_goal", profile?.mainGoal ?? ""],
    ["memory_current_problem", profile?.currentProblem ?? ""],
  ];
}
