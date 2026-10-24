"""HTTP routes. Calculations stay in the service layer."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request

from app.clients.elexon import ElexonError
from app.core.time import iso_z
from app.schemas.responses import AccuracyResponse, ForecastResponse, HealthResponse, OverviewResponse
from app.services.analytics import AnalyticsService

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="foregate-api", time=iso_z(datetime.now(timezone.utc)))


@router.get("/api/overview", response_model=OverviewResponse)
async def overview(
    request: Request,
    settlement_from: date = Query(..., description="First settlement date, YYYY-MM-DD"),
    settlement_to: date = Query(..., description="Last settlement date, inclusive"),
    cutoff_profile: str = Query("epex_60min"),
    cutoff_time: str | None = Query(None, description="UK local gate HH:MM. Required for custom."),
    publish_time: datetime | None = Query(None, description="Exact forecast issue. Overrides the gate."),
    refresh: bool = Query(False),
) -> OverviewResponse:
    _check_range(request, settlement_from, settlement_to)
    service: AnalyticsService = request.app.state.service
    payload = await _call(
        service.overview(
            settlement_from,
            settlement_to,
            cutoff_profile,
            cutoff_time,
            publish_time,
            refresh,
        )
    )
    return OverviewResponse.model_validate(payload)


@router.get("/api/forecasts", response_model=ForecastResponse)
async def forecasts(
    request: Request,
    settlement_date: date = Query(...),
    cutoff_profile: str = Query("epex_60min"),
    cutoff_time: str | None = Query(None),
    publish_time: datetime | None = Query(None),
    start_time: datetime | None = Query(None, description="Delivery hour to inspect, UTC"),
    refresh: bool = Query(False),
) -> ForecastResponse:
    _check_range(request, settlement_date, settlement_date)
    service: AnalyticsService = request.app.state.service
    payload = await _call(
        service.forecasts(
            settlement_date,
            cutoff_profile,
            cutoff_time,
            publish_time,
            start_time,
            refresh,
        )
    )
    return ForecastResponse.model_validate(payload)


@router.get("/api/accuracy", response_model=AccuracyResponse)
async def accuracy(
    request: Request,
    settlement_from: date = Query(...),
    settlement_to: date = Query(...),
    cutoff_profile: str = Query("epex_60min"),
    cutoff_time: str | None = Query(None),
    refresh: bool = Query(False),
) -> AccuracyResponse:
    _check_range(request, settlement_from, settlement_to)
    service: AnalyticsService = request.app.state.service
    payload = await _call(
        service.accuracy(settlement_from, settlement_to, cutoff_profile, cutoff_time, refresh)
    )
    return AccuracyResponse.model_validate(payload)


def _check_range(request: Request, settlement_from: date, settlement_to: date) -> None:
    settings = request.app.state.settings
    if settlement_to < settlement_from:
        raise HTTPException(status_code=422, detail="settlement_to must be on or after settlement_from")
    inclusive_days = (settlement_to - settlement_from).days + 1
    if inclusive_days > settings.max_range_days:
        raise HTTPException(
            status_code=422,
            detail=f"Date range cannot exceed {settings.max_range_days} days",
        )


async def _call(coro: object) -> dict[str, object]:
    try:
        result = await coro  # type: ignore[misc]
    except ElexonError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result
