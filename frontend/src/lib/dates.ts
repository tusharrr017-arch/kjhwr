export const STUDY_START = "2026-01-01";
export const STUDY_END = "2026-01-31";

export type WindowMode = "day" | "week" | "january";

export function clampDay(iso: string): string {
  if (iso < STUDY_START) return STUDY_START;
  if (iso > STUDY_END) return STUDY_END;
  return iso;
}

export function commitDay(value: string, current: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return current;
  return clampDay(value);
}

function utcDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function iso(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function addDays(day: string, amount: number): string {
  const date = utcDate(day);
  date.setUTCDate(date.getUTCDate() + amount);
  return iso(date);
}

export function calendarWeek(day: string): { from: string; to: string } {
  const mondayOffset = (utcDate(day).getUTCDay() + 6) % 7;
  const monday = addDays(day, -mondayOffset);
  return { from: monday, to: addDays(monday, 6) };
}

export function weekWindow(day: string): { from: string; to: string } {
  const week = calendarWeek(day);
  return { from: clampDay(week.from), to: clampDay(week.to) };
}

export function deskContext(day: string, mode: WindowMode, deadline: string): string {
  const range = accuracyWindow(day, mode);
  const windowText = mode === "january" ? "1–31 January 2026" : formatRange(range.from, range.to);
  return `Deadline ${deadline}. The score uses the latest forecast already published by then. Accuracy window: ${windowText}.`;
}

export function windowDescription(day: string, mode: WindowMode): string {
  const range = accuracyWindow(day, mode);
  if (mode === "day") {
    return `This score covers ${formatDay(range.from)} only.`;
  }
  if (mode === "january") {
    return "This score covers every delivery day from 1 January 2026 through 31 January 2026, including days where some hours cannot be matched.";
  }
  const week = calendarWeek(day);
  const dates = formatRange(range.from, range.to);
  if (week.from !== range.from || week.to !== range.to) {
    return `The calendar week is ${formatRange(week.from, week.to)}. Only January delivery dates are scored, so this window is ${dates}.`;
  }
  return `This score covers the calendar week ${dates}, Monday to Sunday.`;
}

export function accuracyHeading(mode: WindowMode): string {
  if (mode === "day") return "Accuracy for this delivery day";
  if (mode === "week") return "Accuracy for this week";
  return "Accuracy for all of January 2026";
}

export function accuracyScopeNote(mode: WindowMode): string {
  if (mode === "day") {
    return "These scores use the decision deadline for the selected day. They stay on that rule even if a different forecast version is pinned above.";
  }
  if (mode === "week") {
    return "These scores cover the week containing the selected day. The cards and chart above stay on that one day.";
  }
  return "These scores cover every delivery day from 1 to 31 January 2026. The cards and chart above stay on the selected day.";
}

export function accuracyWindow(day: string, mode: WindowMode): { from: string; to: string } {
  if (mode === "day") return { from: day, to: day };
  if (mode === "january") return { from: STUDY_START, to: STUDY_END };
  return weekWindow(day);
}

export function formatDay(day: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(utcDate(day));
}

export function formatRange(from: string, to: string): string {
  if (from === to) return formatDay(from);
  return `${formatDay(from)} – ${formatDay(to)}`;
}
