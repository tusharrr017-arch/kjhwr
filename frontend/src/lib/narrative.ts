import type { Evolution } from "../types/api";
import { formatMw, formatSignedMw } from "./format";

export function evolutionSentence(evolution: Evolution): string {
  if (!evolution.points.length) {
    return "No forecast issue in the retrieved archive covers this hour.";
  }
  const selected = evolution.points.find((point) => point.selected);
  const earliest = evolution.points[0];
  const latest = evolution.points[evolution.points.length - 1];
  const sentences: string[] = [];
  if (selected) {
    sentences.push(`The scored issue, ${selected.label}, forecast ${formatMw(selected.generation_mw)}.`);
  } else {
    sentences.push("This hour has no forecast under the current selection.");
  }
  if (earliest.publish_time !== latest.publish_time) {
    const movement = latest.generation_mw - earliest.generation_mw;
    sentences.push(
      `From the earliest issue to the last, the forecast moved ${formatSignedMw(movement, 0)}.`,
    );
  }
  if (evolution.actual_mw == null) {
    sentences.push("A complete actual is not available for this hour.");
  } else {
    sentences.push(`Actual generation was ${formatMw(evolution.actual_mw)}.`);
  }
  sentences.push(
    `Versions published at or before ${evolution.cutoff_label} were available at the decision deadline. Later versions are shown for comparison only.`,
  );
  return sentences.join(" ");
}
