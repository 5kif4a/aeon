import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { LanguageProvider } from "./lib/i18n-context";
import { initTelegram, tg } from "./lib/telegram";
import { LandingView } from "./views/LandingView";
import "./styles.css";

initTelegram();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {tg?.initData ? (
      <QueryClientProvider client={queryClient}>
        <LanguageProvider>
          <App />
        </LanguageProvider>
      </QueryClientProvider>
    ) : (
      <LandingView />
    )}
  </StrictMode>,
);
