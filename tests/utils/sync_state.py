from typing import Any

from prbot.core.models import CheckStatus, MergeStrategy, QaStatus
from prbot.core.sync.sync_state import PullRequestSyncState, PullRequestSyncStateBuilder
from prbot.modules.github.models import (
    GhMergeableState,
    GhMergeStateStatus,
    GhReviewDecision,
)


def dummy_sync_state(**kwargs: Any) -> PullRequestSyncState:
    sync_state = PullRequestSyncState(
        owner="owner",
        name="name",
        number=1,
        title="Foobar",
        status_comment_id=1,
        check_status=CheckStatus.Pass,
        check_url="https://github.com/owner/name/pull/1/checks",
        head_sha="123456",
        locked=False,
        merge_strategy=MergeStrategy.Merge,
        mergeable_state=GhMergeableState.Mergeable,
        merge_state_status=GhMergeStateStatus.Clean,
        merged=False,
        qa_status=QaStatus.Pass,
        review_decision=GhReviewDecision.Approved,
        automerge=False,
        rules=[],
        title_regex="",
        valid_pr_title=True,
        wip=False,
    )

    for k, v in kwargs.items():
        setattr(sync_state, k, v)

    return sync_state


def create_local_builder(state: PullRequestSyncState) -> PullRequestSyncStateBuilder:
    class LocalBuilder(PullRequestSyncStateBuilder):
        async def build(
            self, *, owner: str, name: str, number: int
        ) -> PullRequestSyncState:
            return state

    return LocalBuilder()
