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

/** Best-effort language code from Telegram, then the browser. */
export function detectLanguageCode(): string {
  return tg?.initDataUnsafe?.user?.language_code || navigator.language || "";
}
