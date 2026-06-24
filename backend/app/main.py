"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app import __version__
from app.api.v1 import api_v1_router
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_engine
from app.deps import close_redis
from app.settings import get_settings

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    log.info(
        "app.startup",
        env=settings.app_env,
        cors_origins=settings.app_cors_origins,
        riot_keys_loaded=len(settings.riot_api_keys),
    )
    try:
        yield
    finally:
        log.info("app.shutdown.begin")
        await close_redis()
        await dispose_engine()
        log.info("app.shutdown.done")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="LOL Helper API",
        version=__version__,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": "lolhelper",
            "version": __version__,
            "docs": "/docs" if not settings.is_production else "disabled",
        }

    return app


app = create_app()
