"""One-off live check against the running API. Not part of the unit suite."""

from __future__ import annotations

import json
import urllib.request


def get(path: str) -> dict:
    with urllib.request.urlopen("http://127.0.0.1:8000" + path, timeout=120) as response:
        return json.load(response)


def main() -> None:
    health = get("/api/health")
    print("health", health["status"])
    day = get("/api/forecasts?settlement_date=2026-01-15&cutoff_profile=epex_60min")
    summary = day["summary"]
    print(
        "epex",
        summary["n_matched"],
        summary["n_expected"],
        round(summary["mae_mw"], 1),
        round(summary["rmse_mw"], 1),
        round(summary["bias_mw"], 1),
        round(summary["mean_forecast_mw"], 1),
        round(summary["mean_actual_mw"], 1),
        day["uniform_publish_label"],
        day["metadata"]["cache"],
        day["metadata"]["warnings"],
    )
    first = day["periods"][0]
    print("hour0", first["label"], first["forecast_mw"], first["actual_mw"], first["error_mw"], first["forecast_publish_label"])
    print("halves", [(item["label"], item["generation_mw"]) for item in first["half_hours"]])
    print("evo", len(day["evolution"]["points"]))
    nord = get("/api/overview?settlement_from=2026-01-15&settlement_to=2026-01-15&cutoff_profile=nordpool_60min")
    print(
        "nord",
        nord["summary"]["n_matched"],
        round(nord["summary"]["mae_mw"], 1),
        round(nord["summary"]["bias_mw"], 1),
    )


if __name__ == "__main__":
    main()
