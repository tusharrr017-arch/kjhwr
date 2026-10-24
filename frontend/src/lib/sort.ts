import type { Period } from "../types/api";

export type SortKey = "start" | "publish" | "forecast" | "actual" | "error" | "absolute" | "percent";
export type SortDirection = "asc" | "desc";

export function sortPeriods(rows: Period[], key: SortKey, direction: SortDirection): Period[] {
  const factor = direction === "asc" ? 1 : -1;
  return [...rows].sort((left, right) => compare(read(left, key), read(right, key), factor));
}

function read(row: Period, key: SortKey): string | number | null {
  switch (key) {
    case "start":
      return row.start_time;
    case "publish":
      return row.forecast_publish_time;
    case "forecast":
      return row.forecast_mw;
    case "actual":
      return row.actual_mw;
    case "error":
      return row.error_mw;
    case "absolute":
      return row.absolute_error_mw;
    case "percent":
      return row.percentage_error;
  }
}

function compare(left: string | number | null, right: string | number | null, factor: number): number {
  if (left == null && right == null) return 0;
  if (left == null) return 1;
  if (right == null) return -1;
  if (left < right) return -1 * factor;
  if (left > right) return 1 * factor;
  return 0;
}
