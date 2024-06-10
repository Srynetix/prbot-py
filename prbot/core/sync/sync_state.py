import re
from abc import ABC, abstractmethod
from typing import cast

from pydantic import BaseModel

from prbot.core.models import (
    CheckStatus,
    MergeStrategy,
    NamedRuleBranch,
    PullRequest,
    QaStatus,
    RepositoryRule,
    RuleActionSetAutomerge,
    RuleActionSetChecksEnabled,
    RuleActionSetQaStatus,
    RuleBranch,
    RuleBranchFactory,
    RuleBranchType,
    RuleConditionAuthor,
    RuleConditionBaseBranch,
    RuleConditionHeadBranch,
    RuleConditionType,
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
from prbot.modules.github.client import GitHubClient
from prbot.modules.github.models import (
    GhCheckConclusion,
    GhCheckRun,
    GhPullRequest,
    GhReviewDecision,
)


class PullRequestSyncState(BaseModel):
    owner: str
    name: str
    number: int
    status_comment_id: int

    check_status: CheckStatus
    check_url: str
    qa_status: QaStatus

    rules: list[RepositoryRule]

    review_decision: GhReviewDecision | None

    title: str
    title_regex: str
    valid_pr_title: bool

    locked: bool
    wip: bool

    automerge: bool
    mergeable: bool
    merged: bool
    merge_strategy: MergeStrategy

    head_sha: str

    @property
    def changes_requested(self) -> bool:
        return self.review_decision == GhReviewDecision.ChangesRequested

    @property
    def review_required(self) -> bool:
        return self.review_decision == GhReviewDecision.ReviewRequired

    @property
    def review_skipped(self) -> bool:
        return self.review_decision is None


class PullRequestSyncStateBuilder(ABC):
    @abstractmethod
    async def build(
        self, *, owner: str, name: str, number: int
    ) -> PullRequestSyncState: ...


class PullRequestSyncStateBuilderImplementation(PullRequestSyncStateBuilder):
    _api: GitHubClient
    _repository_db: RepositoryDatabase
    _pull_request_db: PullRequestDatabase
    _rule_db: RepositoryRuleDatabase
    _merge_rule_db: MergeRuleDatabase

    def __init__(self) -> None:
        self._api = inject_instance(GitHubClient)
        self._repository_db = inject_instance(RepositoryDatabase)
        self._pull_request_db = inject_instance(PullRequestDatabase)
        self._rule_db = inject_instance(RepositoryRuleDatabase)
        self._merge_rule_db = inject_instance(MergeRuleDatabase)

    async def build(
        self, *, owner: str, name: str, number: int
    ) -> PullRequestSyncState:
        local_repository = await self._repository_db.get(owner=owner, name=name)
        if local_repository is None:
            raise UnknownRepository(owner=owner, name=name)

        local_pr = await self._pull_request_db.get(
            owner=owner, name=name, number=number
        )
        if local_pr is None:
            raise UnknownPullRequest(owner=owner, name=name, number=number)

        upstream_pr = await self._api.pull_requests().get(
            owner=owner, name=name, number=number
        )

        # Rules
        rules = await self._resolve_repository_rules(
            owner=owner, name=name, upstream_pr=upstream_pr
        )

        # Apply applicable rules
        local_pr = await self._apply_rules(
            owner=owner, name=name, pull_request=local_pr, rules=rules
        )

        # Status check
        if local_pr.checks_enabled:
            check_result = await self._get_checks_result(
                owner=owner, name=name, commit_sha=upstream_pr.head.sha
            )
        else:
            check_result = CheckStatus.Skipped

        # Strategy
        strategy = await self._get_merge_strategy(
            owner=owner,
            name=name,
            base_branch=RuleBranchFactory.from_str(upstream_pr.base.ref),
            head_branch=RuleBranchFactory.from_str(upstream_pr.head.ref),
            local_pull_request=local_pr,
        )

        # Reviews
        decision = await self._api.pull_requests().review_decision(
            owner=owner, name=name, number=number
        )

        return PullRequestSyncState(
            owner=owner,
            name=name,
            number=number,
            title=upstream_pr.title,
            status_comment_id=local_pr.status_comment_id,
            head_sha=upstream_pr.head.sha,
            check_status=check_result,
            check_url=self._get_checks_url(owner=owner, name=name, number=number),
            review_decision=decision,
            automerge=local_pr.automerge,
            locked=local_pr.locked,
            merge_strategy=strategy,
            mergeable=upstream_pr.mergeable
            if upstream_pr.mergeable is not None
            else True,
            merged=upstream_pr.merged is True,
            qa_status=local_pr.qa_status,
            rules=rules,
            title_regex=local_repository.pr_title_validation_regex.pattern,
            valid_pr_title=self._validate_pr_title(
                name=upstream_pr.title,
                pattern=local_repository.pr_title_validation_regex,
            ),
            wip=upstream_pr.draft,
        )

    def _validate_pr_title(self, *, name: str, pattern: re.Pattern[str]) -> bool:
        return pattern.match(name) is not None

    def _get_checks_url(self, *, owner: str, name: str, number: int) -> str:
        return f"https://github.com/{owner}/{name}/pull/{number}/checks"

    async def _apply_rules(
        self,
        *,
        owner: str,
        name: str,
        pull_request: PullRequest,
        rules: list[RepositoryRule],
    ) -> PullRequest:
        number = pull_request.number

        needs_pr_update = False
        for rule in rules:
            for action in rule.actions:
                if isinstance(action, RuleActionSetAutomerge):
                    if pull_request.automerge != action.value:
                        await self._pull_request_db.set_automerge(
                            owner=owner,
                            name=name,
                            number=number,
                            automerge=action.value,
                        )
                        needs_pr_update = True

                elif isinstance(action, RuleActionSetQaStatus):
                    if pull_request.qa_status != action.value:
                        await self._pull_request_db.set_qa_status(
                            owner=owner,
                            name=name,
                            number=number,
                            qa_status=action.value,
                        )
                        needs_pr_update = True

                elif isinstance(action, RuleActionSetChecksEnabled):
                    if pull_request.checks_enabled != action.value:
                        await self._pull_request_db.set_checks_enabled(
                            owner=owner, name=name, number=number, value=action.value
                        )
                        needs_pr_update = True

        if needs_pr_update:
            updated_pull_request = await self._pull_request_db.get(
                owner=owner, name=name, number=number
            )
            assert updated_pull_request is not None
            return updated_pull_request

        else:
            # Nothing changed.
            return pull_request

    async def _resolve_repository_rules(
        self, *, owner: str, name: str, upstream_pr: GhPullRequest
    ) -> list[RepositoryRule]:
        output = []
        rules = await self._rule_db.list(owner=owner, name=name)
        for rule in rules:
            # Ignore rule without actions or conditions
            if len(rule.actions) == 0 or len(rule.conditions) == 0:
                continue

            for condition in rule.conditions:
                if condition.type == RuleConditionType.Author:
                    author_condition = cast(RuleConditionAuthor, condition)
                    if author_condition.value != upstream_pr.user.login:
                        continue

                elif condition.type == RuleConditionType.BaseBranch:
                    base_condition = cast(RuleConditionBaseBranch, condition)
                    if base_condition.value.type == RuleBranchType.Named:
                        branch_name = cast(NamedRuleBranch, base_condition.value).value
                        if branch_name != upstream_pr.base.ref:
                            continue

                elif condition.type == RuleConditionType.HeadBranch:
                    head_condition = cast(RuleConditionHeadBranch, condition)
                    if head_condition.value.type == RuleBranchType.Named:
                        branch_name = cast(NamedRuleBranch, head_condition.value).value
                        if branch_name != upstream_pr.head.ref:
                            continue

                output.append(rule)

        return output

    async def _get_merge_strategy(
        self,
        *,
        owner: str,
        name: str,
        base_branch: RuleBranch,
        head_branch: RuleBranch,
        local_pull_request: PullRequest,
    ) -> MergeStrategy:
        if local_pull_request.strategy_override is not None:
            return local_pull_request.strategy_override

        # Compute
        merge_rule = await self._merge_rule_db.get(
            owner=owner, name=name, base_branch=base_branch, head_branch=head_branch
        )

        if merge_rule:
            return merge_rule.strategy

        return MergeStrategy.Merge

    async def _get_checks_result(
        self, *, owner: str, name: str, commit_sha: str
    ) -> CheckStatus:
        upstream_checks = await self._api.check_runs().for_commit(
            owner=owner, name=name, commit_sha=commit_sha
        )
        if len(upstream_checks) == 0:
            # No checks yet, wait.
            return CheckStatus.Waiting

        # Filter and merge check runs
        filtered = self._filter_last_check_runs(upstream_checks)
        return self._merge_check_run_statuses(filtered)

    def _filter_last_check_runs(self, check_runs: list[GhCheckRun]) -> list[GhCheckRun]:
        last_check_runs: dict[str, GhCheckRun] = {}

        for check_run in check_runs:
            if check_run.name not in last_check_runs:
                last_check_runs[check_run.name] = check_run
            else:
                existing_check_run = last_check_runs[check_run.name]
                if existing_check_run.started_at < check_run.started_at:
                    last_check_runs[check_run.name] = check_run

        return sorted(last_check_runs.values(), key=lambda value: value.name)

    def _merge_check_run_statuses(self, check_runs: list[GhCheckRun]) -> CheckStatus:
        current: CheckStatus | None = None

        for check_run in check_runs:
            if check_run.conclusion == GhCheckConclusion.Failure:
                # Instant fail
                return CheckStatus.Fail

            elif check_run.conclusion == GhCheckConclusion.Success:
                if current == CheckStatus.Pass or current is None:
                    current = CheckStatus.Pass

            elif check_run.conclusion is None:
                # Still waiting
                current = CheckStatus.Waiting

        if current is None:
            return CheckStatus.Waiting
        else:
            return current
