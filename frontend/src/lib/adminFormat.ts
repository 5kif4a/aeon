/** Small display helpers shared by the admin screens. */

import { AGENTS } from "./agents";
import type { Lang } from "./i18n";

/** Agent display name; unknown ids (e.g. "council") are shown as-is. */
export function agentLabel(agentId: string, lang: Lang): string {
  return AGENTS[agentId]?.name[lang] ?? agentId;
}

/** Positive integer page number from a search param; anything else is page 1. */
export function pickPage(value: unknown): number {
  const number = Number(value);
  return Number.isInteger(number) && number > 0 ? number : 1;
}

export function pickString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function pickOptionalId(value: unknown): number | undefined {
  const number = Number(value);
  return Number.isInteger(number) && number > 0 ? number : undefined;
}

export function planChipClass(plan: string): string {
  if (plan === "Pro") return "border-gold text-gold";
  if (plan === "Trial") return "border-success text-success";
  return "text-muted";
}

export const STATS_RANGES = [7, 30, 90] as const;
export type StatsRange = (typeof STATS_RANGES)[number];

export function pickStatsRange(value: unknown): StatsRange {
  const number = Number(value);
  return (STATS_RANGES as readonly number[]).includes(number) ? (number as StatsRange) : 30;
}
