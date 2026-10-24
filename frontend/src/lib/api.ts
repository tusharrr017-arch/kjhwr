import type {
  AccuracyResponse,
  CutoffProfile,
  ForecastResponse,
  OverviewResponse,
} from "../types/api";

const base = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export interface DeskQuery {
  profile: CutoffProfile;
  customTime: string;
  publishTime?: string | null;
  startTime?: string | null;
  refresh?: boolean;
}

export function fetchForecasts(
  settlementDate: string,
  query: DeskQuery,
): Promise<ForecastResponse> {
  return getJson("/api/forecasts", {
    settlement_date: settlementDate,
    ...cutoffParams(query),
    start_time: query.startTime ?? undefined,
  });
}

export function fetchOverview(
  settlementFrom: string,
  settlementTo: string,
  query: DeskQuery,
): Promise<OverviewResponse> {
  return getJson("/api/overview", {
    settlement_from: settlementFrom,
    settlement_to: settlementTo,
    ...cutoffParams(query),
  });
}

export function fetchAccuracy(
  settlementFrom: string,
  settlementTo: string,
  query: DeskQuery,
): Promise<AccuracyResponse> {
  return getJson("/api/accuracy", {
    settlement_from: settlementFrom,
    settlement_to: settlementTo,
    cutoff_profile: query.profile,
    cutoff_time: query.profile === "custom" ? query.customTime : undefined,
    refresh: query.refresh ? "true" : undefined,
  });
}

function cutoffParams(query: DeskQuery): Record<string, string | undefined> {
  return {
    cutoff_profile: query.profile,
    cutoff_time: query.profile === "custom" ? query.customTime : undefined,
    publish_time:
      query.publishTime && query.publishTime !== "decision" ? query.publishTime : undefined,
    refresh: query.refresh ? "true" : undefined,
  };
}

async function getJson<T>(path: string, params: Record<string, string | undefined>): Promise<T> {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value);
  }
  const response = await fetch(`${base}${path}?${search.toString()}`);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json() as Promise<T>;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) return body.detail;
  } catch {
    // The body was not JSON.
  }
  if (response.status === 502) return "Elexon did not return the wind records. Try again in a moment.";
  return `The desk could not load this view (HTTP ${response.status}).`;
}
