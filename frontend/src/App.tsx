import { Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { createContext, useContext, useEffect, useRef, useState } from "react";

import { AssistantSheet, type AssistantMessage } from "./components/AssistantSheet";
import { BottomNav } from "./components/BottomNav";
import { TopBar } from "./components/TopBar";
import { useProfile, useStartCouncil, useStartDialog } from "./hooks/queries";
import { agentMeta, DEFAULT_AGENT_ID } from "./lib/agents";
import { ApiError } from "./lib/api";
import { useT } from "./lib/i18n-context";
import { closeMiniApp, haptic, showBackButton, STABLE_HEIGHT_VAR } from "./lib/telegram";
import { VIEW_PATHS, viewFromPathname, type ViewName } from "./lib/views";

/** 409 means the user has not started the bot chat yet; everything else is a generic failure. */
function dialogErrorKey(error: unknown) {
  return error instanceof ApiError && error.status === 409
    ? ("assistant_start_bot_first" as const)
    : ("assistant_dialog_only_in_telegram" as const);
}

interface AppShellValue {
  activeAgentId: string;
  selectAgent: (agentId: string) => void;
  beginDialog: (message?: string) => void;
  beginCouncil: (message: string) => void;
  showMessage: (text: string, canStartDialog?: boolean) => void;
}

const AppShellContext = createContext<AppShellValue | null>(null);

/** How long the "answer will appear in the chat" note stays before the Mini App closes. */
const CLOSE_DELAY_MS = 1200;

/** Telegram's stable viewport height when available, the dynamic viewport otherwise. */
const shellMinHeight = { minHeight: `var(${STABLE_HEIGHT_VAR}, 100dvh)` } as const;

/** Shell around the routed views: agent selection, dialog actions, sheet, bottom nav. */
export function AppShell() {
  const { t, lang } = useT();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const view: ViewName = viewFromPathname(pathname);
  const [activeAgentId, setActiveAgentId] = useState(DEFAULT_AGENT_ID);
  const [assistantMessage, setAssistantMessage] = useState<AssistantMessage | null>(null);

  const { data: profile } = useProfile();
  const startDialog = useStartDialog();
  const startCouncil = useStartCouncil();
  const closeTimer = useRef<number | null>(null);

  // The close timer must not outlive the shell.
  useEffect(() => {
    return () => {
      if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    };
  }, []);

  useEffect(() => {
    if (profile?.activeAgent) setActiveAgentId(profile.activeAgent);
  }, [profile?.activeAgent]);

  // Reset scroll to the top of the page whenever the route changes.
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [pathname]);

  // Telegram's Back button returns to home from secondary views; home relies on
  // Telegram's own close control.
  useEffect(() => {
    if (view === "home") return;
    return showBackButton(() => {
      haptic("selection");
      void navigate({ to: VIEW_PATHS.home });
    });
  }, [view, navigate]);

  const showMessage = (text: string, canStartDialog = false) => {
    setAssistantMessage({ agentName: agentMeta(activeAgentId, lang).name, text, canStartDialog });
    haptic("impact");
  };

  // Tell the user where the answer will appear, then hand over to the bot chat.
  // Without this the Mini App closing reads as a crash the first time around.
  const confirmAndClose = (agentName: string) => {
    haptic("impact");
    setAssistantMessage({ agentName, text: t("assistant_answer_in_chat"), canStartDialog: false });
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => {
      closeTimer.current = null;
      closeMiniApp();
    }, CLOSE_DELAY_MS);
  };

  const beginDialog = (message = "") => {
    startDialog.mutate(
      { agentId: activeAgentId, message },
      {
        onSuccess: (response) => confirmAndClose(response.agentName),
        onError: (error) => {
          showMessage(t(dialogErrorKey(error)));
        },
      },
    );
  };

  const beginCouncil = (message: string) => {
    startCouncil.mutate(message, {
      onSuccess: (response) => confirmAndClose(response.agentName),
      onError: (error) => showMessage(t(dialogErrorKey(error))),
    });
  };

  const shell: AppShellValue = {
    activeAgentId,
    selectAgent: setActiveAgentId,
    beginDialog,
    beginCouncil,
    showMessage,
  };

  return (
    <AppShellContext.Provider value={shell}>
      <div
        className="border-line relative mx-auto w-[min(100%,560px)] overflow-hidden border-x bg-[#070706] max-[560px]:border-x-0"
        style={shellMinHeight}
      >
        <main
          className="px-[18px] pb-[calc(96px+env(safe-area-inset-bottom,0px))] max-[390px]:px-[14px]"
          style={shellMinHeight}
        >
          <TopBar />
          <Outlet />
        </main>

        <AssistantSheet
          message={assistantMessage}
          onClose={() => setAssistantMessage(null)}
          onStartDialog={() => {
            setAssistantMessage(null);
            beginDialog();
          }}
        />

        <BottomNav view={view} onChange={(next) => void navigate({ to: VIEW_PATHS[next] })} />
      </div>
    </AppShellContext.Provider>
  );
}

// The shell and its hook are intentionally co-located; fast refresh is dev-only.
// oxlint-disable-next-line react/only-export-components
export function useAppShell(): AppShellValue {
  const context = useContext(AppShellContext);
  if (!context) throw new Error("useAppShell must be used within AppShell");
  return context;
}
