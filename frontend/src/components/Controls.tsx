import type { Publication, CutoffProfile } from "../types/api";
import { STUDY_END, STUDY_START, deskContext, formatDay, windowDescription, type WindowMode } from "../lib/dates";

interface ControlsProps {
  deliveryDate: string;
  windowMode: WindowMode;
  profile: CutoffProfile;
  customTime: string;
  publish: string;
  publications: Publication[];
  citation?: string | null;
  onDeliveryDate: (value: string) => void;
  onWindowMode: (value: WindowMode) => void;
  onProfile: (value: CutoffProfile) => void;
  onCustomTime: (value: string) => void;
  onPublish: (value: string) => void;
}

export function Controls({
  deliveryDate,
  windowMode,
  profile,
  customTime,
  publish,
  publications,
  citation,
  onDeliveryDate,
  onWindowMode,
  onProfile,
  onCustomTime,
  onPublish,
}: ControlsProps) {
  const groups = new Map<string, Publication[]>();
  for (const item of publications) {
    const day = formatDay(item.publish_time.slice(0, 10));
    const list = groups.get(day) ?? [];
    list.push(item);
    groups.set(day, list);
  }

  return (
    <div className="desk-controls">
      <form className="controls" aria-label="Desk controls">
        <label className="field">
          <span>Delivery day</span>
          <input
            type="date"
            min={STUDY_START}
            max={STUDY_END}
            value={deliveryDate}
            aria-describedby="delivery-help"
            onChange={(event) => onDeliveryDate(event.target.value)}
          />
        </label>
        <label className="field">
          <span>Decision deadline</span>
          <select
            value={profile}
            aria-describedby="deadline-help"
            onChange={(event) => onProfile(event.target.value as CutoffProfile)}
          >
            <option value="epex_60min">09:20 UK time, day before delivery</option>
            <option value="nordpool_60min">09:50 UK time, day before delivery</option>
            <option value="epex_30min">15:30 UK time, day before delivery</option>
            <option value="custom">A UK time I choose</option>
          </select>
        </label>
        {profile === "custom" ? (
          <label className="field">
            <span>Deadline, UK time</span>
            <input
              type="time"
              value={customTime}
              aria-describedby="deadline-help"
              onChange={(event) => {
                if (event.target.value) onCustomTime(event.target.value);
              }}
            />
          </label>
        ) : null}
        <label className="field">
          <span>Forecast version</span>
          <select value={publish} aria-describedby="version-help" onChange={(event) => onPublish(event.target.value)}>
            <option value="decision">Latest at the deadline</option>
            {[...groups.entries()].map(([day, items]) => (
              <optgroup key={day} label={day}>
                {items.map((item) => (
                  <option key={item.publish_time} value={item.publish_time}>
                    {issueLabel(item)}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Accuracy window</span>
          <select
            value={windowMode}
            aria-describedby="window-help"
            onChange={(event) => onWindowMode(event.target.value as WindowMode)}
          >
            <option value="day">This delivery day</option>
            <option value="week">Week containing this day</option>
            <option value="january">All of January 2026</option>
          </select>
        </label>
        <p className="cite context" id="desk-context">
          {deskContext(deliveryDate, windowMode, deadlinePhrase(profile, customTime))}
        </p>
        <details className="how">
          <summary>How this works</summary>
          <div className="how-grid">
            <div>
              <p className="how-label">Delivery days</p>
              <p id="delivery-help">
                Delivery days run from 1 to 31 January 2026. Forecasts published in late December 2025 are
                used when they cover an early January day. A version is listed only when it predicts at least
                one hour of the selected day. An earlier date is not missing data; that version does not reach
                this day.
              </p>
            </div>
            <div>
              <p className="how-label">Forecast versions</p>
              <p id="version-help">
                A forecast version is one published edition of the prediction. “Latest at the deadline” is the
                newest edition already published by the decision time. An edition published after the deadline
                can be inspected, but it is not used for the original decision-time score.
              </p>
            </div>
            <div>
              <p className="how-label">Accuracy window</p>
              <p id="window-help">
                {windowDescription(deliveryDate, windowMode)} The day, the week and January all use that same
                deadline.
              </p>
            </div>
            {citation ? (
              <div>
                <p className="how-label">This deadline</p>
                <p id="deadline-help">{citation}</p>
              </div>
            ) : null}
          </div>
        </details>
      </form>
    </div>
  );
}

function deadlinePhrase(profile: CutoffProfile, customTime: string): string {
  if (profile === "nordpool_60min") return "09:50 UK time, the day before delivery";
  if (profile === "epex_30min") return "15:30 UK time, the day before delivery";
  if (profile === "custom") return `${customTime || "the chosen"} UK time, the day before delivery`;
  return "09:20 UK time, the day before delivery";
}

function issueLabel(item: Publication): string {
  const timing = item.eligible ? "available before the deadline" : "published after the deadline";
  const used = item.used_for_delivery_hour ? " · used for this view" : "";
  const hours = item.hours_covered === 1 ? "1 hour" : `${item.hours_covered} hours`;
  return `${item.label} · ${timing}${used} · ${hours}`;
}
