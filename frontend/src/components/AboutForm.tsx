import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useUpdateProfile } from "../hooks/queries";
import { useT } from "../lib/i18n-context";
import type { TFunc } from "../lib/i18n";
import { COUNTRIES, GENDERS, matchOption, type SelectOption } from "../lib/options";
import type { Profile } from "../lib/types";
import { field, fieldLabel, goldButton } from "../lib/ui";

function buildSchema(t: TFunc) {
  const max = (limit: number) => t("form_max_chars", { max: limit });
  return z.object({
    name: z.string().trim().min(1, t("form_name_required")).max(64, t("form_name_too_long")),
    gender: z.string().trim().max(32, max(32)),
    location: z.string().trim().max(128, max(128)),
    activity: z.string().trim().max(256, max(256)),
    interests: z.string().trim().max(2000, max(2000)),
    mainGoal: z.string().trim().max(2000, max(2000)),
    currentProblem: z.string().trim().max(2000, max(2000)),
  });
}

type AboutValues = z.infer<ReturnType<typeof buildSchema>>;

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

  // Map stored values onto the current-language option label so the matching
  // <option> stays selected; fall back to the raw value for legacy free text.
  const optionDefault = (options: SelectOption[], stored: string) =>
    matchOption(options, stored)?.labels[lang] ?? stored;
  const genderDefault = optionDefault(GENDERS, profile?.gender ?? "");
  const locationDefault = optionDefault(COUNTRIES, profile?.location || profile?.country || "");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AboutValues>({
    resolver: zodResolver(schema),
    mode: "onBlur",
    defaultValues: {
      name: profile?.name ?? "",
      gender: genderDefault,
      location: locationDefault,
      activity: profile?.activity ?? "",
      interests: profile?.interests ?? "",
      mainGoal: profile?.mainGoal ?? "",
      currentProblem: profile?.currentProblem ?? "",
    },
  });

  // zod .trim() already normalized the values before submission.
  const onSubmit = handleSubmit(async (values) => {
    await updateProfile.mutateAsync(values);
    onSaved();
  });

  const textInput = `${field} aria-[invalid=true]:border-danger`;
  // Native arrow removed (appearance-none); a custom chevron is aligned to the
  // same right inset as the text, with pr-9 reserving room so it never overlaps.
  const selectInput = `${textInput} cursor-pointer appearance-none pr-9`;
  const textArea =
    "min-h-[86px] w-full resize-y rounded-[14px] border border-line bg-[rgba(0,0,0,0.24)] px-3 pt-3 leading-[1.42] text-text outline-none aria-[invalid=true]:border-danger";
  const errorText = "text-[12px] text-danger";

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
    <form className="grid gap-3" onSubmit={onSubmit}>
      <label className={fieldLabel}>
        {t("form_name")}
        <input {...register("name")} aria-invalid={!!errors.name} className={textInput} />
        {errors.name && <small className={errorText}>{errors.name.message}</small>}
      </label>
      <label className={fieldLabel}>
        {t("form_gender")}
        <div className="relative">
          <select {...register("gender")} aria-invalid={!!errors.gender} className={selectInput}>
            {renderOptions(GENDERS, genderDefault)}
          </select>
          <SelectChevron />
        </div>
        {errors.gender && <small className={errorText}>{errors.gender.message}</small>}
      </label>
      <label className={fieldLabel}>
        {t("form_location")}
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
        {t("form_activity")}
        <input {...register("activity")} aria-invalid={!!errors.activity} className={textInput} />
        {errors.activity && <small className={errorText}>{errors.activity.message}</small>}
      </label>
      <label className={fieldLabel}>
        {t("form_interests")}
        <textarea
          {...register("interests")}
          aria-invalid={!!errors.interests}
          className={textArea}
        ></textarea>
        {errors.interests && <small className={errorText}>{errors.interests.message}</small>}
      </label>
      <label className={fieldLabel}>
        {t("form_goals")}
        <textarea
          {...register("mainGoal")}
          aria-invalid={!!errors.mainGoal}
          className={textArea}
        ></textarea>
        {errors.mainGoal && <small className={errorText}>{errors.mainGoal.message}</small>}
      </label>
      <label className={fieldLabel}>
        {t("form_problems")}
        <textarea
          {...register("currentProblem")}
          aria-invalid={!!errors.currentProblem}
          className={textArea}
        ></textarea>
        {errors.currentProblem && (
          <small className={errorText}>{errors.currentProblem.message}</small>
        )}
      </label>
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
