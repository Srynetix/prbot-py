import pytest

from prbot.core.commit_status.builder import CommitStatusBuilder
from prbot.core.commit_status.processor import CommitStatusProcessor
from prbot.core.models import CheckStatus, QaStatus
from prbot.core.sync.sync_state import PullRequestSyncState
from prbot.modules.github.models import (
    GhCommitStatusState,
    GhMergeableState,
    GhReviewDecision,
)
from tests.conftest import get_fake_github_http_client
from tests.utils.http import HttpExpectation
from tests.utils.sync_state import dummy_sync_state

pytestmark = pytest.mark.anyio


def check(
    sync_state: PullRequestSyncState, message: str, state: GhCommitStatusState
) -> None:
    builder = CommitStatusBuilder()
    status_message = builder.build(sync_state=sync_state)
    assert status_message.message == message
    assert status_message.state == state


def test_wip() -> None:
    check(dummy_sync_state(wip=True), "PR is still in WIP", GhCommitStatusState.Pending)


def test_checks_failed() -> None:
    check(
        dummy_sync_state(check_status=CheckStatus.Fail),
        "Checks failed",
        GhCommitStatusState.Failure,
    )


def test_checks_waiting() -> None:
    check(
        dummy_sync_state(check_status=CheckStatus.Waiting),
        "Waiting for checks",
        GhCommitStatusState.Pending,
    )


def test_changes_required() -> None:
    check(
        dummy_sync_state(review_decision=GhReviewDecision.ChangesRequested),
        "Changes required",
        GhCommitStatusState.Failure,
    )


def test_not_mergeable() -> None:
    check(
        dummy_sync_state(mergeable_state=GhMergeableState.Conflicting),
        "PR is not mergeable yet",
        GhCommitStatusState.Pending,
    )


def test_reviews() -> None:
    check(
        dummy_sync_state(review_decision=GhReviewDecision.ReviewRequired),
        "Waiting on reviews",
        GhCommitStatusState.Pending,
    )


def test_qa_fail() -> None:
    check(
        dummy_sync_state(qa_status=QaStatus.Fail),
        "Did not pass QA",
        GhCommitStatusState.Failure,
    )


def test_qa_wait() -> None:
    check(
        dummy_sync_state(qa_status=QaStatus.Waiting),
        "Waiting for QA",
        GhCommitStatusState.Pending,
    )


def test_lock() -> None:
    check(
        dummy_sync_state(locked=True),
        "PR ready to merge, but is merge locked",
        GhCommitStatusState.Failure,
    )


def test_pr_title() -> None:
    check(
        dummy_sync_state(valid_pr_title=False),
        "PR title is not valid",
        GhCommitStatusState.Failure,
    )


def test_ok() -> None:
    check(dummy_sync_state(), "All good", GhCommitStatusState.Success)


async def test_processor() -> None:
    fake_github = get_fake_github_http_client()

    fake_github.expect(
        HttpExpectation()
        .with_input(
            method="POST",
            url="/repos/owner/name/statuses/123456",
            json={
                "state": "success",
                "description": "All good",
                "context": "Validation",
            },
        )
        .with_output_status(200)
    )

    processor = CommitStatusProcessor()
    await processor.process(sync_state=dummy_sync_state())
