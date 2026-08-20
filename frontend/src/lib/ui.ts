/**
 * Shared Tailwind class strings for repeated UI primitives.
 * Kept as plain literals so Tailwind can statically detect the utilities.
 */

/** Dark elevated card used for panels and form containers. */
export const cardPanel =
  "rounded-[8px] border border-line bg-surface shadow-[inset_0_1px_0_rgba(255,255,255,0.035)]";

/** Primary gold gradient button (sizing + font weight added per use). */
export const goldButton = "rounded-[8px] bg-gold-strong text-[#1e1711] cursor-pointer";

/** Single-line text input. */
export const field =
  "h-11 w-full rounded-[8px] border border-line bg-[rgba(0,0,0,0.24)] px-3 text-text outline-none focus:border-gold";

/** Multi-line textarea. */
export const textareaField =
  "w-full resize-y rounded-[8px] border border-line bg-[rgba(0,0,0,0.24)] p-[14px] text-text leading-[1.45] outline-none focus:border-gold";

/** Sheet form field label (grid so the field stacks under the caption). */
export const fieldLabel = "grid gap-[7px] text-[13px] text-muted";
