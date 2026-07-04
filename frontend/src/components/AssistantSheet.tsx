import { Modal } from "./Modal";
import { useT } from "../lib/i18n-context";

export interface AssistantMessage {
  agentName: string;
  text: string;
  canStartDialog?: boolean;
}

export function AssistantSheet({
  message,
  onClose,
  onStartDialog,
}: {
  message: AssistantMessage | null;
  onClose: () => void;
  onStartDialog: () => void;
}) {
  const { t } = useT();
  if (!message) return null;

  const actionBase = "min-h-[42px] rounded-[14px] font-[750] cursor-pointer";
  const gold = "bg-[linear-gradient(135deg,#d4b588,#7d5c3e)] text-[#1e1711]";
  const neutral = "bg-[rgba(255,255,255,0.07)] text-text";

  return (
    <Modal title={message.agentName} onClose={onClose}>
      <p className="mb-[14px] leading-[1.45]">{message.text}</p>
      <div className="grid grid-cols-2 gap-2">
        {message.canStartDialog && (
          <button type="button" onClick={onStartDialog} className={`${actionBase} ${gold}`}>
            {t("assistant_start_dialog")}
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          className={`${actionBase} ${message.canStartDialog ? neutral : gold}`}
        >
          {t("assistant_understood")}
        </button>
      </div>
    </Modal>
  );
}
