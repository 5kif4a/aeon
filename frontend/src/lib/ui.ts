/**
 * Shared Tailwind class strings for repeated UI primitives.
 * Kept as plain literals so Tailwind can statically detect the utilities.
 */

/** Dark elevated card used for panels and form containers. */
export const cardPanel =
  "rounded-[8px] border border-line bg-surface shadow-[inset_0_1px_0_rgba(255,255,255,0.035)]";

/** Primary gold gradient button (sizing + font weight added per use). */
export const goldButton = "rounded-[8px] bg-gold-strong text-[#1e1711] cursor-pointer";

/**
 * Keeps a focused field above the on-screen keyboard when the browser scrolls it
 * into view. 16px text also stops iOS Safari from zooming into the field.
 */
export const focusable = "scroll-mb-[120px] text-[16px]";

/** Single-line text input. */
export const field = `h-11 w-full rounded-[8px] border border-line bg-[rgba(0,0,0,0.24)] px-3 text-text outline-none focus:border-gold ${focusable}`;

/** Multi-line textarea. */
export const textareaField = `w-full resize-y rounded-[8px] border border-line bg-[rgba(0,0,0,0.24)] p-[14px] text-text leading-[1.45] outline-none focus:border-gold ${focusable}`;

/** Sheet form field label (grid so the field stacks under the caption). */
export const fieldLabel = "grid gap-[7px] text-[13px] text-muted";

/** Close button for sheets and modals: 44px hit area. */
export const closeButton =
  "text-text border-line h-11 w-11 shrink-0 cursor-pointer rounded-[8px] border bg-transparent text-[24px]";

/** Inline confirmation line shown under a form after a successful save. */
export const inlineStatus = "text-success text-[13px] font-[650]";

/**
 * Horizontal scroll track with the scrollbar hidden, for carousels and chip rows.
 * Scrolling is contained here so the page body never moves sideways.
 */
export const scrollTrack =
  "flex overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden";
