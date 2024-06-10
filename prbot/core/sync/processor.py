import enum
from abc import ABC, abstractmethod

import structlog
from pydantic import BaseModel

from prbot.core.commit_status.processor import CommitStatusProcessor
from prbot.core.models import PullRequest, QaStatus, Repository, RepositoryPath
from prbot.core.step.models import StepLabel
from prbot.core.step.processor import StepLabelProcessor
from prbot.core.summary.processor import SummaryProcessor
from prbot.injection import inject_instance
from prbot.modules.database.repository import PullRequestDatabase, RepositoryDatabase
from prbot.modules.github.client import GitHubClient
from prbot.modules.lock import LockClient, LockException

from .sync_state import PullRequestSyncState, PullRequestSyncStateBuilder

logger = structlog.get_logger()


class SyncProcessorResultState(enum.StrEnum):
    Success = "success"
    Skipped = "skipped"


class SyncProcessorResult(BaseModel):
    state: SyncProcessorResultState


class SyncProcessorResultSuccess(SyncProcessorResult):
    state: SyncProcessorResultState = SyncProcessorResultState.Success
    sync_state: PullRequestSyncState
    step_label: StepLabel
    summary: str | None


class SyncProcessorResultSkipped(SyncProcessorResult):
    state: SyncProcessorResultState = SyncProcessorResultState.Skipped


class SyncProcessor(ABC):
    @abstractmethod
    async def process(
        self, *, owner: str, name: str, number: int, force_creation: bool
    ) -> SyncProcessorResult: ...


class SyncProcessorImplementation(SyncProcessor):
    _api: GitHubClient
    _lock: LockClient
    _repository_db: RepositoryDatabase
    _pull_request_db: PullRequestDatabase
    _sync_state_builder: PullRequestSyncStateBuilder

    def __init__(self) -> None:
        self._api = inject_instance(GitHubClient)
        self._lock = inject_instance(LockClient)
        self._repository_db = inject_instance(RepositoryDatabase)
        self._pull_request_db = inject_instance(PullRequestDatabase)
        self._sync_state_builder = inject_instance(PullRequestSyncStateBuilder)

    async def process(
        self, *, owner: str, name: str, number: int, force_creation: bool
    ) -> SyncProcessorResult:
        logger.info("Synchronizing pull request", owner=owner, name=name, number=number)
        await self._api.setup_client_for_repository(owner=owner, name=name)

        repository = await self._repository_db.get(owner=owner, name=name)
        if repository is None:
            upstream_repository = await self._api.repositories().get(
                owner=owner, name=name
            )
            repository = Repository(
                owner=upstream_repository.owner.login, name=upstream_repository.name
            )
            repository = await self._repository_db.create(repository)

        pull_request = await self._pull_request_db.get(
            owner=owner, name=name, number=number
        )
        if pull_request is None:
            if repository.manual_interaction and not force_creation:
                logger.info(
                    "Not syncing pull request because of manual interaction settings",
                    owner=owner,
                    name=name,
                    number=number,
                )
                return SyncProcessorResultSkipped()

            # Synchronize pull request
            pull_request = PullRequest(
                repository_path=RepositoryPath(
                    owner=repository.owner, name=repository.name
                ),
                number=number,
                automerge=repository.default_automerge,
                checks_enabled=repository.default_enable_checks,
                qa_status=QaStatus.Waiting
                if repository.default_enable_qa
                else QaStatus.Skipped,
            )
            pull_request = await self._pull_request_db.create(pull_request)

        # Generate sync state
        sync_state = await self._sync_state_builder.build(
            owner=owner, name=name, number=number
        )

        # Update PR commit status
        commit_status_processor = CommitStatusProcessor()
        await commit_status_processor.process(sync_state=sync_state)

        # Generate step label
        step_processor = StepLabelProcessor()
        step_label = await step_processor.process(sync_state=sync_state)

        # Update summary comment
        summary_processor = SummaryProcessor()
        summary = await summary_processor.process(sync_state=sync_state)

        # Handle automerge
        if (
            sync_state.automerge
            and step_label == StepLabel.AwaitingMerge
            and not sync_state.merged
        ):
            try:
                async with self._lock.lock(f"automerge.{owner}.{name}.{number}"):
                    await self._api.pull_requests().merge(
                        owner=owner,
                        name=name,
                        number=number,
                        strategy=sync_state.merge_strategy,
                        commit_title=f"{sync_state.title} (#{number})",
                        commit_message="",
                    )
            except LockException:
                logger.error(
                    "Could not obtain lock to merge pull request. Skipping.",
                    exc_info=True,
                )
            except Exception:
                logger.error(
                    "Something bad happened while merging pull request. Disabling automerge.",
                    exc_info=True,
                )

                # Disable automerge on error
                await self._pull_request_db.set_automerge(
                    owner=owner, name=name, number=number, automerge=False
                )

        return SyncProcessorResultSuccess(
            sync_state=sync_state, step_label=step_label, summary=summary
        )
