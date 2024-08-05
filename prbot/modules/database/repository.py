import re
from abc import ABC, abstractmethod

import structlog

from prbot.core.models import (
    ExternalAccount,
    ExternalAccountRight,
    MergeRule,
    MergeStrategy,
    PullRequest,
    QaStatus,
    Repository,
    RepositoryRule,
    RuleBranch,
)

logger = structlog.get_logger()


class UnknownRepository(Exception):
    def __init__(self, *, owner: str, name: str) -> None:
        super().__init__(f"Unknown repository {owner}/{name}")


class UnknownPullRequest(Exception):
    def __init__(self, *, owner: str, name: str, number: int) -> None:
        super().__init__(f"Unknown pull request {owner}/{name} #{number}")


class UnknownExternalAccount(Exception):
    def __init__(self, *, username: str) -> None:
        super().__init__(f"Unknown external account {username}")


class UnknownExternalAccountRight(Exception):
    def __init__(self, *, owner: str, name: str, username: str) -> None:
        super().__init__(f"Unknown external account right {username} on {owner}/{name}")


class UnknownRepositoryRule(Exception):
    def __init__(self, *, owner: str, name: str, rule_name: str) -> None:
        super().__init__(f"Unknown repository rule {owner}/{name} named {rule_name}")


class UnknownMergeRule(Exception):
    def __init__(
        self, *, owner: str, name: str, base_branch: RuleBranch, head_branch: RuleBranch
    ) -> None:
        super().__init__(
            f"Unknown merge rule {owner}/{name} with base {base_branch} and head {head_branch}"
        )


class RepositoryDatabase(ABC):
    @abstractmethod
    async def all(self) -> list[Repository]: ...

    @abstractmethod
    async def create(self, repository: Repository) -> Repository: ...

    @abstractmethod
    async def update(self, repository: Repository) -> Repository: ...

    @abstractmethod
    async def delete(self, *, owner: str, name: str) -> bool: ...

    @abstractmethod
    async def get(self, *, owner: str, name: str) -> Repository | None: ...

    @abstractmethod
    async def set_default_strategy(
        self, *, owner: str, name: str, strategy: MergeStrategy
    ) -> None: ...

    @abstractmethod
    async def set_default_automerge(
        self, *, owner: str, name: str, value: bool
    ) -> None: ...

    @abstractmethod
    async def set_default_enable_qa(
        self, *, owner: str, name: str, value: bool
    ) -> None: ...

    @abstractmethod
    async def set_default_enable_checks(
        self, *, owner: str, name: str, value: bool
    ) -> None: ...

    @abstractmethod
    async def set_pr_title_validation_regex(
        self, *, owner: str, name: str, value: re.Pattern[str]
    ) -> None: ...

    @abstractmethod
    async def set_manual_interaction(
        self, *, owner: str, name: str, value: bool
    ) -> None: ...

    async def get_or_raise(self, *, owner: str, name: str) -> Repository:
        repository = await self.get(owner=owner, name=name)
        if repository is None:
            raise UnknownRepository(owner=owner, name=name)
        return repository

    async def create_or_update(self, repository: Repository) -> Repository:
        if (await self.get(owner=repository.owner, name=repository.name)) is not None:
            return await self.update(repository)
        else:
            return await self.create(repository)


class PullRequestDatabase(ABC):
    @abstractmethod
    async def all(self) -> list[PullRequest]: ...

    @abstractmethod
    async def filter(self, *, owner: str, name: str) -> list[PullRequest]: ...

    @abstractmethod
    async def get(
        self, *, owner: str, name: str, number: int
    ) -> PullRequest | None: ...

    @abstractmethod
    async def set_qa_status(
        self, *, owner: str, name: str, number: int, qa_status: QaStatus
    ) -> None: ...

    @abstractmethod
    async def set_checks_enabled(
        self, *, owner: str, name: str, number: int, value: bool
    ) -> None: ...

    @abstractmethod
    async def set_status_comment_id(
        self, *, owner: str, name: str, number: int, status_comment_id: int
    ) -> None: ...

    @abstractmethod
    async def set_merge_strategy(
        self, *, owner: str, name: str, number: int, strategy: MergeStrategy | None
    ) -> None: ...

    @abstractmethod
    async def set_automerge(
        self, *, owner: str, name: str, number: int, automerge: bool
    ) -> None: ...

    @abstractmethod
    async def set_locked(
        self, *, owner: str, name: str, number: int, locked: bool
    ) -> None: ...

    @abstractmethod
    async def update(self, pull_request: PullRequest) -> PullRequest: ...

    @abstractmethod
    async def create(self, pull_request: PullRequest) -> PullRequest: ...

    @abstractmethod
    async def delete(self, *, owner: str, name: str, number: int) -> bool: ...

    async def get_or_raise(self, *, owner: str, name: str, number: int) -> PullRequest:
        pull_request = await self.get(owner=owner, name=name, number=number)
        if pull_request is None:
            raise UnknownPullRequest(owner=owner, name=name, number=number)
        return pull_request

    async def create_or_update(self, pull_request: PullRequest) -> PullRequest:
        if (
            await self.get(
                owner=pull_request.repository_path.owner,
                name=pull_request.repository_path.name,
                number=pull_request.number,
            )
        ) is not None:
            return await self.update(pull_request)
        else:
            return await self.create(pull_request)


class MergeRuleDatabase(ABC):
    @abstractmethod
    async def all(self) -> list[MergeRule]: ...

    @abstractmethod
    async def create(self, merge_rule: MergeRule) -> MergeRule: ...

    @abstractmethod
    async def update(self, merge_rule: MergeRule) -> MergeRule: ...

    @abstractmethod
    async def filter(self, *, owner: str, name: str) -> list[MergeRule]: ...

    @abstractmethod
    async def delete(
        self, *, owner: str, name: str, base_branch: RuleBranch, head_branch: RuleBranch
    ) -> bool: ...

    @abstractmethod
    async def get(
        self, *, owner: str, name: str, base_branch: RuleBranch, head_branch: RuleBranch
    ) -> MergeRule | None: ...

    async def get_or_raise(
        self, *, owner: str, name: str, base_branch: RuleBranch, head_branch: RuleBranch
    ) -> MergeRule:
        merge_rule = await self.get(
            owner=owner, name=name, base_branch=base_branch, head_branch=head_branch
        )
        if merge_rule is None:
            raise UnknownMergeRule(
                owner=owner, name=name, base_branch=base_branch, head_branch=head_branch
            )
        return merge_rule

    async def create_or_update(self, merge_rule: MergeRule) -> MergeRule:
        if (
            await self.get(
                owner=merge_rule.repository_path.owner,
                name=merge_rule.repository_path.name,
                base_branch=merge_rule.base_branch,
                head_branch=merge_rule.head_branch,
            )
        ) is not None:
            return await self.update(merge_rule)
        else:
            return await self.create(merge_rule)


class RepositoryRuleDatabase(ABC):
    @abstractmethod
    async def all(self) -> list[RepositoryRule]: ...

    @abstractmethod
    async def filter(self, *, owner: str, name: str) -> list[RepositoryRule]: ...

    @abstractmethod
    async def create(self, repository_rule: RepositoryRule) -> RepositoryRule: ...

    @abstractmethod
    async def update(self, repository_rule: RepositoryRule) -> RepositoryRule: ...

    @abstractmethod
    async def delete(self, *, owner: str, name: str, rule_name: str) -> bool: ...

    @abstractmethod
    async def get(
        self, *, owner: str, name: str, rule_name: str
    ) -> RepositoryRule | None: ...

    async def get_or_raise(
        self, *, owner: str, name: str, rule_name: str
    ) -> RepositoryRule:
        repository_rule = await self.get(owner=owner, name=name, rule_name=rule_name)
        if repository_rule is None:
            raise UnknownRepositoryRule(owner=owner, name=name, rule_name=rule_name)
        return repository_rule

    async def create_or_update(self, repository_rule: RepositoryRule) -> RepositoryRule:
        if (
            await self.get(
                owner=repository_rule.repository_path.owner,
                name=repository_rule.repository_path.name,
                rule_name=repository_rule.name,
            )
        ) is not None:
            return await self.update(repository_rule)
        else:
            return await self.create(repository_rule)


class ExternalAccountDatabase(ABC):
    @abstractmethod
    async def all(self) -> list[ExternalAccount]: ...

    @abstractmethod
    async def get(self, *, username: str) -> ExternalAccount | None: ...

    @abstractmethod
    async def create(self, external_account: ExternalAccount) -> ExternalAccount: ...

    @abstractmethod
    async def update(self, external_account: ExternalAccount) -> ExternalAccount: ...

    @abstractmethod
    async def delete(self, *, username: str) -> bool: ...

    async def get_or_raise(self, *, username: str) -> ExternalAccount:
        external_account = await self.get(username=username)
        if external_account is None:
            raise UnknownExternalAccount(username=username)
        return external_account

    async def create_or_update(
        self, external_account: ExternalAccount
    ) -> ExternalAccount:
        if (
            await self.get(
                username=external_account.username,
            )
        ) is not None:
            return await self.update(external_account)
        else:
            return await self.create(external_account)


class ExternalAccountRightDatabase(ABC):
    @abstractmethod
    async def all(self) -> list[ExternalAccountRight]: ...

    @abstractmethod
    async def create(self, right: ExternalAccountRight) -> ExternalAccountRight: ...

    @abstractmethod
    async def delete(self, *, owner: str, name: str, username: str) -> bool: ...

    @abstractmethod
    async def get(
        self, *, owner: str, name: str, username: str
    ) -> ExternalAccountRight | None: ...

    @abstractmethod
    async def filter(self, *, username: str) -> list[ExternalAccountRight]: ...

    async def get_or_raise(
        self, *, owner: str, name: str, username: str
    ) -> ExternalAccountRight:
        right = await self.get(owner=owner, name=name, username=username)
        if right is None:
            raise UnknownExternalAccountRight(owner=owner, name=name, username=username)
        return right

    async def get_or_create(self, right: ExternalAccountRight) -> ExternalAccountRight:
        existing = await self.get(
            owner=right.repository_path.owner,
            name=right.repository_path.name,
            username=right.username,
        )
        if existing is None:
            return await self.create(right)
        return existing
