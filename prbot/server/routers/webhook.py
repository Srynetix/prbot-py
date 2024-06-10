import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from prbot.config.settings import get_global_settings
from prbot.core.webhooks.models import GhEventType
from prbot.core.webhooks.processor import EventProcessor
from prbot.server.crypto import compute_hash

router = APIRouter()


async def parse_webhook_request(request: Request) -> tuple[GhEventType, dict[str, Any]]:
    # Validate webhook signature
    github_event = request.headers.get("X-GitHub-Event", "")
    if github_event == "":
        # Missing GitHub event
        raise HTTPException(status_code=412, detail="Missing X-GitHub-Event header")

    try:
        event_type = GhEventType(github_event)
    except ValueError:
        raise HTTPException(status_code=412, detail="Unsupported X-GitHub-Event header")

    body_signature = request.headers.get("X-Hub-Signature-256", "")
    if body_signature == "":
        # Missing signature
        raise HTTPException(
            status_code=412, detail="Missing X-Hub-Signature-256 header"
        )

    body = await request.body()
    _, hash_value = body_signature.split("=")

    computed_hash = compute_hash(
        key=get_global_settings().github_webhook_secret, message=body
    )
    if computed_hash != hash_value:
        # Signature does not match
        raise HTTPException(
            status_code=412,
            detail="Body signature does not match the X-Hub-Signature-256 header",
        )

    json_body = json.loads(body)
    return event_type, json_body


@router.post("/webhook")
async def webhook(request: Request) -> Response:
    event_type, json_body = await parse_webhook_request(request)

    processor = EventProcessor()
    await processor.process_event(event_type, json_body)

    return JSONResponse(status_code=200, content={"message": "OK"})
