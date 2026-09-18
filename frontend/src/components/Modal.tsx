import type { ReactNode } from "react";

import { useBodyScrollLock } from "../hooks/useBodyScrollLock";
import { closeButton } from "../lib/ui";

/**
 * Centered modal dialog. Use for focused, action-oriented content.
 *
 * The header never scrolls. By default the body scrolls as a whole; `layout="fixed"` makes
 * the body a flex column that fills the remaining height and leaves scrolling to the child,
 * for dialogs with their own pinned parts (a portrait above, an action below).
 */
export function Modal({
  title,
  onClose,
  layout = "scroll",
  children,
}: {
  title?: string;
  onClose: () => void;
  layout?: "scroll" | "fixed";
  children: ReactNode;
}) {
  useBodyScrollLock();
  const body =
    layout === "fixed"
      ? "flex min-h-0 flex-1 flex-col"
      : "min-h-0 flex-1 overflow-auto overscroll-contain";
  return (
    <div role="dialog" aria-modal="true" className="fixed inset-0 z-30 grid place-items-center p-4">
      <div className="absolute inset-0 bg-[rgba(0,0,0,0.6)]" onClick={onClose}></div>
      <div className="border-line relative z-[1] flex max-h-[min(86dvh,760px)] w-[min(100%,460px)] flex-col rounded-[8px] border bg-[rgba(18,17,16,0.98)] p-5 shadow-[0_28px_80px_rgba(0,0,0,0.55)]">
        <header className="mb-4 flex shrink-0 items-center justify-between gap-3">
          {title ? <h3 className="font-serif text-[22px]">{title}</h3> : <span />}
          <button type="button" onClick={onClose} aria-label="Close" className={closeButton}>
            ×
          </button>
        </header>
        <div className={body}>{children}</div>
      </div>
    </div>
  );
}
