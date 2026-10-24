import { useState } from "react";
import type { DailyScore, Period } from "../types/api";
import { formatDay } from "../lib/dates";
import { formatMw, formatPercent, formatSignedMw } from "../lib/format";
import { sortPeriods, type SortDirection, type SortKey } from "../lib/sort";

export function DailyTable({ rows }: { rows: DailyScore[] }) {
  const maxMae = Math.max(...rows.map((row) => row.mae_mw ?? 0), 0);
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">Daily accuracy at the decision deadline</caption>
        <thead>
          <tr>
            <th scope="col">Delivery day</th>
            <th scope="col" className="num">Matched</th>
            <th scope="col" className="num">Forecast</th>
            <th scope="col" className="num">Actual</th>
            <th scope="col" className="num">MAE</th>
            <th scope="col" className="num">RMSE</th>
            <th scope="col" className="num">Bias</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.settlement_date}>
              <td>{formatDay(row.settlement_date)}</td>
              <td className="num">
                {row.n_matched} / {row.n_expected}
              </td>
              <td className="num">{formatMw(row.mean_forecast_mw)}</td>
              <td className="num">{formatMw(row.mean_actual_mw)}</td>
              <td className="num">
                {row.mae_mw != null && maxMae > 0 ? (
                  <span className="meter" aria-hidden>
                    <span style={{ width: `${Math.max(6, (row.mae_mw / maxMae) * 100)}%` }} />
                  </span>
                ) : null}
                {formatMw(row.mae_mw, 1)}
              </td>
              <td className="num">{formatMw(row.rmse_mw, 1)}</td>
              <td className="num">{formatSignedMw(row.bias_mw)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const COLUMNS: Array<{ key: SortKey; label: string; numeric: boolean }> = [
  { key: "start", label: "Delivery period", numeric: false },
  { key: "publish", label: "Forecast publication", numeric: false },
  { key: "forecast", label: "Forecast", numeric: true },
  { key: "actual", label: "Actual", numeric: true },
  { key: "error", label: "Signed error", numeric: true },
  { key: "absolute", label: "Absolute error", numeric: true },
  { key: "percent", label: "Percentage error", numeric: true },
];

export function PeriodTable({
  periods,
  inspected,
  onInspect,
}: {
  periods: Period[];
  inspected: string | null;
  onInspect: (hourStart: string) => void;
}) {
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({
    key: "start",
    direction: "asc",
  });
  const rows = sortPeriods(periods, sort.key, sort.direction);

  function toggle(key: SortKey) {
    setSort((current) =>
      current.key === key
        ? { key, direction: current.direction === "asc" ? "desc" : "asc" }
        : { key, direction: key === "start" || key === "publish" ? "asc" : "desc" },
    );
  }

  return (
    <div className="table-wrap">
      <table className="interactive">
        <caption className="sr-only">Hourly forecast, actual and error for the selected issue</caption>
        <thead>
          <tr>
            {COLUMNS.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={column.numeric ? "num" : undefined}
                aria-sort={sort.key === column.key ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}
              >
                <button type="button" className="sort" onClick={() => toggle(column.key)}>
                  {column.label}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.start_time}
              aria-selected={row.start_time === inspected}
              tabIndex={0}
              onClick={() => onInspect(row.start_time)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onInspect(row.start_time);
                }
              }}
            >
              <td>
                {row.label}
                {row.settlement_periods.length ? ` · SP ${row.settlement_periods.join("–")}` : ""}
              </td>
              <td>{row.forecast_publish_label ?? "-"}</td>
              <td className="num">{formatMw(row.forecast_mw)}</td>
              <td className="num">{formatMw(row.actual_mw)}</td>
              <td className="num">{formatSignedMw(row.error_mw)}</td>
              <td className="num">{formatMw(row.absolute_error_mw, 1)}</td>
              <td className="num">{formatPercent(row.percentage_error)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
