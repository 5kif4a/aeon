/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend base URL (e.g. https://<app>.up.railway.app). Empty = same origin. */
  readonly VITE_API_URL?: string;
  /** Dev only: admin session token so /admin opens without a Telegram login. */
  readonly VITE_ADMIN_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
