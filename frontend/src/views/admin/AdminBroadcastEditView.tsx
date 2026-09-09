import { getRouteApi, Link, useNavigate } from "@tanstack/react-router";

import { BroadcastComposer } from "../../components/admin/BroadcastComposer";
import { useBroadcast } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import type { Broadcast } from "../../lib/adminTypes";
import { adminLink } from "../../lib/adminUi";

const route = getRouteApi("/admin/broadcasts/$broadcastId/edit");

/** `/admin/broadcasts/new`: compose a draft, then land on its screen to send it. */
export function AdminBroadcastNewView() {
  const { t } = useAdminT();
  const navigate = useNavigate();
  return (
    <div className="grid gap-4">
      <Link to="/admin/broadcasts" className={`${adminLink} text-[13px]`}>
        ← {t("admin_nav_broadcasts")}
      </Link>
      <BroadcastComposer
        onSaved={(saved: Broadcast) =>
          navigate({ to: "/admin/broadcasts/$broadcastId", params: { broadcastId: saved.id } })
        }
      />
    </div>
  );
}

/** `/admin/broadcasts/$broadcastId/edit`: the same composer over a saved draft. */
export function AdminBroadcastEditView() {
  const { t } = useAdminT();
  const navigate = useNavigate();
  const { broadcastId } = route.useParams();
  const broadcast = useBroadcast(broadcastId);

  if (broadcast.isPending) return <p className="text-muted">{t("admin_loading")}</p>;
  if (broadcast.isError || !broadcast.data)
    return <p className="text-danger">{t("admin_error")}</p>;

  return (
    <div className="grid gap-4">
      <Link
        to="/admin/broadcasts/$broadcastId"
        params={{ broadcastId }}
        className={`${adminLink} text-[13px]`}
      >
        ← {broadcast.data.title || t("admin_nav_broadcasts")}
      </Link>
      <BroadcastComposer
        broadcast={broadcast.data}
        onSaved={() => navigate({ to: "/admin/broadcasts/$broadcastId", params: { broadcastId } })}
      />
    </div>
  );
}
