import { useEffect, useState } from "react";

import { AssistantSheet, type AssistantMessage } from "./components/AssistantSheet";
import { BottomNav } from "./components/BottomNav";
import { useProfile, useStartCouncil, useStartDialog } from "./hooks/queries";
import { agentMeta, DEFAULT_AGENT_ID } from "./lib/agents";
import { useT } from "./lib/i18n-context";
import { closeMiniApp, haptic, showBackButton } from "./lib/telegram";
import { CalendarView } from "./views/CalendarView";
import { HomeView } from "./views/HomeView";
import { ProfileView } from "./views/ProfileView";

export type ViewName = "home" | "calendar" | "profile";

function getInitialView(): ViewName {
  const view = new URLSearchParams(window.location.search).get("view");
  return view === "calendar" || view === "profile" ? view : "home";
}

export default function App() {
  const { t, lang } = useT();
  const [view, setView] = useState<ViewName>(getInitialView);
  const [activeAgentId, setActiveAgentId] = useState(DEFAULT_AGENT_ID);
  const [assistantMessage, setAssistantMessage] = useState<AssistantMessage | null>(null);

  const { data: profile } = useProfile();
  const startDialog = useStartDialog();
  const startCouncil = useStartCouncil();

  useEffect(() => {
    if (profile?.activeAgent) setActiveAgentId(profile.activeAgent);
  }, [profile?.activeAgent]);

  // Reset scroll to the top of the page whenever the view changes.
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [view]);

  // Telegram's Back button returns to home from secondary views; home relies on
  // Telegram's own close control.
  useEffect(() => {
    if (view === "home") return;
    return showBackButton(() => {
      haptic("selection");
      setView("home");
    });
  }, [view]);

  const showMessage = (text: string, canStartDialog = false) => {
    setAssistantMessage({ agentName: agentMeta(activeAgentId, lang).name, text, canStartDialog });
    haptic("impact");
  };

  const selectAgent = (agentId: string) => {
    setActiveAgentId(agentId);
  };

  const beginDialog = (message = "") => {
    startDialog.mutate(
      { agentId: activeAgentId, message },
      {
        onSuccess: () => {
          haptic("impact");
          closeMiniApp();
        },
        onError: () => {
          showMessage(t("assistant_dialog_only_in_telegram"));
        },
      },
    );
  };

  const beginCouncil = (message: string) => {
    startCouncil.mutate(message, {
      onSuccess: () => {
        haptic("impact");
        closeMiniApp();
      },
      onError: () => showMessage(t("assistant_dialog_only_in_telegram")),
    });
  };

  return (
    <div className="border-line relative mx-auto min-h-screen w-[min(100%,560px)] overflow-hidden border-x bg-[#070706] max-[560px]:border-x-0">
      <main className="min-h-screen px-[18px] pb-[calc(96px+env(safe-area-inset-bottom,0px))] max-[390px]:px-[14px]">
        {view === "home" && (
          <HomeView
            activeAgentId={activeAgentId}
            onSelectAgent={selectAgent}
            onStartDialog={beginDialog}
            onStartCouncil={beginCouncil}
          />
        )}
        {view === "calendar" && <CalendarView onMessage={showMessage} />}
        {view === "profile" && <ProfileView />}
      </main>

      <AssistantSheet
        message={assistantMessage}
        onClose={() => setAssistantMessage(null)}
        onStartDialog={() => {
          setAssistantMessage(null);
          beginDialog();
        }}
      />

      <BottomNav view={view} onChange={setView} />
    </div>
  );
}
