"""Foregate API."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.clients.elexon import ElexonClient
from app.core.config import Settings, get_settings
from app.services.analytics import AnalyticsService


def create_app(settings: Settings | None = None, client: ElexonClient | None = None) -> FastAPI:
    active = settings or get_settings()
    logging.basicConfig(
        level=getattr(logging, active.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owns_client = client is None
        app.state.settings = active
        app.state.client = client or ElexonClient(active)
        app.state.service = AnalyticsService(app.state.client, active)
        yield
        if owns_client:
            await app.state.client.aclose()

    app = FastAPI(title="Foregate API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
