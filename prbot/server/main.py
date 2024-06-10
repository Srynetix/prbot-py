from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware
from tortoise.contrib.fastapi import RegisterTortoise

from prbot.config.log import setup_logging
from prbot.config.sentry import setup_sentry
from prbot.injection import setup
from prbot.modules.database.settings import get_orm_configuration
from prbot.server.routers import crash as crash_router
from prbot.server.routers import external as external_router
from prbot.server.routers import health as health_router
from prbot.server.routers import index as index_router
from prbot.server.routers import webhook as webhook_router

from .middleware import logging_middleware

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    setup_sentry()
    instrumentator.expose(app)

    async with RegisterTortoise(
        app,
        config=get_orm_configuration(),
        add_exception_handlers=True,
    ):
        setup.setup_injections()
        yield


app = FastAPI(title="prbot", lifespan=lifespan)
instrumentator = Instrumentator().instrument(app)

app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)

app.include_router(index_router.router)
app.include_router(crash_router.router)
app.include_router(external_router.router)
app.include_router(health_router.router)
app.include_router(webhook_router.router)
