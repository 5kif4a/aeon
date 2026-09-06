/** Route-level vocabulary shared by the router, the shell, and the views. */

export type ViewName = "home" | "calendar" | "profile";

export const VIEW_PATHS = {
  home: "/",
  calendar: "/calendar",
  profile: "/profile",
} as const satisfies Record<ViewName, string>;

export const PRACTICE_TABS = ["life", "goal", "diary"] as const;
export type PracticeTab = (typeof PRACTICE_TABS)[number];

export const PROFILE_SHEETS = ["about", "language", "notifications", "pro"] as const;
export type ProfileSheet = (typeof PROFILE_SHEETS)[number];

export function viewFromPathname(pathname: string): ViewName {
  if (pathname.startsWith(VIEW_PATHS.calendar)) return "calendar";
  if (pathname.startsWith(VIEW_PATHS.profile)) return "profile";
  return "home";
}

function pick<T extends string>(allowed: readonly T[], value: unknown): T | undefined {
  return typeof value === "string" && (allowed as readonly string[]).includes(value)
    ? (value as T)
    : undefined;
}

export const pickPracticeTab = (value: unknown) => pick(PRACTICE_TABS, value);
export const pickProfileSheet = (value: unknown) => pick(PROFILE_SHEETS, value);
