/** Shared Tailwind class strings for the desktop admin panel (plain literals for Tailwind). */

export const adminCard = "rounded-[10px] border border-line bg-surface p-5";

export const adminTable = "w-full min-w-[720px] border-collapse text-[13px]";
export const adminTh =
  "border-b border-line px-3 py-2 text-left text-[11px] font-[700] tracking-[0.08em] text-soft uppercase";
export const adminTd = "border-b border-line px-3 py-2.5 align-top text-text";

export const adminInput =
  "h-9 rounded-[8px] border border-line bg-[rgba(0,0,0,0.24)] px-3 text-[13px] text-text outline-none focus:border-gold";
export const adminSelect = `${adminInput} pr-8`;

export const adminButton =
  "h-9 cursor-pointer rounded-[8px] border border-line bg-surface-strong px-3 text-[13px] font-[650] text-text transition hover:border-gold disabled:cursor-default disabled:opacity-50";
export const adminPrimaryButton =
  "h-9 cursor-pointer rounded-[8px] bg-gold-strong px-4 text-[13px] font-[750] text-[#1e1711] transition hover:bg-gold disabled:cursor-default disabled:opacity-50";

export const adminChip =
  "inline-flex h-6 items-center rounded-full border border-line px-2 text-[11px] font-[700]";

export const adminLink = "text-gold underline-offset-2 hover:underline";

export const adminMuted = "text-[12px] text-muted";
