/** Thin typed wrapper around the Telegram Mini App SDK loaded via script tag. */

interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: { user?: { language_code?: string } };
  ready(): void;
  expand(): void;
  close(): void;
  setHeaderColor?(color: string): void;
  setBackgroundColor?(color: string): void;
  sendData?(data: string): void;
  HapticFeedback?: {
    selectionChanged(): void;
    impactOccurred(style: "light" | "medium" | "heavy"): void;
  };
  BackButton?: {
    show(): void;
    hide(): void;
    onClick(cb: () => void): void;
    offClick(cb: () => void): void;
  };
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export const tg: TelegramWebApp | undefined = window.Telegram?.WebApp;

export function initTelegram() {
  tg?.ready();
  tg?.expand();
  tg?.setHeaderColor?.("#070706");
  tg?.setBackgroundColor?.("#070706");
}

export function haptic(type: "selection" | "impact") {
  if (type === "selection") {
    tg?.HapticFeedback?.selectionChanged();
    return;
  }
  tg?.HapticFeedback?.impactOccurred("light");
}

export function closeMiniApp() {
  tg?.close();
}

/**
 * Show Telegram's native Back button with `onClick` wired up.
 * Returns a cleanup that unregisters the handler and hides the button.
 */
export function showBackButton(onClick: () => void): () => void {
  const backButton = tg?.BackButton;
  if (!backButton) return () => {};
  backButton.onClick(onClick);
  backButton.show();
  return () => {
    backButton.offClick(onClick);
    backButton.hide();
  };
}

/** Best-effort language code from Telegram, then the browser. */
export function detectLanguageCode(): string {
  return tg?.initDataUnsafe?.user?.language_code || navigator.language || "";
}
