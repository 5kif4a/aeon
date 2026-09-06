import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";

import { Pagination } from "../../components/admin/Pagination";
import { useAdminConversations } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { agentLabel } from "../../lib/adminFormat";
import {
  adminButton,
  adminCard,
  adminLink,
  adminSelect,
  adminTable,
  adminTableScroll,
  adminTd,
  adminTh,
} from "../../lib/adminUi";
import { AGENT_IDS } from "../../lib/agents";

const route = getRouteApi("/admin/conversations");
const AGENT_OPTIONS = ["", ...AGENT_IDS, "council"];
const STATUS_OPTIONS = ["", "active", "closed"] as const;

export function AdminConversationsView() {
  const { t, lang, formatDateTime } = useAdminT();
  const search = route.useSearch();
  const navigate = useNavigate({ from: "/admin/conversations" });
  const conversations = useAdminConversations(search);

  const update = (patch: Partial<typeof search>) =>
    navigate({ search: (previous) => ({ ...previous, ...patch }) });

  return (
    <div className="grid gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-[750] tracking-[-0.02em]">
            {t("admin_nav_conversations")}
          </h1>
          <p className="text-soft text-[12px]">{t("admin_conversations_privacy")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {search.userId ? (
            <button
              type="button"
              className={adminButton}
              onClick={() => update({ userId: undefined, page: 1 })}
            >
              {t("admin_filter_user", { id: search.userId })} ✕
            </button>
          ) : null}
          <select
            className={adminSelect}
            value={search.agentId}
            onChange={(event) => update({ agentId: event.target.value, page: 1 })}
            aria-label={t("admin_col_agent")}
          >
            {AGENT_OPTIONS.map((agentId) => (
              <option key={agentId} value={agentId}>
                {agentId ? agentLabel(agentId, lang) : t("admin_filter_all_agents")}
              </option>
            ))}
          </select>
          <select
            className={adminSelect}
            value={search.status}
            onChange={(event) => update({ status: event.target.value, page: 1 })}
            aria-label={t("admin_col_status")}
          >
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status === ""
                  ? t("admin_filter_all_statuses")
                  : t(status === "active" ? "admin_status_active" : "admin_status_closed")}
              </option>
            ))}
          </select>
        </div>
      </header>

      <section className={`${adminCard} p-0`}>
        {conversations.isPending ? <p className="text-muted p-5">{t("admin_loading")}</p> : null}
        {conversations.isError ? <p className="text-danger p-5">{t("admin_error")}</p> : null}
        {conversations.data ? (
          <div className={adminTableScroll}>
            <table className={adminTable}>
              <thead>
                <tr>
                  <th className={adminTh}>{t("admin_col_updated")}</th>
                  <th className={adminTh}>{t("admin_col_agent")}</th>
                  <th className={adminTh}>{t("admin_col_user")}</th>
                  <th className={adminTh}>{t("admin_col_preview")}</th>
                  <th className={adminTh}>{t("admin_col_status")}</th>
                  <th className={`${adminTh} text-right`}>{t("admin_col_messages")}</th>
                </tr>
              </thead>
              <tbody>
                {conversations.data.items.map((conversation) => (
                  <tr key={conversation.id} className="hover:bg-[rgba(255,255,255,0.02)]">
                    <td className={`${adminTd} text-muted whitespace-nowrap`}>
                      {formatDateTime(conversation.updatedAt)}
                    </td>
                    <td className={adminTd}>{agentLabel(conversation.agentId, lang)}</td>
                    <td className={adminTd}>
                      <Link
                        to="/admin/users/$userId"
                        params={{ userId: String(conversation.userId) }}
                        className={adminLink}
                      >
                        {conversation.userId}
                      </Link>
                      <div className="text-soft text-[11px]">
                        {conversation.userLanguage} · {conversation.userPlan}
                      </div>
                    </td>
                    <td className={`${adminTd} max-w-[420px]`}>
                      <Link
                        to="/admin/conversations/$conversationId"
                        params={{ conversationId: conversation.id }}
                        className={`${adminLink} line-clamp-2`}
                      >
                        {conversation.preview ||
                          conversation.title ||
                          t("admin_conversation_untitled")}
                      </Link>
                    </td>
                    <td className={adminTd}>
                      {t(
                        conversation.status === "active"
                          ? "admin_status_active"
                          : "admin_status_closed",
                      )}
                    </td>
                    <td className={`${adminTd} text-right tabular-nums`}>
                      {conversation.messageCount}
                    </td>
                  </tr>
                ))}
                {conversations.data.items.length === 0 ? (
                  <tr>
                    <td className={`${adminTd} text-soft text-center`} colSpan={6}>
                      {t("admin_empty")}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
        {conversations.data ? (
          <div className="px-4 pb-3">
            <Pagination
              page={search.page}
              total={conversations.data.total}
              onPage={(page) => update({ page })}
            />
          </div>
        ) : null}
      </section>
    </div>
  );
}
