from unittest import mock

import inject
import pytest

from prbot.core.commands.processor import CommandProcessor
from prbot.core.sync.processor import SyncProcessor
from prbot.core.webhooks.models import GhEventType
from prbot.core.webhooks.processor import EventProcessor
from prbot.modules.github.models import (
    GhPullRequestAction,
)
from tests.conftest import InjectorFixture
from tests.utils.webhooks.webhooks import GhEventBuilder

pytestmark = pytest.mark.anyio


async def test_ping_event() -> None:
    event = GhEventBuilder().ping().with_zen("HEY").build()

    processor = EventProcessor()
    await processor.process_event(GhEventType.Ping, event.model_dump())


async def test_pull_request_opened(
    injector: InjectorFixture,
) -> None:
    event = (
        GhEventBuilder().pull_request().with_action(GhPullRequestAction.Opened).build()
    )
    event.pull_request.body = "Test.\nbot qa+"

    mock_step_processor = mock.AsyncMock(SyncProcessor)
    mock_command_processor = mock.AsyncMock(CommandProcessor)

    def config(binder: inject.Binder) -> None:
        binder.bind(SyncProcessor, mock_step_processor)
        binder.bind(CommandProcessor, mock_command_processor)

    injector(config)

    processor = EventProcessor()
    await processor.process_event(GhEventType.PullRequest, event.model_dump())

    # Make sure we sync
    assert mock_step_processor.process.called
    assert mock_command_processor.process.called
