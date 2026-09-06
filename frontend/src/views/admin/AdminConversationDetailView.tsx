import { getRouteApi, Link } from "@tanstack/react-router";

import { useAdminConversation } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { agentLabel } from "../../lib/adminFormat";
import { adminCard, adminLink, adminMuted } from "../../lib/adminUi";

const route = getRouteApi("/admin/conversations/$conversationId");

export function AdminConversationDetailView() {
  const { t, lang, formatDateTime } = useAdminT();
  const { conversationId } = route.useParams();
  const detail = useAdminConversation(conversationId);

  if (detail.isPending) return <p className="text-muted">{t("admin_loading")}</p>;
  if (detail.isError || !detail.data) return <p className="text-danger">{t("admin_error")}</p>;

  const { conversation, messages } = detail.data;
  const agent = agentLabel(conversation.agentId, lang);

  return (
    <div className="grid max-w-[880px] gap-4">
      <Link
        to="/admin/conversations"
        search={{ agentId: "", status: "", page: 1, userId: undefined }}
        className={`${adminLink} text-[12px]`}
      >
        ← {t("admin_nav_conversations")}
      </Link>
      <header>
        <h1 className="text-[20px] font-[750] tracking-[-0.02em]">
          {conversation.title || t("admin_conversation_untitled")}
        </h1>
        <p className={adminMuted}>
          {agent} ·{" "}
          <Link
            to="/admin/users/$userId"
            params={{ userId: String(conversation.userId) }}
            className={adminLink}
          >
            {t("admin_col_user")} {conversation.userId}
          </Link>{" "}
          · {t(conversation.status === "active" ? "admin_status_active" : "admin_status_closed")} ·{" "}
          {formatDateTime(conversation.createdAt)}
        </p>
      </header>
      {/* The thread scrolls inside its card; the header and back link stay put. */}
      <section
        className={`${adminCard} grid max-h-[calc(100dvh-14rem)] min-h-[240px] content-start gap-3 overflow-y-auto overscroll-contain`}
      >
        {messages.map((message) => (
          <article
            key={message.id}
            className={`max-w-[85%] rounded-[10px] px-4 py-3 text-[14px] leading-relaxed ${
              message.role === "user"
                ? "bg-surface-strong text-text justify-self-end"
                : "border-line text-text justify-self-start border bg-[rgba(0,0,0,0.2)]"
            }`}
          >
            <p className="text-soft mb-1 text-[11px] font-[700]">
              {message.role === "user" ? t("admin_role_user") : agent} ·{" "}
              {formatDateTime(message.createdAt)}
            </p>
            <p className="whitespace-pre-wrap">{message.text}</p>
          </article>
        ))}
        {messages.length === 0 ? <p className="text-soft">{t("admin_empty")}</p> : null}
      </section>
    </div>
  );
}
