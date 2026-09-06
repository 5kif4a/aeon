import { PAGE_SIZE } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { adminButton, adminMuted } from "../../lib/adminUi";

interface PaginationProps {
  page: number;
  total: number;
  onPage: (page: number) => void;
}

export function Pagination({ page, total, onPage }: PaginationProps) {
  const { t, formatNumber } = useAdminT();
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return (
    <div className="flex items-center justify-between gap-3 pt-3">
      <span className={adminMuted}>
        {t("admin_pagination", { page, pages, total: formatNumber(total) })}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className={adminButton}
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          {t("admin_prev")}
        </button>
        <button
          type="button"
          className={adminButton}
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
        >
          {t("admin_next")}
        </button>
      </div>
    </div>
  );
}
