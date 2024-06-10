import pytest

from prbot.core.models import CheckStatus, QaStatus
from prbot.core.step.builder import StepLabelBuilder
from prbot.core.step.models import StepLabel
from prbot.core.step.processor import StepLabelProcessor
from prbot.core.sync.sync_state import PullRequestSyncState
from prbot.modules.github.models import GhLabelsResponse, GhReviewDecision
from tests.conftest import get_fake_github_http_client
from tests.utils.http import HttpExpectation
from tests.utils.sync_state import dummy_sync_state

pytestmark = pytest.mark.anyio


def check(sync_state: PullRequestSyncState, label: StepLabel) -> None:
    assert StepLabelBuilder().build(sync_state=sync_state) == label


def test_wip() -> None:
    check(dummy_sync_state(wip=True), StepLabel.Wip)


def test_awaiting_checks() -> None:
    check(dummy_sync_state(check_status=CheckStatus.Waiting), StepLabel.AwaitingChecks)


def test_awaiting_review() -> None:
    check(
        dummy_sync_state(review_decision=GhReviewDecision.ReviewRequired),
        StepLabel.AwaitingReview,
    )


def test_awaiting_qa() -> None:
    check(dummy_sync_state(qa_status=QaStatus.Waiting), StepLabel.AwaitingQa)


def test_locked() -> None:
    check(dummy_sync_state(locked=True), StepLabel.Locked)


def test_awaiting_merge() -> None:
    check(dummy_sync_state(), StepLabel.AwaitingMerge)


def test_awaiting_changes() -> None:
    check(dummy_sync_state(mergeable=False), StepLabel.AwaitingChanges)
    check(dummy_sync_state(qa_status=QaStatus.Fail), StepLabel.AwaitingChanges)
    check(dummy_sync_state(valid_pr_title=False), StepLabel.AwaitingChanges)
    check(dummy_sync_state(check_status=CheckStatus.Fail), StepLabel.AwaitingChanges)


async def test_processor() -> None:
    fake_github = get_fake_github_http_client()

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/owner/name/issues/1/labels")
        .with_input_params(per_page=100, page=1)
        .with_output_status(200)
        .with_output_models([GhLabelsResponse(name="foo")])
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="PUT", url="/repos/owner/name/issues/1/labels")
        .with_input_json({"labels": ["foo", "step/awaiting-merge"]})
        .with_output_status(200)
    )

    processor = StepLabelProcessor()
    await processor.process(sync_state=dummy_sync_state())
