import { describe, expect, it } from "vitest";
import {
  accuracyHeading,
  accuracyScopeNote,
  accuracyWindow,
  calendarWeek,
  clampDay,
  commitDay,
  deskContext,
  weekWindow,
  windowDescription,
} from "./dates";
import { biasWord, formatMw, formatSignedMw, partialScoreMessage } from "./format";
import { sortPeriods } from "./sort";
import type { Period } from "../types/api";

describe("January windows", () => {
  it("uses the Monday to Sunday week clipped to the month", () => {
    expect(weekWindow("2026-01-15")).toEqual({ from: "2026-01-12", to: "2026-01-18" });
    expect(weekWindow("2026-01-01")).toEqual({ from: "2026-01-01", to: "2026-01-04" });
    expect(weekWindow("2026-01-31")).toEqual({ from: "2026-01-26", to: "2026-01-31" });
    expect(calendarWeek("2026-01-01")).toEqual({ from: "2025-12-29", to: "2026-01-04" });
    expect(accuracyWindow("2026-01-20", "day")).toEqual({ from: "2026-01-20", to: "2026-01-20" });
    expect(accuracyWindow("2026-01-20", "january")).toEqual({ from: "2026-01-01", to: "2026-01-31" });
    expect(accuracyWindow("2026-01-01", "january")).toEqual({ from: "2026-01-01", to: "2026-01-31" });
  });

  it("keeps the date picker inside January and explains clipped weeks", () => {
    expect(clampDay("2025-12-31")).toBe("2026-01-01");
    expect(clampDay("2026-02-01")).toBe("2026-01-31");
    expect(clampDay("2026-01-15")).toBe("2026-01-15");
    expect(commitDay("", "2026-01-15")).toBe("2026-01-15");
    expect(commitDay("2026-03-02", "2026-01-15")).toBe("2026-01-31");
    expect(windowDescription("2026-01-01", "week")).toContain("1 January 2026");
    expect(windowDescription("2026-01-01", "week")).toContain("4 January 2026");
    expect(windowDescription("2026-01-15", "january")).toContain("31 January 2026");
    expect(deskContext("2026-01-15", "week", "09:20 UK time, the day before delivery")).toBe(
      "Deadline 09:20 UK time, the day before delivery. The score uses the latest forecast already published by then. Accuracy window: 12 January 2026 – 18 January 2026.",
    );
  });

  it("keeps a full Monday to Sunday week inside January and clips the edges", () => {
    const days = (from: string, to: string) =>
      (Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000 + 1;

    const interior = weekWindow("2026-01-15");
    expect(interior).toEqual(calendarWeek("2026-01-15"));
    expect(days(interior.from, interior.to)).toBe(7);
    expect(days(interior.from, interior.to) * 24).toBe(168);
    expect(interior.from <= "2026-01-15" && "2026-01-15" <= interior.to).toBe(true);

    const opening = weekWindow("2026-01-01");
    const openingCalendar = calendarWeek("2026-01-01");
    expect(days(openingCalendar.from, openingCalendar.to)).toBe(7);
    expect(opening.from).toBe("2026-01-01");
    expect(opening.to).toBe("2026-01-04");
    expect(days(opening.from, opening.to)).toBe(4);
    expect(opening.from > openingCalendar.from).toBe(true);

    const closing = weekWindow("2026-01-31");
    const closingCalendar = calendarWeek("2026-01-31");
    expect(days(closingCalendar.from, closingCalendar.to)).toBe(7);
    expect(closing).toEqual({ from: "2026-01-26", to: "2026-01-31" });
    expect(days(closing.from, closing.to)).toBe(6);
    expect(closing.to < closingCalendar.to).toBe(true);

    const monday = weekWindow("2026-01-05");
    expect(days(monday.from, monday.to)).toBe(7);
    expect(monday).toEqual({ from: "2026-01-05", to: "2026-01-11" });
  });

  it("names the accuracy window separately from the selected day", () => {
    expect(accuracyHeading("day")).toBe("Accuracy for this delivery day");
    expect(accuracyHeading("week")).toBe("Accuracy for this week");
    expect(accuracyHeading("january")).toBe("Accuracy for all of January 2026");
    expect(accuracyScopeNote("january")).toContain("1 to 31 January 2026");
    expect(accuracyScopeNote("january")).toContain("selected day");
    expect(accuracyScopeNote("week")).toContain("cards and chart above");
  });
});

describe("partial scores", () => {
  it("explains missing forecasts and half-hours without calling them zero", () => {
    expect(
      partialScoreMessage({ n_expected: 24, n_matched: 24, n_complete_actual: 24, n_with_forecast: 24 }),
    ).toBeNull();
    const message = partialScoreMessage({
      n_expected: 24,
      n_matched: 22,
      n_complete_actual: 24,
      n_with_forecast: 22,
    });
    expect(message).toContain("2 hours have no forecast");
    expect(message).toContain("not treated as zero");
  });
});

describe("number formatting", () => {
  it("keeps units and does not render missing values as zero", () => {
    expect(formatMw(14602)).toBe("14,602 MW");
    expect(formatMw(null)).toBe("-");
    expect(formatSignedMw(-20, 0)).toBe("−20 MW");
    expect(formatSignedMw(20, 0)).toBe("+20 MW");
    expect(biasWord(12)).toBe("Over-forecast");
    expect(biasWord(-4)).toBe("Under-forecast");
    expect(biasWord(null)).toBe("No matched hours");
  });
});

describe("table sorting", () => {
  it("sorts numbers and keeps missing values last", () => {
    const rows = [period("2026-01-15T02:00:00Z", 5), period("2026-01-15T00:00:00Z", null), period("2026-01-15T01:00:00Z", 9)];
    const ascending = sortPeriods(rows, "error", "asc").map((row) => row.error_mw);
    expect(ascending).toEqual([5, 9, null]);
    const byTime = sortPeriods(rows, "start", "desc").map((row) => row.start_time);
    expect(byTime[0]).toBe("2026-01-15T02:00:00Z");
  });
});

function period(start: string, error: number | null): Period {
  return {
    start_time: start,
    end_time: start,
    label: start,
    settlement_date: "2026-01-15",
    settlement_periods: [],
    forecast_mw: null,
    forecast_publish_time: null,
    forecast_publish_label: null,
    actual_mw: null,
    error_mw: error,
    absolute_error_mw: error == null ? null : Math.abs(error),
    percentage_error: null,
    half_hours: [],
  };
}
