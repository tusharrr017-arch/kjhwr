const DASH = "-";

export function formatMw(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return DASH;
  return `${formatNumber(value, digits)} MW`;
}

export function formatSignedMw(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return DASH;
  const absolute = formatNumber(Math.abs(value), digits);
  if (value > 0) return `+${absolute} MW`;
  if (value < 0) return `−${absolute} MW`;
  return `${absolute} MW`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return DASH;
  const absolute = formatNumber(Math.abs(value), 1);
  if (value > 0) return `+${absolute}%`;
  if (value < 0) return `−${absolute}%`;
  return `${absolute}%`;
}

export function formatGw(mw: number | null | undefined): string {
  if (mw == null || Number.isNaN(mw)) return DASH;
  return `${formatNumber(mw / 1000, 2)} GW`;
}

export function formatEnergy(mwh: number | null | undefined): string {
  if (mwh == null || Number.isNaN(mwh)) return DASH;
  return `${formatNumber(mwh / 1000, 1)} GWh`;
}

export function formatStamp(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return DASH;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Europe/London",
    timeZoneName: "short",
  }).format(date);
}

export function biasWord(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "No matched hours";
  if (Math.abs(value) < 0.05) return "No material bias";
  return value > 0 ? "Over-forecast" : "Under-forecast";
}

export function partialScoreMessage(summary: {
  n_expected: number;
  n_matched: number;
  n_complete_actual: number;
  n_with_forecast: number;
}): string | null {
  if (summary.n_expected === 0 || summary.n_matched === summary.n_expected) return null;
  const missingForecast = summary.n_expected - summary.n_with_forecast;
  const incompleteActual = summary.n_expected - summary.n_complete_actual;
  const parts: string[] = [];
  if (missingForecast > 0) {
    parts.push(
      missingForecast === 1
        ? "1 hour has no forecast from the selected version"
        : `${missingForecast} hours have no forecast from the selected version`,
    );
  }
  if (incompleteActual > 0) {
    parts.push(
      incompleteActual === 1
        ? "1 hour is missing measured generation for one or both half-hours"
        : `${incompleteActual} hours are missing measured generation for one or both half-hours`,
    );
  }
  const detail = parts.length ? `${parts.join(". ")}. ` : "";
  return `${detail}An hour is scored only when both the forecast and the measured generation are available. A gap is left blank and is not treated as zero.`;
}

export function freshness(items: Array<{ cache: string; retrieved_at: string } | undefined>): string {
  const present = items.filter((item): item is { cache: string; retrieved_at: string } => Boolean(item));
  if (!present.length) return "Waiting for Elexon";
  const cached = present.every((item) => item.cache === "cache");
  const oldest = [...present].sort((a, b) => a.retrieved_at.localeCompare(b.retrieved_at))[0];
  return `${cached ? "Cached" : "Live retrieval"} · ${formatStamp(oldest.retrieved_at)}`;
}

function formatNumber(value: number, digits: number): string {
  return new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}
