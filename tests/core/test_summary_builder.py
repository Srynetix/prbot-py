import pytest

from prbot.core.models import (
    CheckStatus,
    MergeStrategy,
    QaStatus,
    RepositoryPath,
    RepositoryRule,
)
from prbot.core.summary.builder import SummaryBuilder
from prbot.core.sync.sync_state import PullRequestSyncState
from prbot.modules.github.models import GhReviewDecision
from tests.utils.sync_state import dummy_sync_state

pytestmark = pytest.mark.anyio


def repository_rule(*, name: str) -> RepositoryRule:
    return RepositoryRule(
        repository_path=RepositoryPath(owner="owner", name="name"),
        name=name,
        actions=[],
        conditions=[],
    )


@pytest.mark.parametrize(
    "valid,output",
    [
        (
            True,
            "> - :speech_balloon: **Title validation**: _valid!_ :heavy_check_mark:",
        ),
        (False, "> - :speech_balloon: **Title validation**: _invalid!_ :x:"),
    ],
)
async def test_rules_valid_title_message(valid: bool, output: str) -> None:
    builder = SummaryBuilder()
    assert builder._generate_rules_valid_title_message(valid_pr_title=valid) == output


@pytest.mark.parametrize(
    "rgx,output",
    [
        (r"[0-9]+", ">   - _Rule_: [0-9]+"),
        ("", ">   - _Rule_: None"),
    ],
)
async def test_rules_title_regex_message(rgx: str, output: str) -> None:
    builder = SummaryBuilder()
    assert builder._generate_rules_title_regex_message(title_regex=rgx) == output


@pytest.mark.parametrize(
    "rules,output",
    [
        ([], "> - :straight_ruler: **Pull request rules**: _None_"),
        (
            [repository_rule(name="Foo"), repository_rule(name="Bar")],
            "> - :straight_ruler: **Pull request rules**: _Foo, Bar_",
        ),
    ],
)
async def test_rules_rule_list_message(
    rules: list[RepositoryRule], output: str
) -> None:
    builder = SummaryBuilder()
    assert builder._generate_rules_rule_list_message(rules=rules) == output


@pytest.mark.parametrize(
    "strategy,output",
    [
        (
            MergeStrategy.Merge,
            "> - :twisted_rightwards_arrows: **Merge strategy**: _Merge_",
        ),
        (
            MergeStrategy.Rebase,
            "> - :twisted_rightwards_arrows: **Merge strategy**: _Rebase_",
        ),
    ],
)
async def test_rules_merge_strategy_message(
    strategy: MergeStrategy, output: str
) -> None:
    builder = SummaryBuilder()
    assert builder._generate_rules_merge_strategy_message(strategy=strategy) == output


@pytest.mark.parametrize(
    "wip,output",
    [
        (False, "> - :construction: **WIP?**: No :heavy_check_mark:"),
        (True, "> - :construction: **WIP?**: Yes :x:"),
    ],
)
async def test_checks_wip_message(wip: bool, output: str) -> None:
    builder = SummaryBuilder()
    assert builder._generate_checks_wip_message(wip=wip) == output


@pytest.mark.parametrize(
    "status,output",
    [
        (CheckStatus.Fail, "> - :checkered_flag: **Checks**: _failed_. :x:"),
        (
            CheckStatus.Pass,
            "> - :checkered_flag: **Checks**: _passed_! :heavy_check_mark:",
        ),
        (CheckStatus.Waiting, "> - :checkered_flag: **Checks**: _waiting_... :clock2:"),
        (
            CheckStatus.Skipped,
            "> - :checkered_flag: **Checks**: _skipped_. :heavy_check_mark:",
        ),
    ],
)
async def test_checks_check_message(status: CheckStatus, output: str) -> None:
    builder = SummaryBuilder()
    assert builder._generate_checks_check_message(check_status=status) == output


@pytest.mark.parametrize(
    "sync_state,output",
    [
        (
            dummy_sync_state(review_decision=GhReviewDecision.ReviewRequired),
            "> - :mag: **Code reviews**: _waiting..._ :clock2:",
        ),
        (
            dummy_sync_state(review_decision=GhReviewDecision.ChangesRequested),
            "> - :mag: **Code reviews**: _waiting on change requests..._ :x:",
        ),
        (
            dummy_sync_state(review_decision=GhReviewDecision.Approved),
            "> - :mag: **Code reviews**: _passed!_ :heavy_check_mark:",
        ),
        (
            dummy_sync_state(review_decision=None),
            "> - :mag: **Code reviews**: _skipped._ :heavy_check_mark:",
        ),
    ],
)
async def test_checks_review_message(
    sync_state: PullRequestSyncState, output: str
) -> None:
    builder = SummaryBuilder()
    assert builder._generate_checks_review_message(sync_state=sync_state) == output


@pytest.mark.parametrize(
    "status,output",
    [
        (QaStatus.Fail, "> - :test_tube: **QA**: _failed_. :x:"),
        (QaStatus.Pass, "> - :test_tube: **QA**: _passed_! :heavy_check_mark:"),
        (QaStatus.Waiting, "> - :test_tube: **QA**: _waiting_... :clock2:"),
        (QaStatus.Skipped, "> - :test_tube: **QA**: _skipped_. :heavy_check_mark:"),
    ],
)
async def test_checks_qa_message(status: QaStatus, output: str) -> None:
    builder = SummaryBuilder()
    assert builder._generate_checks_qa_message(qa_status=status) == output


@pytest.mark.parametrize(
    "locked,output",
    [
        (True, "> - :lock: **Locked?**: Yes :x:"),
        (False, "> - :lock: **Locked?**: No :heavy_check_mark:"),
    ],
)
async def test_checks_lock_message(locked: bool, output: str) -> None:
    builder = SummaryBuilder()
    assert builder._generate_checks_lock_message(locked=locked) == output


@pytest.mark.parametrize(
    "sync_state,output",
    [
        (
            dummy_sync_state(mergeable=True),
            "> - :twisted_rightwards_arrows: **Mergeable?**: Yes :heavy_check_mark:",
        ),
        (
            dummy_sync_state(merged=True),
            "> - :twisted_rightwards_arrows: **Mergeable?**: Yes :heavy_check_mark:",
        ),
        (
            dummy_sync_state(mergeable=False, merged=False),
            "> - :twisted_rightwards_arrows: **Mergeable?**: No :x:",
        ),
    ],
)
async def test_checks_mergeable_message(
    sync_state: PullRequestSyncState, output: str
) -> None:
    builder = SummaryBuilder()
    assert builder._generate_checks_mergeable_message(sync_state=sync_state) == output


@pytest.mark.parametrize(
    "automerge,output",
    [
        (True, "> - :twisted_rightwards_arrows: **Automerge**: Yes :heavy_check_mark:"),
        (False, "> - :twisted_rightwards_arrows: **Automerge**: No :x:"),
    ],
)
async def test_config_automerge_message(automerge: bool, output: str) -> None:
    builder = SummaryBuilder()
    assert builder._generate_config_automerge_message(automerge=automerge) == output
