import type { Summary } from "../types/api";
import { biasWord, formatEnergy, formatGw, formatMw, formatSignedMw } from "../lib/format";

export function KpiStrip({ summary }: { summary: Summary }) {
  const biasClass = summary.bias_mw == null ? "" : summary.bias_mw > 0 ? "over" : summary.bias_mw < 0 ? "under" : "";
  return (
    <div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <article className="kpi">
          <span>Forecast</span>
          <strong>{formatMw(summary.mean_forecast_mw)}</strong>
          <small>{formatGw(summary.mean_forecast_mw)} · matched hours</small>
        </article>
        <article className="kpi">
          <span>Actual</span>
          <strong>{formatMw(summary.mean_actual_mw)}</strong>
          <small>{formatGw(summary.mean_actual_mw)} · matched hours</small>
        </article>
        <article className="kpi">
          <span>MAE</span>
          <strong>{formatMw(summary.mae_mw, 1)}</strong>
          <small>Average absolute forecast error</small>
        </article>
        <article className="kpi">
          <span>RMSE</span>
          <strong>{formatMw(summary.rmse_mw, 1)}</strong>
          <small>Gives extra weight to large errors</small>
        </article>
        <article className={`kpi ${biasClass}`}>
          <span>Bias</span>
          <strong>{formatSignedMw(summary.bias_mw)}</strong>
          <small>
            {biasWord(summary.bias_mw)}
            {summary.bias_mw == null ? "" : ". Average signed error"}
          </small>
        </article>
        <article className="kpi">
          <span>Matched hours</span>
          <strong>
            {summary.n_matched}
            <span className="font-normal text-[13px] text-[var(--muted)]"> / {summary.n_expected}</span>
          </strong>
          <small>Hours with both a forecast and measured generation</small>
        </article>
      </div>
      <p className="energy">
        Forecast energy {formatEnergy(summary.forecast_energy_mwh)} across {summary.forecast_hours} hourly
        forecasts. Measured generation {formatEnergy(summary.actual_energy_mwh)} across{" "}
        {summary.actual_half_hours} of {summary.expected_half_hours} half-hours. Each half-hour counts as
        MW × 0.5 hour. Energy includes a reading even when that hour cannot be scored.
      </p>
    </div>
  );
}

export function KpiSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6" aria-hidden>
      {Array.from({ length: 6 }, (_, index) => (
        <div className="kpi" key={index}>
          <div className="skeleton" />
          <div className="skeleton" />
        </div>
      ))}
    </div>
  );
}

export function AlertNotice({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="alert" role="alert">
      <p>{message}</p>
      <button type="button" className="button" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}
