from __future__ import annotations

import asyncio
import importlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import disasters, hotspots, notifications
from app.core.config import settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def _build_lifespan(start_scanner: bool):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(level=logging.INFO)
        task = None
        if start_scanner:
            from app.modules.disaster_scanner.broadcaster import (
                stream_consumer_worker,
            )

            logger.info("Starting disaster stream worker")
            task = asyncio.create_task(stream_consumer_worker())

        yield

        if task is not None:
            logger.info("Stopping disaster stream worker")
            task.cancel()

    return lifespan


def create_app(
    *,
    include_existing_routers: bool = False,
    start_scanner: bool = False,
) -> FastAPI:
    app = FastAPI(
        title="Disaster Adviser API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=_build_lifespan(start_scanner),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    app.include_router(disasters.router)
    app.include_router(hotspots.router)
    app.include_router(notifications.router)
    app.include_router(notifications.api_router)

    if include_existing_routers:
        router_specs = [
            ("auth", "router"),
            ("oauth", "router"),
            ("calendar", "router"),
            ("user", "router"),
        ]
        for module_name, attr_name in router_specs:
            try:
                module = importlib.import_module(
                    f"app.api.routers.{module_name}",
                )
                app.include_router(getattr(module, attr_name))
            except ModuleNotFoundError as exc:
                logger.warning(
                    "Skipping router %s because dependency is missing: %s",
                    module_name,
                    exc,
                )

    return app
