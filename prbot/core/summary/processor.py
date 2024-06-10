import structlog

from prbot.core.sync.sync_state import PullRequestSyncState
from prbot.injection import inject_instance
from prbot.modules.database.repository import PullRequestDatabase
from prbot.modules.github.client import GitHubClient
from prbot.modules.lock import LockClient, LockException

from .builder import SummaryBuilder

logger = structlog.get_logger()


class SummaryProcessor:
    _api: GitHubClient
    _lock: LockClient
    _pull_request_db: PullRequestDatabase
    _builder: SummaryBuilder

    def __init__(self) -> None:
        self._api = inject_instance(GitHubClient)
        self._lock = inject_instance(LockClient)
        self._pull_request_db = inject_instance(PullRequestDatabase)
        self._builder = SummaryBuilder()

    async def process(self, *, sync_state: PullRequestSyncState) -> str | None:
        owner = sync_state.owner
        name = sync_state.name
        number = sync_state.number

        if sync_state.status_comment_id > 0:
            summary = self._builder.build(sync_state=sync_state)
            await self._api.issues().update_comment(
                owner=owner,
                name=name,
                comment_id=sync_state.status_comment_id,
                message=summary,
            )
            return summary

        else:
            try:
                async with self._lock.lock(f"summary.{owner}.{name}.{number}"):
                    summary = self._builder.build(sync_state=sync_state)
                    comment_id = await self._api.issues().create_comment(
                        owner=owner, name=name, number=number, message=summary
                    )
                    await self._pull_request_db.set_status_comment_id(
                        owner=owner,
                        name=name,
                        number=number,
                        status_comment_id=comment_id,
                    )
                    return summary

            except LockException:
                logger.error(
                    "Could not obtain lock to create initial summary message. Skipping.",
                    exc_info=True,
                )

                return None
