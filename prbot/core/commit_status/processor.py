from typing import ClassVar

from prbot.core.sync.sync_state import PullRequestSyncState
from prbot.injection import inject_instance
from prbot.modules.github.client import GitHubClient

from .builder import CommitStatusBuilder


class CommitStatusProcessor:
    VALIDATION_STATUS_MESSAGE: ClassVar[str] = "Validation"

    _api: GitHubClient
    _builder: CommitStatusBuilder

    def __init__(self) -> None:
        self._api = inject_instance(GitHubClient)
        self._builder = CommitStatusBuilder()

    async def process(self, *, sync_state: PullRequestSyncState) -> None:
        status_msg = self._builder.build(sync_state=sync_state)

        await self._api.commit_statuses().update(
            owner=sync_state.owner,
            name=sync_state.name,
            commit_ref=sync_state.head_sha,
            state=status_msg.state,
            body=status_msg.message,
            title=status_msg.title,
        )
