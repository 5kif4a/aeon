/**
 * Shared Tailwind class strings for repeated UI primitives.
 * Kept as plain literals so Tailwind can statically detect the utilities.
 */

/** Dark elevated card used for panels and form containers. */
export const cardPanel =
  "rounded-[18px] border border-line bg-[linear-gradient(180deg,rgba(29,28,27,0.94),rgba(20,19,18,0.94))] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]";

/** Primary gold gradient button (sizing + font weight added per use). */
export const goldButton =
  "rounded-[14px] bg-[linear-gradient(135deg,#d4b588,#7d5c3e)] text-[#1e1711] cursor-pointer";

/** Single-line text input. */
export const field =
  "h-11 w-full rounded-[14px] border border-line bg-[rgba(0,0,0,0.24)] px-3 text-text outline-none";

/** Multi-line textarea. */
export const textareaField =
  "w-full resize-y rounded-[16px] border border-line bg-[rgba(0,0,0,0.24)] p-[14px] text-text leading-[1.45] outline-none";

/** Sheet form field label (grid so the field stacks under the caption). */
export const fieldLabel = "grid gap-[7px] text-[13px] text-muted";
