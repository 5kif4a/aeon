import { useAdminT } from "../../lib/admin-i18n-context";
import type { SegmentFilterSpec, SegmentFilters } from "../../lib/adminTypes";
import { adminChip, adminInput, adminSelect } from "../../lib/adminUi";

/**
 * Renders one row per filter the backend declares (`/api/admin/segments/filters`), so a new
 * condition needs no frontend change. A key that is absent from `value` is not applied.
 */
export function SegmentFilterEditor({
  specs,
  value,
  onChange,
}: {
  specs: SegmentFilterSpec[];
  value: SegmentFilters;
  onChange: (filters: SegmentFilters) => void;
}) {
  const { t } = useAdminT();

  const set = (key: string, next: SegmentFilters[string] | undefined) => {
    const filters = { ...value };
    if (next === undefined) delete filters[key];
    else filters[key] = next;
    onChange(filters);
  };

  return (
    <div className="grid gap-3">
      {specs.map((spec) => (
        <div key={spec.key} className="grid gap-1 sm:grid-cols-[240px_1fr] sm:items-center">
          <label className="text-[13px] font-[650]" htmlFor={`filter-${spec.key}`}>
            {spec.key}
            <span className="text-soft block text-[11px] font-normal">{spec.description}</span>
          </label>

          {spec.kind === "enum" ? (
            <div className="flex flex-wrap gap-2">
              {spec.options.map((option) => {
                const picked = ((value[spec.key] as string[]) ?? []).includes(option);
                return (
                  <label
                    key={option}
                    className={`${adminChip} cursor-pointer gap-1 ${
                      picked ? "border-gold text-text" : "text-muted"
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="accent-gold h-3 w-3"
                      checked={picked}
                      onChange={(event) => {
                        const current = (value[spec.key] as string[]) ?? [];
                        const next = event.target.checked
                          ? [...current, option]
                          : current.filter((item) => item !== option);
                        set(spec.key, next.length ? next : undefined);
                      }}
                    />
                    {option}
                  </label>
                );
              })}
            </div>
          ) : null}

          {spec.kind === "bool" ? (
            <select
              id={`filter-${spec.key}`}
              className={`${adminSelect} w-[160px]`}
              value={value[spec.key] === undefined ? "" : String(value[spec.key])}
              onChange={(event) =>
                set(spec.key, event.target.value === "" ? undefined : event.target.value === "true")
              }
            >
              <option value="">{t("admin_filter_any")}</option>
              <option value="true">{t("admin_filter_yes")}</option>
              <option value="false">{t("admin_filter_no")}</option>
            </select>
          ) : null}

          {spec.kind === "int" ? (
            <input
              id={`filter-${spec.key}`}
              className={`${adminInput} w-[160px]`}
              type="number"
              min={0}
              value={value[spec.key] === undefined ? "" : String(value[spec.key])}
              onChange={(event) => {
                const raw = event.target.value.trim();
                set(spec.key, raw === "" ? undefined : Math.max(0, Math.trunc(Number(raw))));
              }}
            />
          ) : null}

          {spec.kind === "ids" ? (
            <input
              id={`filter-${spec.key}`}
              className={`${adminInput} w-full`}
              placeholder={spec.key === "userIds" ? "1234, 5678" : "Kazakhstan, Serbia"}
              value={((value[spec.key] as (string | number)[]) ?? []).join(", ")}
              onChange={(event) => {
                const items = event.target.value
                  .split(",")
                  .map((item) => item.trim())
                  .filter(Boolean);
                if (!items.length) return set(spec.key, undefined);
                set(
                  spec.key,
                  spec.key === "userIds" ? (items.map(Number) as number[]) : (items as string[]),
                );
              }}
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}
