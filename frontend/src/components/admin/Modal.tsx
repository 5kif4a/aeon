import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

import { useAdminT } from "../../lib/admin-i18n-context";
import { adminButton } from "../../lib/adminUi";

/**
 * Modal dialog for actions that need a confirmation step.
 *
 * Built on the native `<dialog>`: Escape, the backdrop and the focus trap come from the
 * platform instead of hand-rolled listeners. `open` drives `showModal()` / `close()`, and
 * both the Escape key (`cancel`) and a click on the backdrop call `onClose`.
 */
export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Action buttons; a Cancel button is added next to them. */
  footer?: ReactNode;
}) {
  const { t } = useAdminT();
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="border-line bg-surface text-text m-auto w-[min(440px,calc(100vw-2rem))] rounded-[12px] border p-0 backdrop:bg-[rgba(0,0,0,0.6)]"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      // A click that lands on the dialog element itself is a click on the backdrop.
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
    >
      <div className="grid gap-4 p-5">
        <h2 className="text-[15px] font-[750]">{title}</h2>
        {children}
        <div className="flex flex-wrap items-center justify-end gap-2">
          <button type="button" className={adminButton} onClick={onClose}>
            {t("admin_cancel")}
          </button>
          {footer}
        </div>
      </div>
    </dialog>
  );
}
