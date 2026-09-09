/** Small display helpers shared by the admin screens. */

import type { BroadcastStatus } from "./adminTypes";
import { AGENTS } from "./agents";
import type { Lang, TranslationKey } from "./i18n";

/**
 * Council answers are stored with `agent_id = "council"` - it is a mode, not an agent, so it
 * has no entry in `AGENTS` and needs its own label.
 */
const COUNCIL_LABEL: Record<Lang, string> = { en: "Council", ru: "Совет" };

/** Agent display name; an unknown id is shown as-is. */
export function agentLabel(agentId: string, lang: Lang): string {
  if (agentId === "council") return COUNCIL_LABEL[lang];
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

export const BROADCAST_STATUS_LABEL: Record<BroadcastStatus, TranslationKey> = {
  draft: "admin_broadcast_status_draft",
  scheduled: "admin_broadcast_status_scheduled",
  sending: "admin_broadcast_status_sending",
  sent: "admin_broadcast_status_sent",
  canceled: "admin_broadcast_status_canceled",
  failed: "admin_broadcast_status_failed",
};

export function broadcastChipClass(status: BroadcastStatus): string {
  if (status === "sent") return "border-gold text-gold";
  if (status === "sending" || status === "scheduled") return "text-text";
  if (status === "failed") return "text-danger border-danger";
  return "text-muted";
}

export const STATS_RANGES = [7, 30, 90] as const;
export type StatsRange = (typeof STATS_RANGES)[number];

export function pickStatsRange(value: unknown): StatsRange {
  const number = Number(value);
  return (STATS_RANGES as readonly number[]).includes(number) ? (number as StatsRange) : 30;
}
