"""FastAPI application factory for VERITAS AI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.routes import router
from .core.config import get_settings
from .core.exceptions import register_exception_handlers
from .core.logging import logger, setup_logging
from .core.security import ApiKeyMiddleware, RateLimitMiddleware
from .database.database import Base, engine
from .database.models import Analysis  # noqa: F401

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Create tables for local/dev (Alembic is used for managed migrations).
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured at %s", settings.database_url.split("@")[-1])
    except Exception as exc:  # noqa: BLE001
        logger.error("Database initialisation failed: %s", exc)
    # Do NOT load the model at startup — first request pays the cost; keeps
    # boot fast and avoids OOM in workers that never serve inference.
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="VERITAS AI API",
        description=(
            "Transformer-powered fake news & misinformation detection. "
            "Predictions are statistical estimates, not factual verdicts."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)
    app.add_middleware(ApiKeyMiddleware)

    register_exception_handlers(app)
    app.include_router(router, prefix=settings.api_prefix)
    return app


app = create_app()
