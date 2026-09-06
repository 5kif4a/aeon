import { useEffect } from "react";

import { setClosingConfirmation } from "../lib/telegram";

/**
 * Ask Telegram to confirm closing the Mini App while `dirty` is true (an unsaved
 * draft exists). The confirmation is switched off when the draft is cleared and
 * when the component unmounts.
 */
export function useClosingConfirmation(dirty: boolean) {
  useEffect(() => {
    setClosingConfirmation(dirty);
    return () => setClosingConfirmation(false);
  }, [dirty]);
}
