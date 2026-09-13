import { useAdminT } from "../../lib/admin-i18n-context";
import type { SortOrder } from "../../lib/adminFormat";
import { adminTh } from "../../lib/adminUi";

interface SortableThProps {
  label: string;
  /** Sort key this column sends to the API; must be one the backend list knows. */
  field: string;
  sort: string;
  order: SortOrder;
  onSort: (sort: string, order: SortOrder) => void;
  align?: "left" | "right";
}

/**
 * A table header that sorts. Clicking an inactive column opens it descending - the useful
 * end first for dates, counts and money alike - and clicking the active one flips it.
 */
export function SortableTh({ label, field, sort, order, onSort, align = "left" }: SortableThProps) {
  const { t } = useAdminT();
  const active = sort === field;
  return (
    <th
      className={`${adminTh} ${align === "right" ? "text-right" : ""}`}
      aria-sort={active ? (order === "asc" ? "ascending" : "descending") : "none"}
    >
      <button
        type="button"
        className={`group hover:text-gold inline-flex cursor-pointer items-center gap-1 uppercase transition ${
          active ? "text-gold" : ""
        } ${align === "right" ? "flex-row-reverse" : ""}`}
        title={t("admin_sort_hint")}
        onClick={() => onSort(field, active && order === "desc" ? "asc" : "desc")}
      >
        {label}
        <span aria-hidden="true" className={active ? "" : "opacity-0 group-hover:opacity-50"}>
          {order === "asc" ? "↑" : "↓"}
        </span>
      </button>
    </th>
  );
}
