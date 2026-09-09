import { useEffect, useId, useMemo, useRef, useState } from "react";

import { useAdminT } from "../../lib/admin-i18n-context";
import { adminCard, adminInput } from "../../lib/adminUi";

export interface ComboboxOption {
  value: string;
  label: string;
  /** Second line under the label: ids, plan, whatever identifies the row. */
  hint?: string;
}

/**
 * Search-and-pick control for lists that live behind an API.
 *
 * One field instead of "search box plus select": typing searches, the results drop down,
 * and scrolling to the bottom asks for the next page. The component owns no data - the
 * caller passes the current page and reacts to `onSearch` / `onLoadMore`, so it works with
 * any paginated endpoint (`useAdminUsersInfinite` is the first one).
 *
 * `onSearch` is debounced here, so a caller can feed the query straight into a query key.
 */
export function Combobox({
  options,
  value,
  onChange,
  onSearch,
  onLoadMore,
  loading = false,
  loadingMore = false,
  hasMore = false,
  placeholder,
  disabled = false,
  debounceMs = 250,
}: {
  options: ComboboxOption[];
  value: ComboboxOption | null;
  onChange: (option: ComboboxOption | null) => void;
  onSearch: (query: string) => void;
  onLoadMore?: () => void;
  loading?: boolean;
  loadingMore?: boolean;
  hasMore?: boolean;
  placeholder?: string;
  disabled?: boolean;
  debounceMs?: number;
}) {
  const { t } = useAdminT();
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLLIElement>(null);
  const searchRef = useRef(onSearch);
  searchRef.current = onSearch;

  // Debounce: the caller usually turns the query into a query key, one request per pause.
  useEffect(() => {
    if (!open) return;
    const timer = setTimeout(() => searchRef.current(query.trim()), debounceMs);
    return () => clearTimeout(timer);
  }, [query, open, debounceMs]);

  // Close on an outside click; Escape is handled on the input itself.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) close();
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  // Infinite loading: ask for the next page once the end of the list is in view. Not while
  // a page is already in flight - react-query's fetchNextPage would cancel and restart it.
  const loadingMoreRef = useRef(loadingMore);
  loadingMoreRef.current = loadingMore;
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!open || !sentinel || !hasMore || !onLoadMore) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (loadingMoreRef.current) return;
        if (entries.some((entry) => entry.isIntersecting)) onLoadMore();
      },
      { root: sentinel.closest("ul"), rootMargin: "80px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [open, hasMore, onLoadMore, options.length]);

  const text = useMemo(() => (open ? query : (value?.label ?? "")), [open, query, value]);

  const close = () => {
    setOpen(false);
    setQuery("");
  };

  const pick = (option: ComboboxOption) => {
    onChange(option);
    close();
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape") {
      close();
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      setActive((current) => {
        const next = event.key === "ArrowDown" ? current + 1 : current - 1;
        if (!options.length) return 0;
        return (next + options.length) % options.length;
      });
      return;
    }
    if (event.key === "Enter" && open && options[active]) {
      event.preventDefault();
      pick(options[active]);
    }
  };

  return (
    <div ref={rootRef} className="relative">
      <input
        className={`${adminInput} w-full`}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        placeholder={placeholder}
        disabled={disabled}
        value={text}
        onChange={(event) => {
          setQuery(event.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {value && !open ? (
        <button
          type="button"
          className="text-soft hover:text-text absolute top-1/2 right-2 -translate-y-1/2 cursor-pointer px-1 text-[13px]"
          aria-label={t("admin_combobox_clear")}
          onClick={() => {
            onChange(null);
            setQuery("");
          }}
        >
          ×
        </button>
      ) : null}

      {open ? (
        <ul
          id={listId}
          role="listbox"
          className={`${adminCard} absolute z-10 mt-1 max-h-[280px] w-full overflow-auto p-1`}
        >
          {loading && !options.length ? (
            <li className="text-muted px-3 py-2 text-[13px]">{t("admin_loading")}</li>
          ) : null}
          {!loading && !options.length ? (
            <li className="text-soft px-3 py-2 text-[13px]">{t("admin_empty")}</li>
          ) : null}
          {options.map((option, index) => (
            <li key={option.value}>
              <button
                type="button"
                role="option"
                aria-selected={option.value === value?.value}
                className={`block w-full cursor-pointer rounded-[6px] px-3 py-2 text-left text-[13px] ${
                  index === active ? "bg-surface-strong text-text" : "text-muted hover:text-text"
                }`}
                onPointerEnter={() => setActive(index)}
                onClick={() => pick(option)}
              >
                {option.label}
                {option.hint ? (
                  <span className="text-soft block text-[11px]">{option.hint}</span>
                ) : null}
              </button>
            </li>
          ))}
          {hasMore ? (
            <li ref={sentinelRef} className="text-soft px-3 py-2 text-[12px]">
              {loadingMore ? t("admin_loading") : ""}
            </li>
          ) : null}
        </ul>
      ) : null}
    </div>
  );
}
