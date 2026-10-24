import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Evolution, EvolutionPoint, Period, SeriesPoint } from "../types/api";
import { formatMw, formatSignedMw } from "../lib/format";

const INK = "#1c1916";
const ACCENT = "#146159";
const OVER = "#7a3329";
const GRID = "#e4ddd3";
const MUTED = "#4e483f";

export function GenerationChart({
  series,
  inspected,
  onInspect,
}: {
  series: SeriesPoint[];
  inspected: string | null;
  onInspect: (hourStart: string) => void;
}) {
  const marker = series.find((point) => point.hour_start === inspected && point.label.endsWith("00"));
  return (
    <div>
      <p className="sr-only">
        Forecast and actual wind generation. The hourly forecast is held across the two half-hours. Gaps are missing data.
      </p>
      <div className="h-[300px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={series}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            onClick={(state) => {
              if (typeof state.activeTooltipIndex !== "number") return;
              const point = series[state.activeTooltipIndex];
              if (point) onInspect(point.hour_start);
            }}
          >
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis dataKey="label" interval={5} tick={{ fill: MUTED, fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis
              tick={{ fill: MUTED, fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={58}
              domain={[0, "auto"]}
              tickFormatter={(value: number) => new Intl.NumberFormat("en-GB", { notation: "compact" }).format(value)}
            />
            <Tooltip content={<GenerationTooltip />} />
            {marker ? <ReferenceLine x={marker.label} stroke={ACCENT} strokeDasharray="3 3" /> : null}
            <Line
              type="monotone"
              dataKey="actual_mw"
              name="Actual"
              stroke={INK}
              strokeWidth={1.7}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line
              type="stepAfter"
              dataKey="forecast_mw"
              name="Forecast"
              stroke={ACCENT}
              strokeWidth={1.7}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <ul className="legend">
        <li>
          <span className="swatch swatch-actual" /> Actual half-hour
        </li>
        <li>
          <span className="swatch swatch-forecast" /> Hourly forecast, held across the hour
        </li>
      </ul>
      <p className="caption">Select a point or a table row to inspect that hour. Missing periods are gaps, not zeroes.</p>
    </div>
  );
}

function GenerationTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload?: SeriesPoint }> }) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="tooltip">
      <p>{point.label} UK</p>
      <p>Actual {formatMw(point.actual_mw)}</p>
      <p>Hour forecast {formatMw(point.forecast_mw)}</p>
    </div>
  );
}

export function ErrorChart({
  periods,
  inspected,
  onInspect,
}: {
  periods: Period[];
  inspected: string | null;
  onInspect: (hourStart: string) => void;
}) {
  const rows = periods.map((period) => ({ ...period, tick: period.label.slice(0, 5) }));
  return (
    <div>
      <div className="h-[240px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            onClick={(state) => {
              if (typeof state.activeTooltipIndex !== "number") return;
              const point = rows[state.activeTooltipIndex];
              if (point) onInspect(point.start_time);
            }}
          >
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis dataKey="tick" interval={2} tick={{ fill: MUTED, fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fill: MUTED, fontSize: 12 }} tickLine={false} axisLine={false} width={52} />
            <Tooltip content={<ErrorTooltip />} />
            <ReferenceLine y={0} stroke={INK} />
            <Bar dataKey="error_mw" isAnimationActive={false} radius={[2, 2, 0, 0]}>
              {rows.map((row) => (
                <Cell
                  key={row.start_time}
                  fill={row.error_mw == null ? "transparent" : row.error_mw >= 0 ? OVER : ACCENT}
                  stroke={row.start_time === inspected ? INK : "none"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="legend">
        <li>
          <span className="swatch swatch-over" /> Above actual
        </li>
        <li>
          <span className="swatch swatch-under" /> Below actual
        </li>
      </ul>
    </div>
  );
}

function ErrorTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload?: Period }> }) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="tooltip">
      <p>{point.label}</p>
      <p>Error {formatSignedMw(point.error_mw)}</p>
      <p>Absolute {formatMw(point.absolute_error_mw, 1)}</p>
    </div>
  );
}

export function EvolutionChart({ evolution }: { evolution: Evolution }) {
  const rows = evolution.points.map((point) => ({
    ...point,
    tick: point.label.replace(" 2026", "").replace(" GMT", "").replace(" BST", ""),
  }));
  return (
    <div>
      <div className="h-[240px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis
              dataKey="tick"
              interval="preserveStartEnd"
              minTickGap={72}
              angle={-35}
              textAnchor="end"
              height={58}
              tick={{ fill: MUTED, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis tick={{ fill: MUTED, fontSize: 12 }} tickLine={false} axisLine={false} width={52} domain={[0, "auto"]} />
            <Tooltip content={<EvolutionTooltip />} />
            {evolution.actual_mw != null ? (
              <ReferenceLine y={evolution.actual_mw} stroke={OVER} strokeDasharray="4 3" label="" />
            ) : null}
            <Line
              type="monotone"
              dataKey="generation_mw"
              stroke={INK}
              strokeWidth={1.5}
              dot={<EvolutionDot />}
              activeDot={{ r: 5 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <ul className="legend">
        <li>
          <span className="swatch swatch-dot" /> Before the deadline
        </li>
        <li>
          <span className="swatch swatch-selected" /> Used for the score
        </li>
        <li>
          <span className="swatch swatch-open" /> After the deadline
        </li>
        <li>
          <span className="swatch swatch-over" /> Measured generation
        </li>
      </ul>
    </div>
  );
}

function EvolutionDot(props: { cx?: number; cy?: number; payload?: EvolutionPoint }) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return <circle cx={0} cy={0} r={0} />;
  const fill = payload.selected ? ACCENT : payload.eligible ? INK : "none";
  const stroke = payload.selected ? ACCENT : payload.eligible ? INK : "#6f685e";
  return <circle cx={cx} cy={cy} r={payload.selected ? 4.5 : 3.5} fill={fill} stroke={stroke} strokeWidth={1.4} />;
}

function EvolutionTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload?: EvolutionPoint }>;
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="tooltip">
      <p>{point.label}</p>
      <p>Forecast {formatMw(point.generation_mw)}</p>
      <p>{point.eligible ? "Available at the deadline" : "Published after the deadline"}</p>
    </div>
  );
}
