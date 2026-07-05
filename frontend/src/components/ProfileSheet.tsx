import type { ReactNode } from "react";

export function ProfileSheet({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <aside className="fixed inset-0 z-20">
      <div className="absolute inset-0 bg-[rgba(0,0,0,0.5)]" onClick={onClose}></div>
      <div className="border-line absolute bottom-0 left-1/2 max-h-[min(82vh,720px)] w-[min(100%,560px)] -translate-x-1/2 overflow-auto rounded-t-[28px] border bg-[rgba(18,17,16,0.98)] p-[10px_16px_calc(18px+env(safe-area-inset-bottom,0px))] shadow-[0_24px_72px_rgba(0,0,0,0.48)]">
        <div className="mx-auto mb-3 h-1 w-11 rounded-full bg-[rgba(255,255,255,0.18)]"></div>
        <header className="mb-3 flex items-center justify-between gap-3">
          <h3 className="font-serif text-[22px]">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-text h-[38px] w-[38px] cursor-pointer rounded-full bg-[rgba(255,255,255,0.06)] text-[24px]"
          >
            ×
          </button>
        </header>
        <div>{children}</div>
      </div>
    </aside>
  );
}
