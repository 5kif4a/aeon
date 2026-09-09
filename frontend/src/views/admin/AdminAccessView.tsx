import { Link } from "@tanstack/react-router";
import { Fragment, useState } from "react";

import {
  useAdminAccess,
  useAdminMe,
  useCan,
  useDeleteRole,
  useGrantAdmin,
  useRevokeAdmin,
  useUpdateRole,
} from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import type { AdminAccount, AdminPermission, AdminRole } from "../../lib/adminTypes";
import {
  adminButton,
  adminChip,
  adminLink,
  adminPrimaryButton,
  adminSelect,
  adminPageFill,
  adminTable,
  adminTableCard,
  adminTableFill,
  adminTd,
  adminTh,
} from "../../lib/adminUi";
import { ApiError } from "../../lib/api";

/**
 * Access control: the role/permission matrix and who holds which role.
 *
 * The matrix is the source of truth for everything else in the panel, so it is edited one
 * checkbox at a time (each toggle is a request) and the backend re-checks every rule -
 * an admin cannot touch their own access, and the OPS_ADMIN_IDS owners are read-only here.
 */
export function AdminAccessView() {
  const { t } = useAdminT();
  const access = useAdminAccess();
  const me = useAdminMe();
  const updateRole = useUpdateRole();
  const canManage = useCan()("admins.manage");
  const [tab, setTab] = useState<"roles" | "admins">("roles");
  const [error, setError] = useState("");

  const fail = (reason: unknown) =>
    setError(reason instanceof ApiError ? reason.message : t("admin_error"));

  const toggle = (role: AdminRole, permission: string, on: boolean) => {
    setError("");
    const permissions = on
      ? [...role.permissions, permission]
      : role.permissions.filter((key) => key !== permission);
    updateRole.mutate({ roleId: role.id, permissions }, { onError: fail });
  };

  return (
    <div className={adminPageFill}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="border-line flex gap-1 rounded-[8px] border p-1" role="tablist">
            {(["roles", "admins"] as const).map((value) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={tab === value}
                className={`cursor-pointer rounded-[6px] px-3 py-1.5 text-[12px] font-[700] ${
                  tab === value ? "bg-surface-strong text-text" : "text-muted hover:text-text"
                }`}
                onClick={() => setTab(value)}
              >
                {value === "roles" ? t("admin_access_roles") : t("admin_access_admins")}
              </button>
            ))}
          </div>
          {error ? <span className="text-danger text-[13px]">{error}</span> : null}
        </div>
        {canManage ? (
          <Link
            to={tab === "roles" ? "/admin/access/roles/new" : "/admin/access/grant"}
            className={`${adminPrimaryButton} leading-9`}
          >
            {tab === "roles" ? t("admin_access_new_role") : t("admin_access_grant")}
          </Link>
        ) : null}
      </div>

      {access.isPending ? <p className="text-muted">{t("admin_loading")}</p> : null}
      {access.isError ? <p className="text-danger">{t("admin_error")}</p> : null}

      {access.data ? (
        tab === "roles" ? (
          <RoleMatrix
            roles={access.data.roles}
            permissions={access.data.permissions}
            myRoleId={me.data?.roleId ?? ""}
            onToggle={toggle}
            busy={updateRole.isPending}
          />
        ) : (
          <AdminsTable
            admins={access.data.admins}
            roles={access.data.roles}
            myId={me.data?.id ?? 0}
            onError={fail}
          />
        )
      ) : null}
    </div>
  );
}

function RoleMatrix({
  roles,
  permissions,
  myRoleId,
  onToggle,
  busy,
}: {
  roles: AdminRole[];
  permissions: AdminPermission[];
  myRoleId: string;
  onToggle: (role: AdminRole, permission: string, on: boolean) => void;
  busy: boolean;
}) {
  const { t } = useAdminT();
  const deleteRole = useDeleteRole();
  const groups = [...new Set(permissions.map((permission) => permission.group))];

  return (
    <section className={adminTableCard}>
      <div className={adminTableFill}>
        <table className={adminTable}>
          <thead>
            <tr>
              <th className={adminTh}>{t("admin_access_permission")}</th>
              {roles.map((role) => (
                <th key={role.id} className={`${adminTh} text-center`}>
                  {role.title}
                  <div className="text-soft text-[10px] font-normal normal-case">
                    {t("admin_access_admins_count", { count: role.admins })}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => (
              <Fragment key={group}>
                <tr>
                  <td
                    className={`${adminTd} bg-surface-strong text-soft text-[11px] font-[700] tracking-[0.08em] uppercase`}
                    colSpan={roles.length + 1}
                  >
                    {group}
                  </td>
                </tr>
                {permissions
                  .filter((permission) => permission.group === group)
                  .map((permission) => (
                    <tr key={permission.key}>
                      <td className={adminTd}>
                        <span className="font-[650]">{permission.key}</span>
                        <div className="text-soft text-[11px]">{permission.description}</div>
                      </td>
                      {roles.map((role) => {
                        // The owner role is fixed, and nobody re-cuts the role they are using.
                        const locked = role.isOwner || role.id === myRoleId;
                        return (
                          <td key={role.id} className={`${adminTd} text-center`}>
                            <input
                              type="checkbox"
                              className="accent-gold h-4 w-4 cursor-pointer disabled:cursor-default disabled:opacity-40"
                              checked={role.isOwner || role.permissions.includes(permission.key)}
                              disabled={locked || busy}
                              title={locked ? t("admin_access_locked_role") : undefined}
                              onChange={(event) =>
                                onToggle(role, permission.key, event.target.checked)
                              }
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
              </Fragment>
            ))}
            <tr>
              <td className={`${adminTd} text-soft text-[11px]`}>{t("admin_access_role_row")}</td>
              {roles.map((role) => (
                <td key={role.id} className={`${adminTd} text-center`}>
                  {role.isSystem ? (
                    <span className={adminChip}>{t("admin_access_system_role")}</span>
                  ) : (
                    <button
                      type="button"
                      className="text-soft hover:text-danger cursor-pointer text-[12px]"
                      onClick={() => deleteRole.mutate(role.id)}
                    >
                      {t("admin_access_delete_role")}
                    </button>
                  )}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AdminsTable({
  admins,
  roles,
  myId,
  onError,
}: {
  admins: AdminAccount[];
  roles: AdminRole[];
  myId: number;
  onError: (reason: unknown) => void;
}) {
  const { t } = useAdminT();
  // Still needed here: the role dropdown in each row moves an admin between roles.
  const grant = useGrantAdmin();
  const revoke = useRevokeAdmin();

  return (
    <section className={adminTableCard}>
      <div className={adminTableFill}>
        <table className={adminTable}>
          <thead>
            <tr>
              <th className={adminTh}>{t("admin_col_user")}</th>
              <th className={adminTh}>{t("admin_access_role")}</th>
              <th className={adminTh}>{t("admin_access_note")}</th>
              <th className={adminTh} />
            </tr>
          </thead>
          <tbody>
            {admins.map((admin) => (
              <tr key={admin.userId}>
                <td className={adminTd}>
                  <a className={adminLink} href={`/admin/users/${admin.userId}`}>
                    {admin.name || t("admin_user_unnamed")}
                  </a>
                  <div className="text-soft text-[11px]">
                    {admin.userId}
                    {admin.username ? ` · @${admin.username}` : ""}
                    {admin.userId === myId ? ` · ${t("admin_access_you")}` : ""}
                  </div>
                </td>
                <td className={adminTd}>
                  <select
                    className={adminSelect}
                    value={admin.roleId}
                    disabled={admin.userId === myId || grant.isPending}
                    onChange={(event) =>
                      grant.mutate(
                        { userId: admin.userId, roleId: event.target.value, note: admin.note },
                        { onError },
                      )
                    }
                    aria-label={t("admin_access_role")}
                  >
                    {roles.map((role) => (
                      <option key={role.id} value={role.id}>
                        {role.title}
                      </option>
                    ))}
                  </select>
                </td>
                <td className={`${adminTd} text-muted`}>{admin.note || "—"}</td>
                <td className={`${adminTd} text-right`}>
                  {admin.userId === myId ? null : (
                    <button
                      type="button"
                      className={adminButton}
                      disabled={revoke.isPending}
                      onClick={() => revoke.mutate(admin.userId, { onError })}
                    >
                      {t("admin_access_revoke")}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
