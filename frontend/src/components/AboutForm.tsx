import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useUpdateProfile } from "../hooks/queries";
import { useT } from "../lib/i18n-context";
import type { TFunc, TranslationKey } from "../lib/i18n";
import { todayKey } from "../lib/life";
import { COUNTRIES, matchOption, type SelectOption } from "../lib/options";
import type { Profile } from "../lib/types";
import { field, fieldLabel, focusable, goldButton } from "../lib/ui";

/** Free-text answers feed a short prompt block, so they are capped well below an essay. */
const TEXT_LIMIT = 300;

function buildSchema(t: TFunc) {
  const max = (limit: number) => t("form_max_chars", { max: limit });
  return z.object({
    name: z.string().trim().min(1, t("form_name_required")).max(64, t("form_name_too_long")),
    birthDate: z
      .string()
      .refine((value) => !value || value <= todayKey(), t("form_birthdate_future")),
    location: z.string().trim().max(128, max(128)),
    activity: z.string().trim().max(256, max(256)),
    interests: z.string().trim().max(TEXT_LIMIT, max(TEXT_LIMIT)),
    mainGoal: z.string().trim().max(TEXT_LIMIT, max(TEXT_LIMIT)),
    currentProblem: z.string().trim().max(TEXT_LIMIT, max(TEXT_LIMIT)),
  });
}

type AboutValues = z.infer<ReturnType<typeof buildSchema>>;
type TextField = "interests" | "mainGoal" | "currentProblem";

const TEXT_FIELDS: { name: TextField; label: TranslationKey; placeholder: TranslationKey }[] = [
  { name: "interests", label: "memory_interests", placeholder: "form_interests_hint" },
  { name: "mainGoal", label: "memory_main_goal", placeholder: "form_goals_hint" },
  { name: "currentProblem", label: "memory_current_problem", placeholder: "form_problems_hint" },
];

function SelectChevron() {
  return (
    <svg
      className="text-muted pointer-events-none absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      aria-hidden="true"
    >
      <path d="M6 8l4 4 4-4" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function AboutForm({
  profile,
  onSaved,
}: {
  profile: Profile | undefined;
  onSaved: () => void;
}) {
  const { t, lang } = useT();
  const updateProfile = useUpdateProfile();
  const schema = useMemo(() => buildSchema(t), [t]);

  // Map the stored value onto the current-language option label so the matching
  // <option> stays selected; fall back to the raw value for legacy free text.
  const locationDefault =
    matchOption(COUNTRIES, profile?.location || profile?.country || "")?.labels[lang] ??
    (profile?.location || profile?.country || "");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AboutValues>({
    resolver: zodResolver(schema),
    mode: "onBlur",
    defaultValues: {
      name: profile?.name ?? "",
      birthDate: profile?.birthDate ?? "",
      location: locationDefault,
      activity: profile?.activity ?? "",
      interests: profile?.interests ?? "",
      mainGoal: profile?.mainGoal ?? "",
      currentProblem: profile?.currentProblem ?? "",
    },
  });

  // The three open questions are the slow part, so they start folded away.
  const hasContext = Boolean(profile?.interests || profile?.mainGoal || profile?.currentProblem);
  const [contextOpen, setContextOpen] = useState(hasContext);

  // zod .trim() already normalized the values before submission. An empty date
  // input means "leave the stored one alone": the life grid and the daily
  // notifications depend on it, so it is not cleared from here.
  const onSubmit = handleSubmit(async ({ birthDate, ...values }) => {
    await updateProfile.mutateAsync(birthDate ? { ...values, birthDate } : values);
    onSaved();
  });

  const textInput = `${field} aria-[invalid=true]:border-danger`;
  // Native arrow removed (appearance-none); a custom chevron is aligned to the
  // same right inset as the text, with pr-9 reserving room so it never overlaps.
  const selectInput = `${textInput} cursor-pointer appearance-none pr-9`;
  const textArea = `min-h-[74px] w-full resize-y rounded-[8px] border border-line bg-[rgba(0,0,0,0.24)] px-3 pt-3 text-[16px] leading-[1.42] text-text outline-none focus:border-gold aria-[invalid=true]:border-danger ${focusable}`;
  const errorText = "text-[12px] text-danger";
  const groupLabel = "text-muted text-[11px] font-[750] tracking-[0.12em] uppercase";

  // Placeholder + known options, plus the current value when it is legacy free
  // text that matches no option (so saving does not silently drop it).
  const renderOptions = (options: SelectOption[], current: string) => {
    const labels = options.map((option) => option.labels[lang]);
    return (
      <>
        <option value="">{t("form_not_specified")}</option>
        {current && !labels.includes(current) && <option value={current}>{current}</option>}
        {options.map((option) => (
          <option key={option.code} value={option.labels[lang]}>
            {option.labels[lang]}
          </option>
        ))}
      </>
    );
  };

  return (
    <form className="grid gap-4" onSubmit={onSubmit}>
      <p className="text-muted text-[13px] leading-[1.45]">{t("form_intro")}</p>

      <fieldset className="grid gap-3 border-0 p-0">
        <legend className={groupLabel}>{t("form_group_basics")}</legend>
        <label className={fieldLabel}>
          {t("memory_name")}
          <input {...register("name")} aria-invalid={!!errors.name} className={textInput} />
          {errors.name && <small className={errorText}>{errors.name.message}</small>}
        </label>
        <label className={fieldLabel}>
          {t("memory_birthdate")}
          <input
            type="date"
            max={todayKey()}
            {...register("birthDate")}
            aria-invalid={!!errors.birthDate}
            className={textInput}
          />
          {errors.birthDate && <small className={errorText}>{errors.birthDate.message}</small>}
        </label>
        <label className={fieldLabel}>
          {t("memory_location")}
          <div className="relative">
            <select
              {...register("location")}
              aria-invalid={!!errors.location}
              className={selectInput}
            >
              {renderOptions(COUNTRIES, locationDefault)}
            </select>
            <SelectChevron />
          </div>
          {errors.location && <small className={errorText}>{errors.location.message}</small>}
        </label>
        <label className={fieldLabel}>
          {t("memory_activity")}
          <input
            {...register("activity")}
            placeholder={t("form_activity_hint")}
            aria-invalid={!!errors.activity}
            className={textInput}
          />
          {errors.activity && <small className={errorText}>{errors.activity.message}</small>}
        </label>
      </fieldset>

      <fieldset className="grid gap-3 border-0 p-0">
        <legend className="sr-only">{t("form_group_context")}</legend>
        <button
          type="button"
          aria-expanded={contextOpen}
          onClick={() => setContextOpen(!contextOpen)}
          className="flex min-h-11 items-center justify-between gap-3 text-left"
        >
          <span className={groupLabel}>{t("form_group_context")}</span>
          <span className="text-muted text-[18px] leading-none" aria-hidden="true">
            {contextOpen ? "−" : "+"}
          </span>
        </button>

        {contextOpen &&
          TEXT_FIELDS.map((item) => (
            <label key={item.name} className={fieldLabel}>
              {t(item.label)}
              <textarea
                {...register(item.name)}
                rows={3}
                maxLength={TEXT_LIMIT}
                placeholder={t(item.placeholder)}
                aria-invalid={!!errors[item.name]}
                className={textArea}
              ></textarea>
              {errors[item.name] && (
                <small className={errorText}>{errors[item.name]?.message}</small>
              )}
            </label>
          ))}
      </fieldset>

      <button
        type="submit"
        disabled={isSubmitting}
        className={`${goldButton} min-h-[46px] font-extrabold disabled:opacity-60`}
      >
        {t("form_save")}
      </button>
    </form>
  );
}
