import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";

import { Pagination } from "../../components/admin/Pagination";
import { SortableTh } from "../../components/admin/SortableTh";
import { useAdminConversations } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { agentLabel, type SortOrder } from "../../lib/adminFormat";
import {
  adminButton,
  adminPageFill,
  adminTableCard,
  adminTableFill,
  adminLink,
  adminSelect,
  adminTable,
  adminTd,
  adminTh,
} from "../../lib/adminUi";
import { AGENT_IDS } from "../../lib/agents";
import type { TranslationKey } from "../../lib/i18n";

const route = getRouteApi("/admin/conversations");
const AGENT_OPTIONS = ["", ...AGENT_IDS, "council"];
const STATUS_OPTIONS = ["", "active", "closed"] as const;

/**
 * Columns in render order; `field` is the sort key `services/admin.list_conversations` knows.
 * The first message has none: sorting a page of dialogues by their opening words orders
 * nothing anyone looks for.
 */
const COLUMNS: { field?: string; label: TranslationKey; align?: "left" | "right" }[] = [
  { field: "updated", label: "admin_col_updated" },
  { field: "agent", label: "admin_col_agent" },
  { field: "user", label: "admin_col_user" },
  { label: "admin_col_preview" },
  { field: "status", label: "admin_col_status" },
  { field: "messages", label: "admin_col_messages", align: "right" },
];

export function AdminConversationsView() {
  const { t, lang, formatDateTime } = useAdminT();
  const search = route.useSearch();
  const navigate = useNavigate({ from: "/admin/conversations" });
  const conversations = useAdminConversations(search);

  const update = (patch: Partial<typeof search>) =>
    navigate({ search: (previous) => ({ ...previous, ...patch }) });

  // A new sort reshuffles every page, so page 5 of the old order means nothing in the new one.
  const sortBy = (sort: string, order: SortOrder) => update({ sort, order, page: 1 });

  return (
    <div className={adminPageFill}>
      <header className="flex flex-wrap items-end gap-3">
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

      <section className={adminTableCard}>
        {conversations.isPending ? <p className="text-muted p-5">{t("admin_loading")}</p> : null}
        {conversations.isError ? <p className="text-danger p-5">{t("admin_error")}</p> : null}
        {conversations.data ? (
          <div className={adminTableFill}>
            <table className={adminTable}>
              <thead>
                <tr>
                  {COLUMNS.map((column) =>
                    column.field ? (
                      <SortableTh
                        key={column.label}
                        label={t(column.label)}
                        field={column.field}
                        align={column.align}
                        sort={search.sort || "updated"}
                        order={search.order}
                        onSort={sortBy}
                      />
                    ) : (
                      <th key={column.label} className={adminTh}>
                        {t(column.label)}
                      </th>
                    ),
                  )}
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
                        {conversation.userName || t("admin_user_unnamed")}
                      </Link>
                      <div className="text-soft text-[11px]">
                        {conversation.userId}
                        {conversation.userUsername ? ` · @${conversation.userUsername}` : ""}
                        {" · "}
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
                    <td className={`${adminTd} text-soft text-center`} colSpan={COLUMNS.length}>
                      {t("admin_empty")}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
        {conversations.data ? (
          <div className="shrink-0 px-4 pb-3">
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
