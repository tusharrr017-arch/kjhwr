import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw, Wind } from "lucide-react";
import { fetchAccuracy, fetchForecasts, fetchOverview, type DeskQuery } from "./lib/api";
import {
  accuracyHeading,
  accuracyScopeNote,
  accuracyWindow,
  commitDay,
  formatDay,
  formatRange,
  type WindowMode,
} from "./lib/dates";
import { freshness, formatMw, formatSignedMw, partialScoreMessage } from "./lib/format";
import { evolutionSentence } from "./lib/narrative";
import type { CutoffProfile } from "./types/api";
import { Controls } from "./components/Controls";
import { Definitions } from "./components/Definitions";
import { ErrorChart, EvolutionChart, GenerationChart } from "./components/Charts";
import { AlertNotice, KpiSkeleton, KpiStrip } from "./components/KpiStrip";
import { DailyTable, PeriodTable } from "./components/Tables";

export default function App() {
  const [deliveryDate, setDeliveryDate] = useState("2026-01-15");
  const [windowMode, setWindowMode] = useState<WindowMode>("week");
  const [profile, setProfile] = useState<CutoffProfile>("epex_60min");
  const [customTime, setCustomTime] = useState("09:20");
  const [publish, setPublish] = useState("decision");
  const [hourStart, setHourStart] = useState<string | null>(null);
  const refresh = useRefresh();
  const range = accuracyWindow(deliveryDate, windowMode);
  const dayQuery: DeskQuery = {
    profile,
    customTime,
    publishTime: publish,
    startTime: hourStart,
    refresh: false,
  };

  const overview = useQuery({
    queryKey: ["overview", deliveryDate, profile, customTime, publish, refresh.token],
    queryFn: () => fetchOverview(deliveryDate, deliveryDate, { ...dayQuery, refresh: refresh.take("overview") }),
  });
  const forecasts = useQuery({
    queryKey: ["forecasts", deliveryDate, profile, customTime, publish, hourStart, refresh.token],
    queryFn: () => fetchForecasts(deliveryDate, { ...dayQuery, refresh: refresh.take("forecasts") }),
  });
  const accuracy = useQuery({
    queryKey: ["accuracy", range.from, range.to, profile, customTime, refresh.token],
    queryFn: () =>
      fetchAccuracy(range.from, range.to, {
        profile,
        customTime,
        refresh: refresh.take("accuracy"),
      }),
  });

  useEffect(() => {
    if (!forecasts.data || publish === "decision") return;
    const known = forecasts.data.publications.some((item) => item.publish_time === publish);
    if (!known) setPublish("decision");
  }, [forecasts.data, publish]);

  const view = forecasts.data;
  const summary = overview.data?.summary ?? view?.summary;
  const metadata = view?.metadata ?? overview.data?.metadata;
  const inspected = hourStart ?? view?.evolution.start_time ?? null;
  const hasSeries = view?.series.some((point) => point.actual_mw != null || point.forecast_mw != null) ?? false;

  return (
    <>
      <a className="skip" href="#delivery">
        Skip to delivery day
      </a>
      <main className="shell">
        <header className="topbar">
          <div className="brand">
            <p className="eyebrow">
              <Wind size={14} aria-hidden /> GB wind desk
            </p>
            <h1>Foregate</h1>
            <p>Day-ahead view of national wind forecasts and outturn.</p>
          </div>
          <div className="freshness">
            <p>{formatDay(deliveryDate)}</p>
            <p>{freshness([overview.data?.metadata, view?.metadata, accuracy.data?.metadata])}</p>
            <button type="button" className="button" onClick={refresh.request}>
              <RefreshCw size={15} aria-hidden /> Refresh from Elexon
            </button>
          </div>
        </header>

        <p className="lede">
          National wind for 1–31 January 2026. Positive error means the forecast was higher than measured
          generation. The score does not say how much electricity to buy.
        </p>

        <Controls
          deliveryDate={deliveryDate}
          windowMode={windowMode}
          profile={profile}
          customTime={customTime}
          publish={publish}
          publications={view?.publications ?? []}
          onDeliveryDate={(value) => {
            const next = commitDay(value, deliveryDate);
            if (next === deliveryDate) return;
            setDeliveryDate(next);
            setPublish("decision");
            setHourStart(null);
          }}
          onWindowMode={setWindowMode}
          onProfile={setProfile}
          onCustomTime={setCustomTime}
          onPublish={(value) => {
            setPublish(value);
            setHourStart(null);
          }}
          citation={metadata?.cutoff_citation}
        />
        {metadata?.warnings.length ? (
          <div className="warn" role="status">
            {metadata.warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        ) : null}

        <div className="stack">
          <section aria-labelledby="day-kpis-heading">
            <div className="panel-head">
              <h2 id="day-kpis-heading" className="section-title">
                Selected day
              </h2>
              <p>{formatDay(deliveryDate)}</p>
            </div>
            <p className="note">
              These cards, and the chart below, are for {formatDay(deliveryDate)} only. Changing the accuracy
              window does not change them.
            </p>
            {summary ? (
              <KpiStrip summary={summary} />
            ) : overview.isError && forecasts.isError ? (
              <AlertNotice message={messageOf(overview.error)} onRetry={() => void overview.refetch()} />
            ) : (
              <>
                <p className="sr-only">Loading summary</p>
                <KpiSkeleton />
              </>
            )}
          </section>

          <section className="panel" id="delivery" aria-labelledby="delivery-heading">
            <div className="panel-head">
              <h2 id="delivery-heading">Selected-day forecast</h2>
              <p>{formatDay(deliveryDate)}</p>
            </div>
            {forecasts.isPending ? (
              <div className="skeleton chart-skeleton" aria-label="Loading delivery day" />
            ) : forecasts.isError ? (
              <AlertNotice message={messageOf(forecasts.error)} onRetry={() => void forecasts.refetch()} />
            ) : view && hasSeries ? (
              <>
                <p className="note">
                  {view.uniform_publish_label
                    ? `Hours with a forecast use the version published ${view.uniform_publish_label}.`
                    : "More than one forecast version is in use. The table shows which."}{" "}
                  {view.summary.n_matched} of {view.summary.n_expected} hours have both a forecast and
                  measured generation.
                </p>
                {partialScoreMessage(view.summary) ? (
                  <p className="note">{partialScoreMessage(view.summary)}</p>
                ) : null}
                <GenerationChart series={view.series} inspected={inspected} onInspect={setHourStart} />
              </>
            ) : (
              <p className="note">
                No wind forecast or measured generation was returned for this delivery day. Nothing has
                been filled in with zero.
              </p>
            )}
          </section>

          {view && hasSeries ? (
            <div className="grid items-start gap-4 xl:grid-cols-2">
              <section className="panel" aria-labelledby="error-heading">
                <div className="panel-head">
                  <h2 id="error-heading">Signed error</h2>
                  <p>Forecast − actual</p>
                </div>
                <ErrorChart periods={view.periods} inspected={inspected} onInspect={setHourStart} />
              </section>
              <section className="panel" aria-labelledby="evolution-heading">
                <div className="panel-head">
                  <h2 id="evolution-heading">How the forecast changed</h2>
                  <p>{view.evolution.label} UK</p>
                </div>
                {view.evolution.points.length ? (
                  <EvolutionChart evolution={view.evolution} />
                ) : (
                  <p className="note">No published version in the retrieved archive covers this hour.</p>
                )}
              </section>
              <p className="caption pair-note">{evolutionSentence(view.evolution)}</p>
            </div>
          ) : null}

          <section className="panel" aria-labelledby="accuracy-heading">
            <div className="panel-head">
              <h2 id="accuracy-heading">{accuracyHeading(windowMode)}</h2>
              <p>{formatRange(range.from, range.to)}</p>
            </div>
            <p className="note">{accuracyScopeNote(windowMode)}</p>
            {publish !== "decision" ? (
              <p className="note">
                The delivery-day charts follow the forecast version you selected. This section still uses
                the latest version available at the decision deadline.
              </p>
            ) : null}
            {accuracy.isPending ? (
              <div className="skeleton chart-skeleton" aria-label="Loading accuracy window" />
            ) : accuracy.isError ? (
              <AlertNotice message={messageOf(accuracy.error)} onRetry={() => void accuracy.refetch()} />
            ) : accuracy.data ? (
              <>
                <p className="note">
                  {accuracy.data.summary.n_matched} matched hours in this window, out of{" "}
                  {accuracy.data.summary.n_expected} expected hours. MAE {formatMw(accuracy.data.summary.mae_mw, 1)}. RMSE{" "}
                  {formatMw(accuracy.data.summary.rmse_mw, 1)}. Bias{" "}
                  {formatSignedMw(accuracy.data.summary.bias_mw)}.
                  {accuracy.data.summary.n_excluded_near_zero > 0
                    ? ` Percentage error leaves out ${accuracy.data.summary.n_excluded_near_zero} hours below ${accuracy.data.metadata.near_zero_mw} MW.`
                    : ""}
                </p>
                {partialScoreMessage(accuracy.data.summary) ? (
                  <p className="note">{partialScoreMessage(accuracy.data.summary)}</p>
                ) : null}
                {accuracy.data.daily.length ? (
                  <DailyTable rows={accuracy.data.daily} />
                ) : (
                  <p className="note">No delivery days were returned for this window.</p>
                )}
              </>
            ) : null}
          </section>

          {view && hasSeries ? (
            <section className="panel" aria-labelledby="table-heading">
              <div className="panel-head">
                <h2 id="table-heading">Selected day, hour by hour</h2>
                <p>{formatDay(deliveryDate)}</p>
              </div>
              <PeriodTable periods={view.periods} inspected={inspected} onInspect={setHourStart} />
            </section>
          ) : null}

          <section className="panel" aria-labelledby="definitions-heading">
            <h2 id="definitions-heading" className="section-title">
              How the scores are defined
            </h2>
            <Definitions definitions={metadata?.definitions} />
          </section>
        </div>

        <footer className="footer">
          <p>
            Actuals from the{" "}
            <a href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream">FUELHH stream</a>,
            fuel type WIND. Forecasts from the{" "}
            <a href="https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream">WINDFOR stream</a>.
            Both are Elexon Insights records, in MW. Nothing on this desk is a substitute for a traded position.
          </p>
        </footer>
      </main>
    </>
  );
}

function messageOf(error: unknown): string {
  if (error instanceof Error) {
    if (error.message === "Failed to fetch") {
      return "The Foregate API is not reachable. Check that the backend is running.";
    }
    return error.message;
  }
  return "The desk could not load this view.";
}

function useRefresh() {
  const [token, setToken] = useState(0);
  const remaining = useRef(0);
  function request() {
    remaining.current = 3;
    setToken((current) => current + 1);
  }
  function take(scope: string): boolean {
    void scope;
    if (remaining.current <= 0) return false;
    remaining.current -= 1;
    return true;
  }
  return { token, request, take };
}
