import { useEffect, useState } from "react";

import { AssistantSheet, type AssistantMessage } from "./components/AssistantSheet";
import { BottomNav } from "./components/BottomNav";
import { useProfile, useStartDialog } from "./hooks/queries";
import { agentMeta, DEFAULT_AGENT_ID } from "./lib/agents";
import { useT } from "./lib/i18n-context";
import { closeMiniApp, haptic } from "./lib/telegram";
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

  useEffect(() => {
    if (profile?.activeAgent) setActiveAgentId(profile.activeAgent);
  }, [profile?.activeAgent]);

  const showMessage = (text: string, canStartDialog = false) => {
    setAssistantMessage({ agentName: agentMeta(activeAgentId, lang).name, text, canStartDialog });
    haptic("impact");
  };

  const selectAgent = (agentId: string) => {
    setActiveAgentId(agentId);
    const name = agentMeta(agentId, lang).name;
    setAssistantMessage({
      agentName: name,
      text: t("assistant_agent_selected", { name }),
      canStartDialog: true,
    });
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

  return (
    <div className="relative mx-auto min-h-screen w-[min(100%,560px)] overflow-hidden bg-[#070706]">
      <main className="min-h-screen px-[18px] pb-[calc(96px+env(safe-area-inset-bottom,0px))] max-[390px]:px-[14px]">
        {view === "home" && (
          <HomeView
            activeAgentId={activeAgentId}
            onSelectAgent={selectAgent}
            onStartDialog={beginDialog}
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
