import { useState } from "react";

import { AboutForm } from "../components/AboutForm";
import { Modal } from "../components/Modal";
import { ProfileSheet } from "../components/ProfileSheet";
import {
  useBillingStatus,
  useCancelSubscription,
  useCreateCheckout,
  useProfile,
  useStartTrial,
} from "../hooks/queries";
import { useT } from "../lib/i18n-context";
import {
  LANGUAGE_NAMES,
  LOCALES,
  SUPPORTED_LANGUAGES,
  type TFunc,
  type TranslationKey,
} from "../lib/i18n";
import { openInvoice } from "../lib/telegram";
import type { Profile } from "../lib/types";
import { goldButton } from "../lib/ui";

type SheetName = "about" | "language" | "pro" | null;

const PRO_FEATURES: TranslationKey[] = [
  "pro_feat_memory",
  "pro_feat_three_minds",
  "pro_feat_deep",
  "pro_feat_history",
  "pro_feat_voice",
];

const settingRow =
  "grid min-h-[60px] w-full grid-cols-[36px_1fr_auto_18px] items-center gap-3 border-b border-line px-3 text-left text-text last:border-b-0";
const settingIcon =
  "border-line bg-surface-strong text-gold-strong grid h-9 w-9 place-items-center rounded-[8px] border text-[12px] font-[800]";
const panelAction =
  "border-line bg-surface min-h-9 rounded-[8px] border px-3 text-[12px] font-[750] text-gold-strong";
const sheetOption =
  "border-line bg-surface min-h-[46px] w-full rounded-[8px] border font-[650] text-text";
const sheetPrimary = `${goldButton} min-h-[52px] w-full px-3 py-2 text-[14px] leading-[1.25] font-[800]`;
const sheetCopy = "text-muted text-[14px] leading-[1.5]";

export function ProfileView() {
  const { t, lang, setLang } = useT();
  const profileQuery = useProfile();
  const billingQuery = useBillingStatus();
  const profile = profileQuery.data;
  const billing = billingQuery.data;
  const startTrial = useStartTrial();
  const createCheckout = useCreateCheckout();
  const cancelSubscription = useCancelSubscription();
  const [sheet, setSheet] = useState<SheetName>(null);
  const [paymentState, setPaymentState] = useState<"paid" | "pending" | "failed" | null>(null);

  const completion = profile ? profileCompletion(profile) : 0;
  const plan = billing?.plan ?? profile?.plan ?? "Free";
  const profileName = profile?.name?.trim() || t("profile_anonymous");
  const profileInitial = Array.from(profileName)[0]?.toUpperCase() ?? "A";
  const closeSheet = () => setSheet(null);

  const beginCheckout = () => {
    setPaymentState(null);
    createCheckout.mutate(undefined, {
      onSuccess: async ({ invoiceLink }) => {
        const result = await openInvoice(invoiceLink);
        if (result === "paid") {
          setPaymentState("paid");
          await Promise.all([billingQuery.refetch(), profileQuery.refetch()]);
        } else if (result === "failed") {
          setPaymentState("failed");
        } else if (result === "pending") {
          setPaymentState("pending");
        }
      },
      onError: () => setPaymentState("failed"),
    });
  };

  return (
    <section className="animate-view-in block" aria-label={t("cabinet_title")}>
      <header className="flex min-h-[118px] items-center gap-3 pt-6">
        <span className="border-line bg-surface-strong text-gold-strong grid h-12 w-12 shrink-0 place-items-center rounded-[8px] border font-serif text-[22px]">
          {profileInitial}
        </span>
        <div className="min-w-0 flex-1">
          <span className="text-muted block text-[12px]">{t("profile_eyebrow")}</span>
          <h1 className="mt-0.5 truncate font-serif text-[26px] leading-tight">{profileName}</h1>
        </div>
        <button
          type="button"
          onClick={() => setSheet("pro")}
          className="border-line bg-surface text-gold-strong min-h-9 shrink-0 rounded-[8px] border px-3 text-[12px] font-[800]"
        >
          {planLabel(plan, t)}
        </button>
      </header>

      <section className="mt-2" aria-labelledby="settings-title">
        <h2
          id="settings-title"
          className="text-muted mb-2 text-[12px] font-[750] tracking-[0.12em] uppercase"
        >
          {t("profile_settings")}
        </h2>
        <div className="border-line bg-surface overflow-hidden rounded-[8px] border">
          <button type="button" className={settingRow} onClick={() => setSheet("language")}>
            <span className={settingIcon}>文</span>
            <strong className="text-[14px]">{t("language_label")}</strong>
            <em className="text-gold text-[13px] font-[750] not-italic">{LANGUAGE_NAMES[lang]}</em>
            <i className="text-muted text-[20px] not-italic">›</i>
          </button>
          <button type="button" className={settingRow} onClick={() => setSheet("pro")}>
            <span className={settingIcon}>★</span>
            <strong className="text-[14px]">{t("plan_label")}</strong>
            <em className="text-gold text-[13px] font-[750] not-italic">{planLabel(plan, t)}</em>
            <i className="text-muted text-[20px] not-italic">›</i>
          </button>
        </div>
      </section>

      <section className="mt-7" aria-labelledby="about-title">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <h2 id="about-title" className="font-serif text-[23px]">
              {t("about_title")}
            </h2>
            <p className="text-muted mt-1 text-[13px] leading-[1.4]">
              {t("profile_context_intro")}
            </p>
          </div>
          <button type="button" className={panelAction} onClick={() => setSheet("about")}>
            {t("about_edit")}
          </button>
        </div>

        <div className="mb-3">
          <div className="mb-2 flex items-center justify-between text-[12px]">
            <span className="text-muted">{t("profile_completion")}</span>
            <strong className="text-gold-strong">{completion}%</strong>
          </div>
          <div className="bg-surface-strong h-1.5 overflow-hidden rounded-full">
            <i
              className="bg-gold-strong block h-full rounded-full"
              style={{ width: `${completion}%` }}
            />
          </div>
        </div>

        <div className="border-line bg-surface overflow-hidden rounded-[8px] border">
          {memoryRows(profile).map(([labelKey, value]) => (
            <article
              key={labelKey}
              className="border-line grid min-h-[58px] grid-cols-[112px_1fr] items-center gap-3 border-b px-3 py-2 last:border-b-0 max-[390px]:grid-cols-[94px_1fr]"
            >
              <span className="text-muted text-[12px]">{t(labelKey)}</span>
              <div className="min-w-0 text-right">
                <strong className="text-text block text-[14px] leading-[1.35] break-words">
                  {value || t("not_specified")}
                </strong>
                {!value && <small className="text-gold text-[10px]">{t("memory_hint")}</small>}
              </div>
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
              <span className="text-muted text-[13px]">
                {t("sheet_current_plan", { plan: planLabel(plan, t) })}
              </span>
              <span className={panelAction}>{planLabel(plan, t)}</span>
            </div>
            <p className={sheetCopy}>{t("pro_desc")}</p>
            {billing && (
              <div className="border-line grid gap-2 border-y py-3 text-[13px]">
                <BillingRow
                  label={t("billing_daily_limit")}
                  value={`${billing.dailyRemaining}/${billing.dailyLimit}`}
                />
                {billing.plan === "Trial" && (
                  <BillingRow
                    label={t("billing_trial_total")}
                    value={`${billing.trialTotalLimit - billing.trialTotalUsed}/${billing.trialTotalLimit}`}
                  />
                )}
                {billing.councilLimit > 0 && (
                  <BillingRow
                    label={t("billing_council_left")}
                    value={String(billing.councilRemaining)}
                  />
                )}
                {(billing.trialExpiresAt || billing.proExpiresAt) && (
                  <BillingRow
                    label={t("billing_active_until")}
                    value={formatDate(
                      billing.proExpiresAt ?? billing.trialExpiresAt,
                      LOCALES[lang],
                    )}
                  />
                )}
              </div>
            )}
            <ul className="grid list-none gap-2 p-0">
              {PRO_FEATURES.map((key) => (
                <li
                  key={key}
                  className="grid grid-cols-[18px_1fr] gap-2 text-[14px] leading-[1.4] text-[#d7cebf]"
                >
                  <span className="text-success">✓</span>
                  {t(key)}
                </li>
              ))}
            </ul>
            {billing?.canStartTrial && (
              <button
                type="button"
                className={sheetOption}
                disabled={startTrial.isPending}
                onClick={() => startTrial.mutate()}
              >
                {t("trial_start")}
              </button>
            )}
            {plan !== "Pro" && (
              <button
                type="button"
                className={sheetPrimary}
                disabled={createCheckout.isPending}
                onClick={beginCheckout}
              >
                {t("pro_upgrade", { price: billing?.proPriceStars ?? 299 })}
              </button>
            )}
            {plan === "Pro" && billing?.proAutoRenew && (
              <button
                type="button"
                className={sheetOption}
                disabled={cancelSubscription.isPending}
                onClick={() => cancelSubscription.mutate()}
              >
                {t("pro_cancel")}
              </button>
            )}
            {paymentState && <p className={sheetCopy}>{t(paymentMessageKey(paymentState))}</p>}
          </div>
        </Modal>
      )}
    </section>
  );
}

function BillingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted">{label}</span>
      <strong className="text-right">{value}</strong>
    </div>
  );
}

function planLabel(plan: string, t: TFunc): string {
  if (plan === "Pro") return t("plan_pro");
  if (plan === "Trial") return t("plan_trial");
  return t("plan_free");
}

function paymentMessageKey(state: "paid" | "pending" | "failed"): TranslationKey {
  if (state === "paid") return "payment_paid";
  if (state === "pending") return "payment_pending";
  return "payment_failed";
}

function formatDate(value: string | null, locale: string): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
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
