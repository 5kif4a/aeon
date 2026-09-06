/** Thin typed wrapper around the Telegram Mini App SDK loaded via script tag. */

type TelegramEvent = "viewportChanged";

interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: { user?: { language_code?: string }; start_param?: string };
  viewportHeight?: number;
  viewportStableHeight?: number;
  isExpanded?: boolean;
  ready(): void;
  expand(): void;
  close(): void;
  setHeaderColor?(color: string): void;
  setBackgroundColor?(color: string): void;
  setBottomBarColor?(color: string): void;
  disableVerticalSwipes?(): void;
  enableClosingConfirmation?(): void;
  disableClosingConfirmation?(): void;
  onEvent?(event: TelegramEvent, handler: () => void): void;
  offEvent?(event: TelegramEvent, handler: () => void): void;
  sendData?(data: string): void;
  openInvoice?(url: string, callback?: (status: InvoiceStatus) => void): void;
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

export type InvoiceStatus = "paid" | "cancelled" | "failed" | "pending";

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export const tg: TelegramWebApp | undefined = window.Telegram?.WebApp;

const BRAND_BACKGROUND = "#070706";
const BRAND_BOTTOM_BAR = "#0d0d0c";

/** CSS custom property that mirrors Telegram's stable viewport height (px). */
export const STABLE_HEIGHT_VAR = "--tg-stable-height";

/**
 * Keyboard is treated as open when the stable viewport shrinks below this share of
 * the largest stable height seen in this session. Comparing with the session maximum
 * rather than `screen.height` keeps Telegram Desktop (a small window on a large
 * screen) from hiding the navigation permanently.
 */
const KEYBOARD_HEIGHT_RATIO = 0.75;
let maxStableHeight = 0;

function syncViewportHeight() {
  const height = tg?.viewportStableHeight;
  if (!height) return;
  if (height > maxStableHeight) maxStableHeight = height;
  document.documentElement.style.setProperty(STABLE_HEIGHT_VAR, `${Math.round(height)}px`);
}

export function initTelegram() {
  tg?.ready();
  tg?.expand();
  tg?.setHeaderColor?.(BRAND_BACKGROUND);
  tg?.setBackgroundColor?.(BRAND_BACKGROUND);
  tg?.setBottomBarColor?.(BRAND_BOTTOM_BAR);
  // A vertical swipe at the top of a long page would otherwise close the app.
  tg?.disableVerticalSwipes?.();
  syncViewportHeight();
  tg?.onEvent?.("viewportChanged", syncViewportHeight);
}

/** Current stable viewport height, or null outside Telegram. */
export function stableViewportHeight(): number | null {
  return tg?.viewportStableHeight ?? null;
}

/** True while the on-screen keyboard (or another overlay) shrinks the stable viewport. */
export function isKeyboardOpen(): boolean {
  const height = stableViewportHeight();
  if (!height || !maxStableHeight) return false;
  return height < maxStableHeight * KEYBOARD_HEIGHT_RATIO;
}

/** Subscribe to viewport changes; returns an unsubscribe function. */
export function onViewportChanged(handler: () => void): () => void {
  if (!tg?.onEvent) return () => {};
  tg.onEvent("viewportChanged", handler);
  return () => tg.offEvent?.("viewportChanged", handler);
}

/** Ask Telegram to confirm before closing (used while a form holds unsaved text). No-op when unsupported. */
export function setClosingConfirmation(enabled: boolean) {
  if (enabled) tg?.enableClosingConfirmation?.();
  else tg?.disableClosingConfirmation?.();
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

export function openInvoice(url: string): Promise<InvoiceStatus> {
  return new Promise((resolve) => {
    if (tg?.openInvoice) {
      tg.openInvoice(url, resolve);
      return;
    }
    window.open(url, "_blank", "noopener,noreferrer");
    resolve("pending");
  });
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
