import datetime
import re
from typing import Any, Callable, Coroutine

import pytest

from prbot.core.models import (
    CheckStatus,
    MergeRule,
    MergeStrategy,
    NamedRuleBranch,
    PullRequest,
    QaStatus,
    Repository,
    RepositoryRule,
    RuleActionSetAutomerge,
    RuleActionSetChecksEnabled,
    RuleActionSetQaStatus,
    RuleConditionAuthor,
    RuleConditionBaseBranch,
    RuleConditionHeadBranch,
    WildcardRuleBranch,
)
from prbot.core.sync.sync_state import (
    PullRequestSyncState,
    PullRequestSyncStateBuilderImplementation,
)
from prbot.injection import inject_instance
from prbot.modules.database.repository import (
    MergeRuleDatabase,
    PullRequestDatabase,
    RepositoryDatabase,
    RepositoryRuleDatabase,
    UnknownPullRequest,
    UnknownRepository,
)
from prbot.modules.github.models import (
    GhApiCheckSuiteResponse,
    GhApplication,
    GhBranch,
    GhBranchShort,
    GhCheckConclusion,
    GhCheckRun,
    GhCheckStatus,
    GhPullRequest,
    GhPullRequestShort,
    GhPullRequestState,
    GhReviewDecision,
    GhUser,
)
from tests.conftest import get_fake_github_http_client
from tests.utils.github import dummy_gh_check_run, dummy_gh_pull_request
from tests.utils.http import HttpExpectation
from tests.utils.sync_state import dummy_sync_state

pytestmark = pytest.mark.anyio


async def test_no_repo() -> None:
    builder = PullRequestSyncStateBuilderImplementation()

    with pytest.raises(UnknownRepository):
        await builder.build(owner="owner", name="name", number=1)


async def test_no_pr() -> None:
    repository_db = inject_instance(RepositoryDatabase)
    await repository_db.create(Repository(owner="owner", name="name"))

    builder = PullRequestSyncStateBuilderImplementation()

    with pytest.raises(UnknownPullRequest):
        await builder.build(owner="owner", name="name", number=1)


async def test_checks_skipped() -> None:
    fake_github = get_fake_github_http_client()

    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)

    repository = await repository_db.create(Repository(owner="owner", name="name"))
    await pull_request_db.create(
        PullRequest(
            repository_path=repository.path(),
            number=1,
            checks_enabled=False,
        )
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="POST", url="/graphql", json=HttpExpectation.IGNORE)
        .with_output_status(200)
        .with_output_json(
            {"data": {"repository": {"pullRequest": {"reviewDecision": "APPROVED"}}}}
        )
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/owner/name/pulls/1")
        .with_output_status(200)
        .with_output_model(dummy_gh_pull_request())
    )

    builder = PullRequestSyncStateBuilderImplementation()
    sync_state = await builder.build(owner="owner", name="name", number=1)

    assert sync_state == dummy_sync_state(
        status_comment_id=0,
        qa_status=QaStatus.Waiting,
        check_status=CheckStatus.Skipped,
    )


async def test_checks_empty() -> None:
    fake_github = get_fake_github_http_client()
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)

    repository = await repository_db.create(Repository(owner="owner", name="name"))

    await pull_request_db.create(
        PullRequest(
            repository_path=repository.path(),
            number=1,
            checks_enabled=True,
        )
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/owner/name/commits/123456/check-runs")
        .with_input_params(per_page=100, page=1)
        .with_output_status(200)
        .with_output_model(GhApiCheckSuiteResponse(check_runs=[]))
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="POST", url="/graphql", json=HttpExpectation.IGNORE)
        .with_output_status(200)
        .with_output_json(
            {"data": {"repository": {"pullRequest": {"reviewDecision": "APPROVED"}}}}
        )
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/owner/name/pulls/1")
        .with_output_status(200)
        .with_output_model(dummy_gh_pull_request())
    )

    builder = PullRequestSyncStateBuilderImplementation()
    sync_state = await builder.build(owner="owner", name="name", number=1)

    assert sync_state == dummy_sync_state(
        status_comment_id=0,
        qa_status=QaStatus.Waiting,
        check_status=CheckStatus.Waiting,
    )


async def test_strategy_override() -> None:
    fake_github = get_fake_github_http_client()
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)

    repository = await repository_db.create(Repository(owner="owner", name="name"))
    await pull_request_db.create(
        PullRequest(
            repository_path=repository.path(),
            number=1,
            checks_enabled=False,
            strategy_override=MergeStrategy.Rebase,
        )
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="POST", url="/graphql", json=HttpExpectation.IGNORE)
        .with_output_status(200)
        .with_output_json(
            {"data": {"repository": {"pullRequest": {"reviewDecision": "APPROVED"}}}}
        )
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/owner/name/pulls/1")
        .with_output_status(200)
        .with_output_model(dummy_gh_pull_request())
    )

    builder = PullRequestSyncStateBuilderImplementation()
    sync_state = await builder.build(owner="owner", name="name", number=1)

    assert sync_state == dummy_sync_state(
        status_comment_id=0,
        check_status=CheckStatus.Skipped,
        merge_strategy=MergeStrategy.Rebase,
        qa_status=QaStatus.Waiting,
    )


async def test_sync_state_builder() -> None:
    fake_github = get_fake_github_http_client()
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)
    merge_rule_db = inject_instance(MergeRuleDatabase)
    repository_rule_db = inject_instance(RepositoryRuleDatabase)

    repository = await repository_db.create(
        Repository(
            owner="owner", name="name", pr_title_validation_regex=re.compile("[0-9]+")
        )
    )

    await pull_request_db.create(
        PullRequest(
            repository_path=repository.path(),
            number=1,
            checks_enabled=True,
            automerge=False,
        )
    )

    await merge_rule_db.create(
        MergeRule(
            repository_path=repository.path(),
            base_branch=NamedRuleBranch(value="foo"),
            head_branch=NamedRuleBranch(value="bar"),
            strategy=MergeStrategy.Rebase,
        )
    )

    rule1 = await repository_rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name="Rule1",
            conditions=[RuleConditionAuthor(value="foo")],
            actions=[RuleActionSetAutomerge(value=True)],
        )
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/owner/name/commits/654321/check-runs")
        .with_input_params(per_page=100, page=1)
        .with_output_status(200)
        .with_output_model(
            GhApiCheckSuiteResponse(
                check_runs=[
                    GhCheckRun(
                        id=1,
                        name="FOO",
                        head_sha="654321",
                        status=GhCheckStatus.Completed,
                        conclusion=GhCheckConclusion.Failure,
                        pull_requests=[
                            GhPullRequestShort(
                                number=1,
                                base=GhBranchShort(ref="foo", sha="123456"),
                                head=GhBranchShort(ref="bar", sha="654321"),
                            )
                        ],
                        app=GhApplication(
                            name="foo", slug="foo", owner=GhUser(login="foo")
                        ),
                        started_at=datetime.datetime.now(datetime.timezone.utc),
                    )
                ]
            )
        )
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="POST", url="/graphql", json=HttpExpectation.IGNORE)
        .with_output_status(200)
        .with_output_json(
            {
                "data": {
                    "repository": {
                        "pullRequest": {"reviewDecision": "CHANGES_REQUESTED"}
                    }
                }
            }
        )
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(method="GET", url="/repos/owner/name/pulls/1")
        .with_output_status(200)
        .with_output_model(
            GhPullRequest(
                number=1,
                title="Foobar",
                user=GhUser(login="foo"),
                state=GhPullRequestState.Open,
                base=GhBranch(
                    ref="foo",
                    sha="123456",
                ),
                body=None,
                locked=False,
                created_at=datetime.datetime.now(datetime.timezone.utc),
                updated_at=datetime.datetime.now(datetime.timezone.utc),
                requested_reviewers=[],
                labels=[],
                draft=False,
                head=GhBranch(ref="bar", sha="654321"),
            )
        )
    )

    builder = PullRequestSyncStateBuilderImplementation()
    sync_state = await builder.build(owner="owner", name="name", number=1)

    assert sync_state == PullRequestSyncState(
        owner="owner",
        name="name",
        title="Foobar",
        number=1,
        status_comment_id=0,
        check_status=CheckStatus.Fail,
        check_url="https://github.com/owner/name/pull/1/checks",
        qa_status=QaStatus.Waiting,
        rules=[rule1],
        review_decision=GhReviewDecision.ChangesRequested,
        title_regex="[0-9]+",
        valid_pr_title=False,
        locked=False,
        wip=False,
        automerge=True,
        mergeable=True,
        merged=False,
        merge_strategy=MergeStrategy.Rebase,
        head_sha="654321",
    )


async def test_resolve_repository_rules() -> None:
    async def check(pr: GhPullRequest, rules: list[RepositoryRule]) -> None:
        builder = PullRequestSyncStateBuilderImplementation()
        assert (
            await builder._resolve_repository_rules(
                owner="owner", name="name", upstream_pr=pr
            )
        ) == rules

    repository_db = inject_instance(RepositoryDatabase)
    repository_rule_db = inject_instance(RepositoryRuleDatabase)

    repository = await repository_db.create(Repository(owner="owner", name="name"))

    rule1 = await repository_rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name="Rule1",
            conditions=[RuleConditionAuthor(value="foo")],
            actions=[RuleActionSetAutomerge(value=True)],
        )
    )

    rule2 = await repository_rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name="Rule2",
            conditions=[RuleConditionHeadBranch(value=NamedRuleBranch(value="foo"))],
            actions=[RuleActionSetAutomerge(value=True)],
        )
    )

    rule3 = await repository_rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name="Rule3",
            conditions=[RuleConditionBaseBranch(value=WildcardRuleBranch())],
            actions=[RuleActionSetAutomerge(value=True)],
        )
    )

    rule4 = await repository_rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name="Rule4",
            conditions=[RuleConditionHeadBranch(value=WildcardRuleBranch())],
            actions=[RuleActionSetAutomerge(value=True)],
        )
    )

    await repository_rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name="Rule5",
            conditions=[RuleConditionHeadBranch(value=NamedRuleBranch(value="nop"))],
            actions=[RuleActionSetAutomerge(value=True)],
        )
    )

    await repository_rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name="Rule6",
            conditions=[RuleConditionBaseBranch(value=NamedRuleBranch(value="nop"))],
            actions=[RuleActionSetAutomerge(value=True)],
        )
    )

    await repository_rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name="Rule7",
            conditions=[RuleConditionAuthor(value="nop")],
            actions=[RuleActionSetAutomerge(value=True)],
        )
    )

    await repository_rule_db.create(
        RepositoryRule(
            repository_path=repository.path(),
            name="Rule8",
            conditions=[],
            actions=[RuleActionSetAutomerge(value=True)],
        )
    )

    await check(
        dummy_gh_pull_request(head=GhBranch(ref="foo", sha="123456")),
        [rule1, rule2, rule3, rule4],
    )


async def test_filter_last_check_runs() -> None:
    def check(runs: list[GhCheckRun], last: list[GhCheckRun]) -> None:
        builder = PullRequestSyncStateBuilderImplementation()
        assert (builder._filter_last_check_runs(runs)) == last

    run_a1 = dummy_gh_check_run(
        name="a", started_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00Z")
    )
    run_a2 = dummy_gh_check_run(
        name="a", started_at=datetime.datetime.fromisoformat("2020-03-01T00:00:00Z")
    )
    run_a3 = dummy_gh_check_run(
        name="a", started_at=datetime.datetime.fromisoformat("2020-02-01T00:00:00Z")
    )
    run_b1 = dummy_gh_check_run(
        name="b", started_at=datetime.datetime.fromisoformat("2020-03-01T01:00:00Z")
    )
    run_b2 = dummy_gh_check_run(
        name="b", started_at=datetime.datetime.fromisoformat("2020-02-01T00:00:00Z")
    )
    run_b3 = dummy_gh_check_run(
        name="b", started_at=datetime.datetime.fromisoformat("2020-03-01T00:00:00Z")
    )

    check([run_a1, run_a2, run_a3, run_b1, run_b2, run_b3], [run_a2, run_b1])


async def test_merge_check_run_statuses() -> None:
    def check(runs: list[GhCheckRun], status: CheckStatus) -> None:
        builder = PullRequestSyncStateBuilderImplementation()
        assert (builder._merge_check_run_statuses(runs)) == status

    check([dummy_gh_check_run(conclusion=GhCheckConclusion.Failure)], CheckStatus.Fail)

    check(
        [
            dummy_gh_check_run(conclusion=GhCheckConclusion.Failure),
            dummy_gh_check_run(conclusion=GhCheckConclusion.Success),
        ],
        CheckStatus.Fail,
    )

    check(
        [
            dummy_gh_check_run(conclusion=GhCheckConclusion.Failure),
            dummy_gh_check_run(conclusion=None),
        ],
        CheckStatus.Fail,
    )

    check(
        [
            dummy_gh_check_run(conclusion=GhCheckConclusion.Success),
            dummy_gh_check_run(conclusion=None),
        ],
        CheckStatus.Waiting,
    )

    check([dummy_gh_check_run(conclusion=None)], CheckStatus.Waiting)

    check([], CheckStatus.Waiting)


class TestApplyRules:
    @pytest.fixture
    async def repository(self) -> Repository:
        repo_db = inject_instance(RepositoryDatabase)
        return await repo_db.create(Repository(owner="owner", name="name"))

    @pytest.fixture
    async def setup(
        self, repository: Repository
    ) -> Callable[..., Coroutine[Any, Any, PullRequest]]:
        async def inner(**kwargs: Any) -> PullRequest:
            pr_db = inject_instance(PullRequestDatabase)
            return await pr_db.create(
                PullRequest(repository_path=repository.path(), number=1, **kwargs)
            )

        return inner

    async def test_automerge_change(
        self,
        repository: Repository,
        setup: Callable[..., Coroutine[Any, Any, PullRequest]],
    ) -> None:
        builder = PullRequestSyncStateBuilderImplementation()
        pull_request = await builder._apply_rules(
            owner="owner",
            name="name",
            pull_request=await setup(automerge=False),
            rules=[
                RepositoryRule(
                    repository_path=repository.path(),
                    name="Foo",
                    conditions=[],
                    actions=[RuleActionSetAutomerge(value=True)],
                )
            ],
        )

        assert pull_request.automerge is True

        pull_request = await builder._apply_rules(
            owner="owner",
            name="name",
            pull_request=pull_request,
            rules=[
                RepositoryRule(
                    repository_path=repository.path(),
                    name="Foo",
                    conditions=[],
                    actions=[RuleActionSetAutomerge(value=False)],
                )
            ],
        )

        assert pull_request.automerge is False

    async def test_automerge_no_change(
        self,
        repository: Repository,
        setup: Callable[..., Coroutine[Any, Any, PullRequest]],
    ) -> None:
        builder = PullRequestSyncStateBuilderImplementation()
        pull_request = await builder._apply_rules(
            owner="owner",
            name="name",
            pull_request=await setup(automerge=True),
            rules=[
                RepositoryRule(
                    repository_path=repository.path(),
                    name="Foo",
                    conditions=[],
                    actions=[RuleActionSetAutomerge(value=True)],
                )
            ],
        )

        assert pull_request.automerge is True

    async def test_qa_status_change(
        self,
        repository: Repository,
        setup: Callable[..., Coroutine[Any, Any, PullRequest]],
    ) -> None:
        builder = PullRequestSyncStateBuilderImplementation()
        pull_request = await builder._apply_rules(
            owner="owner",
            name="name",
            pull_request=await setup(qa_status=QaStatus.Waiting),
            rules=[
                RepositoryRule(
                    repository_path=repository.path(),
                    name="Foo",
                    conditions=[],
                    actions=[RuleActionSetQaStatus(value=QaStatus.Skipped)],
                )
            ],
        )

        assert pull_request.qa_status == QaStatus.Skipped

    async def test_qa_status_no_change(
        self,
        repository: Repository,
        setup: Callable[..., Coroutine[Any, Any, PullRequest]],
    ) -> None:
        builder = PullRequestSyncStateBuilderImplementation()
        pull_request = await builder._apply_rules(
            owner="owner",
            name="name",
            pull_request=await setup(qa_status=QaStatus.Skipped),
            rules=[
                RepositoryRule(
                    repository_path=repository.path(),
                    name="Foo",
                    conditions=[],
                    actions=[RuleActionSetQaStatus(value=QaStatus.Skipped)],
                )
            ],
        )

        assert pull_request.qa_status == QaStatus.Skipped

    async def test_checks_enabled_change(
        self,
        repository: Repository,
        setup: Callable[..., Coroutine[Any, Any, PullRequest]],
    ) -> None:
        builder = PullRequestSyncStateBuilderImplementation()
        pull_request = await builder._apply_rules(
            owner="owner",
            name="name",
            pull_request=await setup(checks_enabled=False),
            rules=[
                RepositoryRule(
                    repository_path=repository.path(),
                    name="Foo",
                    conditions=[],
                    actions=[RuleActionSetChecksEnabled(value=True)],
                )
            ],
        )

        assert pull_request.checks_enabled is True

    async def test_checks_enabled_no_change(
        self,
        repository: Repository,
        setup: Callable[..., Coroutine[Any, Any, PullRequest]],
    ) -> None:
        builder = PullRequestSyncStateBuilderImplementation()
        pull_request = await builder._apply_rules(
            owner="owner",
            name="name",
            pull_request=await setup(checks_enabled=True),
            rules=[
                RepositoryRule(
                    repository_path=repository.path(),
                    name="Foo",
                    conditions=[],
                    actions=[RuleActionSetChecksEnabled(value=True)],
                )
            ],
        )

        assert pull_request.checks_enabled is True
