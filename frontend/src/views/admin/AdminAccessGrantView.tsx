import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";

import { Combobox, type ComboboxOption } from "../../components/admin/Combobox";
import {
  useAdminAccess,
  useAdminUser,
  useAdminUsersInfinite,
  useCreateRole,
  useGrantAdmin,
} from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import {
  adminCard,
  adminChip,
  adminInput,
  adminLink,
  adminMuted,
  adminPrimaryButton,
  adminSelect,
} from "../../lib/adminUi";
import { ApiError } from "../../lib/api";

/**
 * `/admin/access/grant`: pick an existing user and give them a role.
 *
 * The subject is chosen from the user list rather than typed as a Telegram id: the backend
 * only grants access to someone who has already opened the bot, so a free-form id was just
 * a way to get that wrong. The search box narrows the list server-side (the select itself
 * holds one page of users).
 */
const route = getRouteApi("/admin/access/grant");

export function AdminAccessGrantView() {
  const { t } = useAdminT();
  const navigate = useNavigate();
  const { userId: fromLink } = route.useSearch();
  const access = useAdminAccess();
  const grant = useGrantAdmin();
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<ComboboxOption | null>(null);
  const [roleId, setRoleId] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const users = useAdminUsersInfinite(query);
  // Opened from a user card: preselect that user once their name is known. Applied once per
  // linked id, so a later `?userId` (browser history) replaces the selection while a manual
  // pick is never overridden by a stale fetch.
  const linked = useAdminUser(fromLink ?? 0);
  const appliedLink = useRef<number | null>(null);
  useEffect(() => {
    if (!fromLink || !linked.data || appliedLink.current === fromLink) return;
    appliedLink.current = fromLink;
    const user = linked.data.user;
    setPicked({
      value: String(user.id),
      label: user.name || String(user.id),
      hint: [user.id, user.username ? `@${user.username}` : "", user.plan]
        .filter(Boolean)
        .join(" · "),
    });
  }, [fromLink, linked.data]);

  const roles = access.data?.roles ?? [];
  const role = roleId || roles[0]?.id || "";
  // Someone who already holds a role is shown with it: granting again moves them over.
  const currentRole = new Map(
    (access.data?.admins ?? []).map((admin) => [admin.userId, admin.roleTitle]),
  );
  const options: ComboboxOption[] = (users.data?.pages ?? []).flatMap((page) =>
    page.items.map((user) => ({
      value: String(user.id),
      label: user.name || t("admin_user_unnamed"),
      hint: [
        user.id,
        user.username ? `@${user.username}` : "",
        user.plan,
        currentRole.get(user.id) ?? "",
      ]
        .filter(Boolean)
        .join(" · "),
    })),
  );

  const submit = () => {
    const id = Number(picked?.value);
    if (!Number.isFinite(id) || id <= 0) return;
    setError("");
    grant.mutate(
      { userId: id, roleId: role, note },
      {
        onError: (reason) =>
          setError(reason instanceof ApiError ? reason.message : t("admin_error")),
        onSuccess: () => navigate({ to: "/admin/access" }),
      },
    );
  };

  return (
    <div className="grid gap-4">
      <Link to="/admin/access" className={`${adminLink} text-[13px]`}>
        ← {t("admin_nav_access")}
      </Link>

      <section className={`${adminCard} grid max-w-[560px] gap-3`}>
        <h2 className="text-[15px] font-[750]">{t("admin_access_grant")}</h2>
        <p className={adminMuted}>{t("admin_access_grant_hint")}</p>

        <Combobox
          options={options}
          value={picked}
          onChange={setPicked}
          onSearch={setQuery}
          onLoadMore={users.fetchNextPage}
          loading={users.isPending}
          loadingMore={users.isFetchingNextPage}
          hasMore={Boolean(users.hasNextPage)}
          placeholder={t("admin_access_pick_user")}
        />

        <select
          className={adminSelect}
          value={role}
          onChange={(event) => setRoleId(event.target.value)}
          aria-label={t("admin_access_role")}
        >
          {roles.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title}
            </option>
          ))}
        </select>
        <input
          className={adminInput}
          placeholder={t("admin_access_note")}
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            className={adminPrimaryButton}
            disabled={!picked || !role || grant.isPending}
            onClick={submit}
          >
            {t("admin_access_grant")}
          </button>
          {error ? <span className="text-danger text-[13px]">{error}</span> : null}
        </div>
      </section>
    </div>
  );
}

/** `/admin/access/roles/new`: a role is an id, a name and a set of permissions. */
export function AdminRoleNewView() {
  const { t } = useAdminT();
  const navigate = useNavigate();
  const access = useAdminAccess();
  const createRole = useCreateRole();
  const [id, setId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [error, setError] = useState("");

  const submit = () => {
    setError("");
    createRole.mutate(
      { id: id.trim(), title: title.trim(), description: description.trim(), permissions: picked },
      {
        onError: (reason) =>
          setError(reason instanceof ApiError ? reason.message : t("admin_error")),
        onSuccess: () => navigate({ to: "/admin/access" }),
      },
    );
  };

  return (
    <div className="grid gap-4">
      <Link to="/admin/access" className={`${adminLink} text-[13px]`}>
        ← {t("admin_nav_access")}
      </Link>

      <section className={`${adminCard} grid gap-3`}>
        <h2 className="text-[15px] font-[750]">{t("admin_access_new_role")}</h2>

        <div className="flex flex-wrap gap-2">
          <input
            className={`${adminInput} w-[180px]`}
            placeholder={t("admin_access_role_id")}
            value={id}
            onChange={(event) => setId(event.target.value)}
          />
          <input
            className={`${adminInput} w-[220px]`}
            placeholder={t("admin_access_role_title")}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <input
            className={`${adminInput} min-w-[240px] flex-1`}
            placeholder={t("admin_segment_description")}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {(access.data?.permissions ?? []).map((permission) => (
            <label
              key={permission.key}
              title={permission.description}
              className={`${adminChip} cursor-pointer gap-1 ${
                picked.includes(permission.key) ? "border-gold text-text" : "text-muted"
              }`}
            >
              <input
                type="checkbox"
                className="accent-gold h-3 w-3"
                checked={picked.includes(permission.key)}
                onChange={(event) =>
                  setPicked((previous) =>
                    event.target.checked
                      ? [...previous, permission.key]
                      : previous.filter((key) => key !== permission.key),
                  )
                }
              />
              {permission.key}
            </label>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            className={adminPrimaryButton}
            disabled={!id.trim() || !title.trim() || createRole.isPending}
            onClick={submit}
          >
            {t("admin_access_create_role")}
          </button>
          {error ? <span className="text-danger text-[13px]">{error}</span> : null}
        </div>
      </section>
    </div>
  );
}
