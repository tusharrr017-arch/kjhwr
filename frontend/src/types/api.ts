export type CacheStatus = "live" | "cache";

export interface Summary {
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  mape_percent: number | null;
  n_matched: number;
  n_expected: number;
  n_complete_actual: number;
  n_with_forecast: number;
  n_excluded_near_zero: number;
  mean_forecast_mw: number | null;
  mean_actual_mw: number | null;
  forecast_energy_mwh: number | null;
  forecast_hours: number;
  actual_energy_mwh: number | null;
  actual_half_hours: number;
  expected_half_hours: number;
}

export interface Metadata {
  unit: string;
  energy_unit: string;
  timezone: string;
  settlement_from: string;
  settlement_to: string;
  cutoff_profile: string;
  cutoff_label: string;
  cutoff_local_time: string;
  offset_days: number;
  cutoff_citation: string;
  selection_rule: string;
  publish_time: string | null;
  alignment: string;
  near_zero_mw: number;
  definitions: Record<string, string>;
  retrieved_at: string;
  cache: CacheStatus;
  warnings: string[];
  sources: string[];
}

export interface HalfHour {
  start_time: string;
  label: string;
  settlement_period: number | null;
  generation_mw: number | null;
}

export interface Period {
  start_time: string;
  end_time: string;
  label: string;
  settlement_date: string;
  settlement_periods: number[];
  forecast_mw: number | null;
  forecast_publish_time: string | null;
  forecast_publish_label: string | null;
  actual_mw: number | null;
  error_mw: number | null;
  absolute_error_mw: number | null;
  percentage_error: number | null;
  half_hours: HalfHour[];
}

export interface SeriesPoint {
  start_time: string;
  label: string;
  hour_start: string;
  actual_mw: number | null;
  forecast_mw: number | null;
}

export interface Publication {
  publish_time: string;
  label: string;
  hours_covered: number;
  eligible: boolean;
  used_for_delivery_hour: boolean;
}

export interface EvolutionPoint {
  publish_time: string;
  label: string;
  generation_mw: number;
  eligible: boolean;
  selected: boolean;
}

export interface Evolution {
  start_time: string;
  label: string;
  actual_mw: number | null;
  cutoff_time: string;
  cutoff_label: string;
  gate_local_time: string;
  points: EvolutionPoint[];
}

export interface ForecastResponse {
  metadata: Metadata;
  summary: Summary;
  uniform_publish_time: string | null;
  uniform_publish_label: string | null;
  periods: Period[];
  series: SeriesPoint[];
  publications: Publication[];
  evolution: Evolution;
}

export interface OverviewResponse {
  metadata: Metadata;
  summary: Summary;
}

export interface DailyScore {
  settlement_date: string;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  mape_percent: number | null;
  n_matched: number;
  n_expected: number;
  n_excluded_near_zero: number;
  mean_forecast_mw: number | null;
  mean_actual_mw: number | null;
}

export interface AccuracyResponse {
  metadata: Metadata;
  summary: Summary;
  daily: DailyScore[];
}

export type CutoffProfile = "epex_60min" | "nordpool_60min" | "epex_30min" | "custom";
