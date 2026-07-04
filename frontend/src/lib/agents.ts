/** Agent presentation data; ids match the backend AGENTS registry. */

import type { Lang } from "./i18n";

interface AgentDef {
  icon: string;
  name: Record<Lang, string>;
  role: Record<Lang, string>;
}

export const AGENTS: Record<string, AgentDef> = {
  aurelius: {
    icon: "♜",
    name: { en: "Marcus Aurelius", ru: "Марк Аврелий" },
    role: { en: "Sage psychologist", ru: "Мудрец-психолог" },
  },
  machiavelli: {
    icon: "♞",
    name: { en: "Machiavelli", ru: "Макиавелли" },
    role: { en: "Business tactician", ru: "Бизнес-тактик" },
  },
  jung: {
    icon: "◐",
    name: { en: "Carl Jung", ru: "Карл Юнг" },
    role: { en: "Shadow analyst", ru: "Аналитик тени" },
  },
};

export const AGENT_IDS = Object.keys(AGENTS);
export const DEFAULT_AGENT_ID = "aurelius";

export interface AgentMeta {
  icon: string;
  name: string;
  role: string;
}

export function agentMeta(agentId: string | null | undefined, lang: Lang): AgentMeta {
  const agent = AGENTS[agentId ?? DEFAULT_AGENT_ID] ?? AGENTS[DEFAULT_AGENT_ID];
  return { icon: agent.icon, name: agent.name[lang], role: agent.role[lang] };
}
