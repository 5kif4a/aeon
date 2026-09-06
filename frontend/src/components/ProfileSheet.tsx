import type { ReactNode } from "react";

import { useBodyScrollLock } from "../hooks/useBodyScrollLock";
import { STABLE_HEIGHT_VAR } from "../lib/telegram";
import { closeButton } from "../lib/ui";

/**
 * The overlay follows Telegram's stable viewport height instead of `100vh`, so when
 * the keyboard opens the sheet shrinks above it and the field scrolls into view inside
 * the sheet rather than WebKit scrolling the whole page.
 */
const overlayHeight = { height: `var(${STABLE_HEIGHT_VAR}, 100dvh)` } as const;

export function ProfileSheet({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useBodyScrollLock();
  return (
    <aside className="fixed inset-x-0 top-0 z-20" style={overlayHeight}>
      <div className="absolute inset-0 bg-[rgba(0,0,0,0.5)]" onClick={onClose}></div>
      <div className="border-line absolute bottom-0 left-1/2 flex max-h-[min(88%,720px)] w-[min(100%,560px)] -translate-x-1/2 flex-col overflow-hidden rounded-t-[8px] border bg-[rgba(18,17,16,0.98)] shadow-[0_24px_72px_rgba(0,0,0,0.48)]">
        <header className="shrink-0 px-4 pt-[10px]">
          <div className="mx-auto mb-3 h-1 w-11 rounded-full bg-[rgba(255,255,255,0.18)]"></div>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h3 className="font-serif text-[22px]">{title}</h3>
            <button type="button" onClick={onClose} aria-label="Close" className={closeButton}>
              ×
            </button>
          </div>
        </header>
        <div className="min-h-0 overflow-y-auto overscroll-contain px-4 pb-[calc(18px+env(safe-area-inset-bottom,0px))]">
          {children}
        </div>
      </div>
    </aside>
  );
}
