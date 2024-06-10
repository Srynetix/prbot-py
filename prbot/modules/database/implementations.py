import re

import structlog
from tortoise.transactions import atomic

from prbot.core.models import (
    ExternalAccount,
    ExternalAccountRight,
    MergeRule,
    MergeStrategy,
    PullRequest,
    QaStatus,
    Repository,
    RepositoryPath,
    RepositoryRule,
    RuleActionFactory,
    RuleBranch,
    RuleBranchFactory,
    RuleConditionFactory,
)

from .models import (
    ExternalAccountModel,
    ExternalAccountRightModel,
    MergeRuleModel,
    PullRequestModel,
    RepositoryModel,
    RepositoryRuleModel,
)
from .repository import (
    ExternalAccountDatabase,
    ExternalAccountRightDatabase,
    MergeRuleDatabase,
    PullRequestDatabase,
    RepositoryDatabase,
    RepositoryRuleDatabase,
    UnknownExternalAccount,
    UnknownMergeRule,
    UnknownPullRequest,
    UnknownRepository,
    UnknownRepositoryRule,
)

logger = structlog.get_logger()


class RepositoryDatabaseImplementation(RepositoryDatabase):
    async def all(self) -> list[Repository]:
        return [self._model_to_domain(repo) for repo in await RepositoryModel.all()]

    async def create(self, repository: Repository) -> Repository:
        logger.info("Creating repository", repository=repository)

        await RepositoryModel.create(
            name=repository.name,
            owner=repository.owner,
            manual_interaction=repository.manual_interaction,
            pr_title_validation_regex=repository.pr_title_validation_regex.pattern,
            default_strategy=repository.default_strategy.value,
            default_automerge=repository.default_automerge,
            default_enable_qa=repository.default_enable_qa,
            default_enable_checks=repository.default_enable_checks,
        )

        return await self.get_or_raise(owner=repository.owner, name=repository.name)

    async def update(self, repository: Repository) -> Repository:
        logger.info("Updating repository", repository=repository)

        model = await RepositoryModel.select_for_update().get(
            name=repository.name, owner=repository.owner
        )
        model.manual_interaction = repository.manual_interaction
        model.pr_title_validation_regex = repository.pr_title_validation_regex.pattern
        model.default_strategy = repository.default_strategy
        model.default_enable_qa = repository.default_enable_qa
        model.default_enable_checks = repository.default_enable_checks
        await model.save()

        return await self.get_or_raise(owner=repository.owner, name=repository.name)

    async def get(self, *, owner: str, name: str) -> Repository | None:
        model = await RepositoryModel.get_or_none(owner=owner, name=name)
        if model is not None:
            return self._model_to_domain(model)

        return None

    @atomic()
    async def set_default_strategy(
        self, *, owner: str, name: str, strategy: MergeStrategy
    ) -> None:
        await self._raise_on_missing(owner, name)

        model = await RepositoryModel.select_for_update().get(owner=owner, name=name)

        model.default_strategy = strategy.value
        await model.save(update_fields=["default_strategy"])

    @atomic()
    async def set_default_automerge(
        self, *, owner: str, name: str, value: bool
    ) -> None:
        await self._raise_on_missing(owner, name)

        model = await RepositoryModel.select_for_update().get(owner=owner, name=name)

        model.default_automerge = value
        await model.save(update_fields=["default_automerge"])

    @atomic()
    async def set_default_enable_qa(
        self, *, owner: str, name: str, value: bool
    ) -> None:
        await self._raise_on_missing(owner, name)

        model = await RepositoryModel.select_for_update().get(owner=owner, name=name)

        model.default_enable_qa = value
        await model.save(update_fields=["default_enable_qa"])

    @atomic()
    async def set_default_enable_checks(
        self, *, owner: str, name: str, value: bool
    ) -> None:
        await self._raise_on_missing(owner, name)

        model = await RepositoryModel.select_for_update().get(owner=owner, name=name)

        model.default_enable_checks = value
        await model.save(update_fields=["default_enable_checks"])

    @atomic()
    async def set_pr_title_validation_regex(
        self, *, owner: str, name: str, value: re.Pattern[str]
    ) -> None:
        await self._raise_on_missing(owner, name)

        model = await RepositoryModel.select_for_update().get(owner=owner, name=name)

        model.pr_title_validation_regex = value.pattern
        await model.save(update_fields=["pr_title_validation_regex"])

    @atomic()
    async def set_manual_interaction(
        self, *, owner: str, name: str, value: bool
    ) -> None:
        await self._raise_on_missing(owner, name)

        model = await RepositoryModel.select_for_update().get(owner=owner, name=name)

        model.manual_interaction = value
        await model.save(update_fields=["manual_interaction"])

    def _model_to_domain(self, model: RepositoryModel) -> Repository:
        return Repository(
            owner=model.owner,
            name=model.name,
            manual_interaction=model.manual_interaction,
            pr_title_validation_regex=re.compile(model.pr_title_validation_regex),
            default_strategy=MergeStrategy(model.default_strategy),
            default_automerge=model.default_automerge,
            default_enable_qa=model.default_enable_qa,
            default_enable_checks=model.default_enable_checks,
        )

    async def _raise_on_missing(self, owner: str, name: str) -> None:
        if not await RepositoryModel.exists(owner=owner, name=name):
            raise UnknownRepository(owner=owner, name=name)


class PullRequestDatabaseImplementation(PullRequestDatabase):
    async def all(self) -> list[PullRequest]:
        return [
            self._model_to_domain(model)
            for model in await PullRequestModel.all().select_related("repository")
        ]

    async def create(self, pull_request: PullRequest) -> PullRequest:
        logger.info("Creating pull request", pull_request=pull_request)

        repository = await RepositoryModel.get(
            owner=pull_request.repository_path.owner,
            name=pull_request.repository_path.name,
        )
        await PullRequestModel.create(
            repository_id=repository.id,
            number=pull_request.number,
            qa_status=pull_request.qa_status.value,
            status_comment_id=pull_request.status_comment_id,
            checks_enabled=pull_request.checks_enabled,
            automerge=pull_request.automerge,
            locked=pull_request.locked,
            strategy_override=pull_request.strategy_override.value
            if pull_request.strategy_override
            else None,
        )

        return await self.get_or_raise(
            owner=pull_request.repository_path.owner,
            name=pull_request.repository_path.name,
            number=pull_request.number,
        )

    async def update(self, pull_request: PullRequest) -> PullRequest:
        logger.info("Updating pull request", pull_request=pull_request)

        model = await PullRequestModel.select_for_update().get(
            repository__owner=pull_request.repository_path.owner,
            repository__name=pull_request.repository_path.name,
            number=pull_request.number,
        )
        model.qa_status = pull_request.qa_status
        model.status_comment_id = pull_request.status_comment_id
        model.checks_enabled = pull_request.checks_enabled
        model.automerge = pull_request.automerge
        model.locked = pull_request.locked

        strategy_override = (
            pull_request.strategy_override.value
            if pull_request.strategy_override
            else None
        )
        model.strategy_override = strategy_override  # type: ignore
        await model.save()

        return await self.get_or_raise(
            owner=pull_request.repository_path.owner,
            name=pull_request.repository_path.name,
            number=pull_request.number,
        )

    async def get(self, *, owner: str, name: str, number: int) -> PullRequest | None:
        model = await PullRequestModel.get_or_none(
            repository__owner=owner, repository__name=name, number=number
        ).select_related("repository")
        if model is not None:
            return self._model_to_domain(model)

        return None

    @atomic()
    async def set_qa_status(
        self, *, owner: str, name: str, number: int, qa_status: QaStatus
    ) -> None:
        await self._raise_on_missing(owner, name, number)

        model = await PullRequestModel.select_for_update().get(
            repository__owner=owner, repository__name=name, number=number
        )

        model.qa_status = str(qa_status)
        await model.save(update_fields=["qa_status"])

    @atomic()
    async def set_checks_enabled(
        self, *, owner: str, name: str, number: int, value: bool
    ) -> None:
        await self._raise_on_missing(owner, name, number)

        model = await PullRequestModel.select_for_update().get(
            repository__owner=owner, repository__name=name, number=number
        )

        model.checks_enabled = value
        await model.save(update_fields=["checks_enabled"])

    @atomic()
    async def set_automerge(
        self, *, owner: str, name: str, number: int, automerge: bool
    ) -> None:
        await self._raise_on_missing(owner, name, number)

        model = await PullRequestModel.select_for_update().get(
            repository__owner=owner, repository__name=name, number=number
        )

        model.automerge = automerge
        await model.save(update_fields=["automerge"])

    @atomic()
    async def set_locked(
        self, *, owner: str, name: str, number: int, locked: bool
    ) -> None:
        await self._raise_on_missing(owner, name, number)

        model = await PullRequestModel.select_for_update().get(
            repository__owner=owner, repository__name=name, number=number
        )

        model.locked = locked
        await model.save(update_fields=["locked"])

    @atomic()
    async def set_status_comment_id(
        self, *, owner: str, name: str, number: int, status_comment_id: int
    ) -> None:
        await self._raise_on_missing(owner, name, number)

        model = await PullRequestModel.select_for_update().get(
            repository__owner=owner, repository__name=name, number=number
        )

        model.status_comment_id = status_comment_id
        await model.save(update_fields=["status_comment_id"])

    @atomic()
    async def set_merge_strategy(
        self, *, owner: str, name: str, number: int, strategy: MergeStrategy | None
    ) -> None:
        await self._raise_on_missing(owner, name, number)

        model = await PullRequestModel.select_for_update().get(
            repository__owner=owner, repository__name=name, number=number
        )

        model.strategy_override = strategy.value if strategy is not None else None  # type: ignore
        await model.save(update_fields=["strategy_override"])

    async def _raise_on_missing(self, owner: str, name: str, number: int) -> None:
        if not await PullRequestModel.exists(
            repository__owner=owner, repository__name=name, number=number
        ):
            raise UnknownPullRequest(owner=owner, name=name, number=number)

    def _model_to_domain(self, model: PullRequestModel) -> PullRequest:
        return PullRequest(
            repository_path=RepositoryPath(
                owner=model.repository.owner, name=model.repository.name
            ),
            number=model.number,
            qa_status=QaStatus(model.qa_status),
            status_comment_id=model.status_comment_id,
            checks_enabled=model.checks_enabled,
            automerge=model.automerge,
            locked=model.locked,
            strategy_override=MergeStrategy(model.strategy_override)
            if model.strategy_override is not None
            else None,
        )


class MergeRuleDatabaseImplementation(MergeRuleDatabase):
    async def all(self) -> list[MergeRule]:
        return [
            self._model_to_domain(model)
            for model in await MergeRuleModel.all().select_related("repository")
        ]

    async def create(self, merge_rule: MergeRule) -> MergeRule:
        logger.info("Creating merge rule", merge_rule=merge_rule)

        repository = await RepositoryModel.get(
            owner=merge_rule.repository_path.owner, name=merge_rule.repository_path.name
        )
        await MergeRuleModel.create(
            repository_id=repository.id,
            base_branch=merge_rule.base_branch.get_name(),
            head_branch=merge_rule.head_branch.get_name(),
            strategy=merge_rule.strategy.value,
        )

        return await self.get_or_raise(
            owner=repository.owner,
            name=repository.name,
            base_branch=merge_rule.base_branch,
            head_branch=merge_rule.head_branch,
        )

    async def update(self, merge_rule: MergeRule) -> MergeRule:
        logger.info("Updating merge rule", merge_rule=merge_rule)
        await self._raise_on_missing(
            owner=merge_rule.repository_path.owner,
            name=merge_rule.repository_path.name,
            base_branch=merge_rule.base_branch,
            head_branch=merge_rule.head_branch,
        )

        model = await MergeRuleModel.select_for_update().get(
            repository__owner=merge_rule.repository_path.owner,
            repository__name=merge_rule.repository_path.name,
            base_branch=merge_rule.base_branch.get_name(),
            head_branch=merge_rule.head_branch.get_name(),
        )
        model.strategy = merge_rule.strategy.value
        await model.save(update_fields=["strategy"])

        return await self.get_or_raise(
            owner=merge_rule.repository_path.owner,
            name=merge_rule.repository_path.name,
            base_branch=merge_rule.base_branch,
            head_branch=merge_rule.head_branch,
        )

    async def get(
        self, *, owner: str, name: str, base_branch: RuleBranch, head_branch: RuleBranch
    ) -> MergeRule | None:
        model = await MergeRuleModel.get_or_none(
            repository__owner=owner,
            repository__name=name,
            base_branch=base_branch.get_name(),
            head_branch=head_branch.get_name(),
        ).select_related("repository")
        if model is not None:
            return self._model_to_domain(model)

        return None

    async def _raise_on_missing(
        self, *, owner: str, name: str, base_branch: RuleBranch, head_branch: RuleBranch
    ) -> None:
        if not await MergeRuleModel.exists(
            repository__owner=owner,
            repository__name=name,
            base_branch=base_branch.get_name(),
            head_branch=head_branch.get_name(),
        ):
            raise UnknownMergeRule(
                owner=owner, name=name, base_branch=base_branch, head_branch=head_branch
            )

    def _model_to_domain(self, model: MergeRuleModel) -> MergeRule:
        return MergeRule(
            repository_path=RepositoryPath(
                owner=model.repository.owner, name=model.repository.name
            ),
            base_branch=RuleBranchFactory.from_str(model.base_branch),
            head_branch=RuleBranchFactory.from_str(model.head_branch),
            strategy=MergeStrategy(model.strategy),
        )


class RepositoryRuleDatabaseImplementation(RepositoryRuleDatabase):
    async def all(self) -> list[RepositoryRule]:
        return [
            self._model_to_domain(model)
            for model in await RepositoryRuleModel.all().select_related("repository")
        ]

    async def list(self, *, owner: str, name: str) -> list[RepositoryRule]:
        rules = (
            await RepositoryRuleModel.filter(
                repository__owner=owner, repository__name=name
            )
            .select_related("repository")
            .order_by("name")
        )
        return [self._model_to_domain(rule) for rule in rules]

    async def create(self, repository_rule: RepositoryRule) -> RepositoryRule:
        logger.info("Creating repository rule", repository_rule=repository_rule)

        repository = await RepositoryModel.get(
            owner=repository_rule.repository_path.owner,
            name=repository_rule.repository_path.name,
        )
        await RepositoryRuleModel.create(
            repository_id=repository.id,
            name=repository_rule.name,
            conditions=RuleConditionFactory.many_to_str(repository_rule.conditions),
            actions=RuleActionFactory.many_to_str(repository_rule.actions),
        )

        return await self.get_or_raise(
            owner=repository_rule.repository_path.owner,
            name=repository_rule.repository_path.name,
            rule_name=repository_rule.name,
        )

    async def update(self, repository_rule: RepositoryRule) -> RepositoryRule:
        logger.info("Updating repository rule", repository_rule=repository_rule)
        await self._raise_on_missing(
            owner=repository_rule.repository_path.owner,
            name=repository_rule.repository_path.name,
            rule_name=repository_rule.name,
        )

        model = await RepositoryRuleModel.select_for_update().get(
            repository__owner=repository_rule.repository_path.owner,
            repository__name=repository_rule.repository_path.name,
            name=repository_rule.name,
        )
        model.conditions = RuleConditionFactory.many_to_str(repository_rule.conditions)
        model.actions = RuleActionFactory.many_to_str(repository_rule.actions)
        await model.save()

        return await self.get_or_raise(
            owner=repository_rule.repository_path.owner,
            name=repository_rule.repository_path.name,
            rule_name=repository_rule.name,
        )

    async def delete(self, *, owner: str, name: str, rule_name: str) -> bool:
        logger.info(
            "Deleting repository rule", owner=owner, name=name, rule_name=rule_name
        )

        entries = await RepositoryRuleModel.filter(
            repository__owner=owner, repository__name=name, name=rule_name
        ).delete()
        return entries > 0

    async def get(
        self, *, owner: str, name: str, rule_name: str
    ) -> RepositoryRule | None:
        model = await RepositoryRuleModel.get_or_none(
            repository__owner=owner, repository__name=name, name=rule_name
        ).select_related("repository")
        if model is not None:
            return self._model_to_domain(model)

        return None

    async def _raise_on_missing(self, *, owner: str, name: str, rule_name: str) -> None:
        if not await RepositoryRuleModel.exists(
            repository__owner=owner, repository__name=name, name=rule_name
        ):
            raise UnknownRepositoryRule(owner=owner, name=name, rule_name=rule_name)

    def _model_to_domain(self, model: RepositoryRuleModel) -> RepositoryRule:
        return RepositoryRule(
            repository_path=RepositoryPath(
                owner=model.repository.owner, name=model.repository.name
            ),
            name=model.name,
            conditions=RuleConditionFactory.from_str_many(model.conditions),
            actions=RuleActionFactory.from_str_many(model.actions),
        )


class ExternalAccountDatabaseImplementation(ExternalAccountDatabase):
    async def all(self) -> list[ExternalAccount]:
        return [
            self._model_to_domain(model) for model in await ExternalAccountModel.all()
        ]

    async def get(self, *, username: str) -> ExternalAccount | None:
        model = await ExternalAccountModel.get_or_none(username=username)
        if model is not None:
            return self._model_to_domain(model)

        return None

    async def create(self, external_account: ExternalAccount) -> ExternalAccount:
        logger.info("Creating external account", external_account=external_account)

        model = await ExternalAccountModel.create(
            username=external_account.username,
            public_key=external_account.public_key,
            private_key=external_account.private_key,
        )
        return self._model_to_domain(model)

    async def update(self, external_account: ExternalAccount) -> ExternalAccount:
        logger.info("Updating external account", external_account=external_account)
        await self._raise_on_missing(external_account.username)

        model = await ExternalAccountModel.select_for_update().get(
            username=external_account.username,
        )

        model.private_key = external_account.private_key
        model.public_key = external_account.public_key
        await model.save()

        return self._model_to_domain(model)

    async def list(self) -> list[ExternalAccount]:
        return [
            self._model_to_domain(account)
            for account in await ExternalAccountModel.all().order_by("username")
        ]

    async def _raise_on_missing(self, username: str) -> None:
        if not await ExternalAccountModel.exists(username=username):
            raise UnknownExternalAccount(username=username)

    def _model_to_domain(self, model: ExternalAccountModel) -> ExternalAccount:
        return ExternalAccount(
            private_key=model.private_key,
            public_key=model.public_key,
            username=model.username,
        )


class ExternalAccountRightDatabaseImplementation(ExternalAccountRightDatabase):
    async def all(self) -> list[ExternalAccountRight]:
        return [
            self._model_to_domain(model)
            for model in await ExternalAccountRightModel.all().select_related(
                "repository", "account"
            )
        ]

    async def list(self, *, username: str) -> list[ExternalAccountRight]:
        return [
            self._model_to_domain(model)
            for model in await ExternalAccountRightModel.filter(
                username=username
            ).select_related("repository", "account")
        ]

    async def create(self, right: ExternalAccountRight) -> ExternalAccountRight:
        logger.info("Creating external account right", right=right)

        repository = await RepositoryModel.get(
            owner=right.repository_path.owner,
            name=right.repository_path.name,
        )
        account = await ExternalAccountModel.get(username=right.username)
        await ExternalAccountRightModel.create(
            repository_id=repository.id, account=account
        )

        return await self.get_or_raise(
            owner=right.repository_path.owner,
            name=right.repository_path.name,
            username=right.username,
        )

    async def get(
        self, *, owner: str, name: str, username: str
    ) -> ExternalAccountRight | None:
        model = await ExternalAccountRightModel.get_or_none(
            repository__owner=owner, repository__name=name, account__username=username
        ).select_related("repository", "account")
        if model is not None:
            return self._model_to_domain(model)

        return None

    def _model_to_domain(
        self, model: ExternalAccountRightModel
    ) -> ExternalAccountRight:
        return ExternalAccountRight(
            repository_path=RepositoryPath(
                owner=model.repository.owner, name=model.repository.name
            ),
            username=model.account.username,
        )
