import type { ReactNode } from "react";

/** Centered modal dialog. Use for focused, action-oriented content. */
export function Modal({
  title,
  onClose,
  children,
}: {
  title?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-30 grid place-items-center p-4">
      <div className="absolute inset-0 bg-[rgba(0,0,0,0.6)]" onClick={onClose}></div>
      <div className="relative z-[1] max-h-[min(86vh,760px)] w-[min(100%,460px)] overflow-auto rounded-[24px] border border-line bg-[rgba(18,17,16,0.98)] p-5 shadow-[0_28px_80px_rgba(0,0,0,0.55)]">
        <header className="mb-4 flex items-center justify-between gap-3">
          {title ? <h3 className="font-serif text-[22px]">{title}</h3> : <span />}
          <button
            type="button"
            onClick={onClose}
            className="h-[38px] w-[38px] shrink-0 cursor-pointer rounded-full bg-[rgba(255,255,255,0.06)] text-[24px] text-text"
          >
            ×
          </button>
        </header>
        <div>{children}</div>
      </div>
    </div>
  );
}
