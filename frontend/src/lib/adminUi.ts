/** Shared Tailwind class strings for the desktop admin panel (plain literals for Tailwind). */

export const adminCard = "rounded-[10px] border border-line bg-surface p-5";

/**
 * Scroll container for data tables: the table scrolls in both axes inside the card while the
 * page stays put. `border-separate` (not collapse) is required for the sticky header row to
 * keep its bottom border while scrolling.
 *
 * Use this for a table that sits among other blocks on a long screen (a detail page). For a
 * screen whose table is the content, pair `adminPageFill` + `adminTableCard` + `adminTableFill`
 * instead: the card then takes the height left below the header instead of hugging its rows.
 */
export const adminTableScroll = "max-h-[calc(100dvh-15rem)] min-h-[160px] overflow-auto";

/** Page wrapper that claims the full height of the scroll area it lives in. */
export const adminPageFill = "flex h-full min-h-0 flex-col gap-4";

/**
 * Card that grows into the leftover height; the table inside scrolls, the footer stays put.
 * The `min-h` matters when something tall sits below the table on the same screen: the card
 * gives way to it, but never collapses to a strip of header row.
 */
export const adminTableCard = `${adminCard} flex min-h-[240px] flex-1 flex-col overflow-hidden p-0`;

/**
 * Scroll box for a table filling `adminTableCard` (`min-h-0` lets it shrink and scroll).
 * Below `lg` the panel is one scrolling column, so the table keeps its own height cap there.
 */
export const adminTableFill = "max-h-[70dvh] min-h-0 flex-1 overflow-auto lg:max-h-none";
export const adminTable = "w-full min-w-[720px] border-separate border-spacing-0 text-[13px]";
export const adminTh =
  "sticky top-0 z-[1] border-b border-line bg-surface px-3 py-2 text-left text-[11px] font-[700] tracking-[0.08em] text-soft uppercase";
export const adminTd = "border-b border-line px-3 py-2.5 align-top text-text";

export const adminInput =
  "h-9 rounded-[8px] border border-line bg-[rgba(0,0,0,0.24)] px-3 text-[13px] text-text outline-none focus:border-gold";
// `admin-select` (styles.css) replaces the native arrow with one inset like the padding.
export const adminSelect = `${adminInput} admin-select pr-9`;
export const adminTextarea =
  "w-full resize-y rounded-[8px] border border-line bg-[rgba(0,0,0,0.24)] px-3 py-2 text-[13px] leading-relaxed text-text outline-none focus:border-gold";

export const adminButton =
  "h-9 cursor-pointer rounded-[8px] border border-line bg-surface-strong px-3 text-[13px] font-[650] text-text transition hover:border-gold disabled:cursor-default disabled:opacity-50";
export const adminPrimaryButton =
  "h-9 cursor-pointer rounded-[8px] bg-gold-strong px-4 text-[13px] font-[750] text-[#1e1711] transition hover:bg-gold disabled:cursor-default disabled:opacity-50";

/** Destructive confirmation button, used inside `Modal` (delete, cancel a running send). */
export const adminDangerButton =
  "border-danger text-danger hover:bg-[rgba(213,114,103,0.12)] h-9 cursor-pointer rounded-[8px] border px-3 text-[13px] font-[650] transition disabled:cursor-default disabled:opacity-50";

export const adminChip =
  "inline-flex h-6 items-center rounded-full border border-line px-2 text-[11px] font-[700]";

export const adminLink = "text-gold underline-offset-2 hover:underline";

export const adminMuted = "text-[12px] text-muted";
