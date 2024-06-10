import uuid
from typing import Any, Callable

import structlog
from fastapi import Request
from sentry_sdk import set_context


async def logging_middleware(request: Request, call_next: Callable[..., Any]) -> Any:
    # Generate request UUID
    request_uuid = uuid.uuid4()

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_uuid=str(request_uuid))

    # Add request to Sentry
    set_context("request", {"uuid": str(request_uuid)})

    return await call_next(request)
