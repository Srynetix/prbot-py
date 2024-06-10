from typing import Any

from sentry_sdk import set_tag
from structlog import get_logger

from prbot.core.commands.processor import CommandProcessor
from prbot.core.models import RepositoryPath
from prbot.core.sync.processor import SyncProcessor
from prbot.core.webhooks.models import GhEventType
from prbot.injection import inject_instance
from prbot.modules.github.client import GitHubClient
from prbot.modules.github.models import GhPullRequestAction, GhRepository
from prbot.modules.github.webhooks.models import (
    GhCheckSuiteEvent,
    GhIssueCommentEvent,
    GhPingEvent,
    GhPullRequestEvent,
    GhReviewEvent,
)
from prbot.modules.lock import LockClient

logger = get_logger(__name__)


class EventProcessorBase:
    def _add_repository_tag_to_sentry(self, repository: GhRepository) -> None:
        set_tag(
            "repository_path",
            RepositoryPath(owner=repository.owner.login, name=repository.name),
        )


class PingEventProcessor(EventProcessorBase):
    async def process(self, event: GhPingEvent) -> None:
        logger.info("Processing PingEvent...", payload=event)


class PullRequestEventProcessor(EventProcessorBase):
    _api: GitHubClient
    _lock: LockClient
    _sync_processor: SyncProcessor

    def __init__(self) -> None:
        self._api = inject_instance(GitHubClient)
        self._lock = inject_instance(LockClient)
        self._sync_processor = inject_instance(SyncProcessor)

    async def process(self, event: GhPullRequestEvent) -> None:
        logger.info("Processing PullRequestEvent", payload=event)
        self._add_repository_tag_to_sentry(event.repository)

        await self._api.setup_client_for_repository(
            owner=event.repository.owner.login, name=event.repository.name
        )

        # Ignore sync on specific actions
        if event.action in [
            GhPullRequestAction.Assigned,
            GhPullRequestAction.Labeled,
            GhPullRequestAction.Unlabeled,
            GhPullRequestAction.Unassigned,
        ]:
            return

        await self._sync_processor.process(
            owner=event.repository.owner.login,
            name=event.repository.name,
            number=event.pull_request.number,
            force_creation=event.action == GhPullRequestAction.Opened,
        )


class CheckSuiteEventProcessor(EventProcessorBase):
    _api: GitHubClient
    _sync_processor: SyncProcessor

    def __init__(self) -> None:
        self._api = inject_instance(GitHubClient)
        self._sync_processor = inject_instance(SyncProcessor)

    async def process(self, event: GhCheckSuiteEvent) -> None:
        logger.info("Processing CheckSuiteEvent", payload=event)
        self._add_repository_tag_to_sentry(event.repository)

        await self._api.setup_client_for_repository(
            owner=event.repository.owner.login, name=event.repository.name
        )

        for pull_request in event.check_suite.pull_requests:
            await self._sync_processor.process(
                owner=event.repository.owner.login,
                name=event.repository.name,
                number=pull_request.number,
                force_creation=False,
            )


class IssueCommentEventProcessor(EventProcessorBase):
    _api: GitHubClient
    _sync_processor: SyncProcessor

    def __init__(self) -> None:
        self._api = inject_instance(GitHubClient)
        self._sync_processor = inject_instance(SyncProcessor)

    async def process(self, event: GhIssueCommentEvent) -> None:
        logger.info("Processing IssueCommentEvent", payload=event)
        self._add_repository_tag_to_sentry(event.repository)

        await self._api.setup_client_for_repository(
            owner=event.repository.owner.login, name=event.repository.name
        )

        needs_sync = False

        # Try to parse each line as a command
        command_processor = CommandProcessor()
        for line in event.comment.body.splitlines():
            output = await command_processor.process(
                owner=event.repository.owner.login,
                name=event.repository.name,
                number=event.issue.number,
                author=event.comment.user.login,
                command=line,
                comment_id=event.comment.id,
            )

            if output.needs_sync:
                needs_sync = True

        if needs_sync:
            await self._sync_processor.process(
                owner=event.repository.owner.login,
                name=event.repository.name,
                number=event.issue.number,
                force_creation=False,
            )


class ReviewEventProcessor(EventProcessorBase):
    _api: GitHubClient
    _sync_processor: SyncProcessor

    def __init__(self) -> None:
        self._api = inject_instance(GitHubClient)
        self._sync_processor = inject_instance(SyncProcessor)

    async def process(self, event: GhReviewEvent) -> None:
        logger.info("Processing ReviewEvent", payload=event)
        self._add_repository_tag_to_sentry(event.repository)

        await self._api.setup_client_for_repository(
            owner=event.repository.owner.login, name=event.repository.name
        )

        await self._sync_processor.process(
            owner=event.repository.owner.login,
            name=event.repository.name,
            number=event.pull_request.number,
            force_creation=False,
        )


class EventProcessor:
    async def process_event(
        self, event_type: GhEventType, body: dict[str, Any]
    ) -> None:
        if event_type == GhEventType.Ping:
            await PingEventProcessor().process(GhPingEvent.model_validate(body))
        elif event_type == GhEventType.CheckSuite:
            await CheckSuiteEventProcessor().process(
                GhCheckSuiteEvent.model_validate(body)
            )
        elif event_type == GhEventType.IssueComment:
            await IssueCommentEventProcessor().process(
                GhIssueCommentEvent.model_validate(body)
            )
        elif event_type == GhEventType.PullRequest:
            await PullRequestEventProcessor().process(
                GhPullRequestEvent.model_validate(body)
            )
        elif event_type == GhEventType.PullRequestReview:
            await ReviewEventProcessor().process(GhReviewEvent.model_validate(body))
        else:
            print("Unhandled event type.")
