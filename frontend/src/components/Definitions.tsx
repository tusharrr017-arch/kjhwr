const TITLES: Record<string, string> = {
  error: "Error",
  absolute_error: "Absolute error",
  mae: "MAE",
  rmse: "RMSE",
  bias: "Bias",
  matched_hours: "Matched hours",
  percentage_error: "Percentage error",
  alignment: "Half-hours and hours",
  selection: "Decision deadline",
  procurement: "What this does not decide",
};

const ORDER = Object.keys(TITLES);

export function Definitions({ definitions }: { definitions?: Record<string, string> }) {
  if (!definitions) {
    return <p className="note">Metric definitions load with the Elexon records.</p>;
  }
  return (
    <dl className="defs">
      {ORDER.filter((key) => definitions[key]).map((key) => (
        <div key={key}>
          <dt>{TITLES[key]}</dt>
          <dd>{definitions[key]}</dd>
        </div>
      ))}
    </dl>
  );
}
