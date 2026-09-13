import { PAGE_SIZE } from "../../hooks/adminQueries";
import { useAdminT } from "../../lib/admin-i18n-context";
import { adminMuted } from "../../lib/adminUi";

interface PaginationProps {
  page: number;
  total: number;
  onPage: (page: number) => void;
}

const EDGE = 1; // pages pinned at each end
const AROUND = 1; // pages kept on each side of the current one

/**
 * The page numbers to render: the first and last pages, the current one with its neighbours,
 * and `"gap"` wherever the sequence skips. A single skipped page is shown instead of an
 * ellipsis that would take the same room and say less.
 */
function pageItems(page: number, pages: number): (number | "gap")[] {
  const wanted = new Set<number>();
  for (let index = 1; index <= Math.min(EDGE, pages); index += 1) wanted.add(index);
  for (let index = Math.max(1, pages - EDGE + 1); index <= pages; index += 1) wanted.add(index);
  for (let index = page - AROUND; index <= page + AROUND; index += 1) {
    if (index >= 1 && index <= pages) wanted.add(index);
  }
  const items: (number | "gap")[] = [];
  let previous = 0;
  for (const index of [...wanted].sort((a, b) => a - b)) {
    if (index - previous === 2) items.push(index - 1);
    else if (index - previous > 2) items.push("gap");
    items.push(index);
    previous = index;
  }
  return items;
}

const pageButton =
  "h-8 min-w-8 cursor-pointer rounded-[8px] border border-line bg-surface-strong px-2 text-[13px] font-[650] text-text transition hover:border-gold";
const currentPageButton =
  "h-8 min-w-8 rounded-[8px] border border-gold bg-[rgba(193,160,116,0.14)] px-2 text-[13px] font-[750] text-gold";

export function Pagination({ page, total, onPage }: PaginationProps) {
  const { t, formatNumber } = useAdminT();
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const current = Math.min(Math.max(page, 1), pages);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-3">
      <span className={adminMuted}>
        {t("admin_pagination", { page: current, pages, total: formatNumber(total) })}
      </span>
      {pages > 1 ? (
        <nav className="flex flex-wrap gap-1" aria-label={t("admin_pagination_nav")}>
          {pageItems(current, pages).map((item, index) =>
            item === "gap" ? (
              <span
                // Gaps have no identity of their own; their position is what they are.
                key={`gap-${index}`}
                className="text-soft flex h-8 min-w-8 items-center justify-center text-[13px]"
                aria-hidden="true"
              >
                …
              </span>
            ) : (
              <button
                key={item}
                type="button"
                className={item === current ? currentPageButton : pageButton}
                aria-current={item === current ? "page" : undefined}
                onClick={() => onPage(item)}
              >
                {item}
              </button>
            ),
          )}
        </nav>
      ) : null}
    </div>
  );
}
