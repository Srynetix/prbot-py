from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sentry_sdk import set_tag

from prbot.core.commands.commands import CommandContext, SetQa
from prbot.core.models import ExternalAccount, QaStatus
from prbot.core.sync.processor import SyncProcessor
from prbot.injection import inject_instance
from prbot.server.authentication import get_current_user

router = APIRouter()
logger = structlog.get_logger(__name__)


class QaStatusRequest(BaseModel):
    repository_path: str
    pull_request_numbers: list[int]
    author: str
    status: bool | None


@router.post("/external/set-qa-status")
async def set_qa_status(
    external_account: Annotated[ExternalAccount, Depends(get_current_user)],
    qa_status_request: QaStatusRequest,
) -> Response:
    sync_processor = inject_instance(SyncProcessor)

    # Create a command and send it
    qa_status = QaStatus.Waiting
    if qa_status_request.status is True:
        qa_status = QaStatus.Pass
    elif qa_status_request.status is False:
        qa_status = QaStatus.Fail

    logger.info(
        "External QA status modification",
        qa_status=qa_status,
        external_account=external_account.username,
        author=qa_status_request.author,
        repository_path=qa_status_request.repository_path,
    )

    set_tag("external_account", external_account.username)
    set_tag("author", qa_status_request.author)
    set_tag("repository_path", qa_status_request.repository_path)

    # Note: This code only supports a list of PR numbers on a specific repository,
    #       not PR numbers on various repositories.
    owner, name = qa_status_request.repository_path.split("/")
    for pull_request_number in qa_status_request.pull_request_numbers:
        ctx = CommandContext(
            owner=owner,
            name=name,
            number=pull_request_number,
            author=qa_status_request.author,
            command=None,
            comment_id=None,
        )
        qa_command = SetQa(qa_status)
        await qa_command.process(ctx)

        # Sync!
        await sync_processor.process(
            owner=owner, name=name, number=pull_request_number, force_creation=False
        )

    return Response(status_code=204)
