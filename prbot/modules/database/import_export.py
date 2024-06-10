import copy
import json
import re
from typing import IO, Any

from pydantic import BaseModel

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
    RuleBranchFactory,
    RuleConditionFactory,
)
from prbot.injection import inject_instance
from prbot.modules.database.repository import (
    ExternalAccountDatabase,
    ExternalAccountRightDatabase,
    MergeRuleDatabase,
    PullRequestDatabase,
    RepositoryDatabase,
    RepositoryRuleDatabase,
)


class ImportExportData(BaseModel):
    repositories: list[Repository]
    pull_requests: list[PullRequest]
    repository_rules: list[RepositoryRule]
    merge_rules: list[MergeRule]
    external_accounts: list[ExternalAccount]
    external_account_rights: list[ExternalAccountRight]


class ImportExportProcessor:
    _repository_db: RepositoryDatabase
    _pull_request_db: PullRequestDatabase
    _repository_rule_db: RepositoryRuleDatabase
    _merge_rule_db: MergeRuleDatabase
    _external_account_db: ExternalAccountDatabase
    _external_account_right_db: ExternalAccountRightDatabase

    def __init__(self) -> None:
        self._repository_db = inject_instance(RepositoryDatabase)
        self._pull_request_db = inject_instance(PullRequestDatabase)
        self._repository_rule_db = inject_instance(RepositoryRuleDatabase)
        self._merge_rule_db = inject_instance(MergeRuleDatabase)
        self._external_account_db = inject_instance(ExternalAccountDatabase)
        self._external_account_right_db = inject_instance(ExternalAccountRightDatabase)

    async def import_data(self, stream: IO[bytes]) -> None:
        data = self._generate_data_from_stream(stream)
        await self._import_data_to_database(data)

    async def import_data_compatibility(self, stream: IO[bytes]) -> None:
        data = self._convert_compatibility_data_to_data(json.load(stream))
        await self._import_data_to_database(data)

    async def export_data(self, stream: IO[bytes]) -> None:
        data = await self._generate_data_from_database()
        stream.write(data.model_dump_json(indent=4).encode())

    async def _import_data_to_database(self, data: ImportExportData) -> None:
        for repository in data.repositories:
            await self._repository_db.create_or_update(repository)

        for pull_request in data.pull_requests:
            await self._pull_request_db.create_or_update(pull_request)

        for repository_rule in data.repository_rules:
            await self._repository_rule_db.create_or_update(repository_rule)

        for merge_rule in data.merge_rules:
            await self._merge_rule_db.create_or_update(merge_rule)

        for external_account in data.external_accounts:
            await self._external_account_db.create_or_update(external_account)

        for external_account_right in data.external_account_rights:
            await self._external_account_right_db.get_or_create(external_account_right)

    def _generate_data_from_stream(self, stream: IO[bytes]) -> ImportExportData:
        return ImportExportData.model_validate_json(stream.read())

    def _convert_compatibility_data_to_data(
        self, previous: dict[str, Any]
    ) -> ImportExportData:
        data = ImportExportData(
            repositories=[],
            pull_requests=[],
            repository_rules=[],
            merge_rules=[],
            external_accounts=[],
            external_account_rights=[],
        )
        repository_ids: dict[int, RepositoryPath] = {}

        # Read repositories
        for repository_data in previous["repositories"]:
            repository = Repository(
                owner=repository_data["owner"],
                name=repository_data["name"],
                manual_interaction=repository_data["manual_interaction"],
                pr_title_validation_regex=re.compile(
                    repository_data["pr_title_validation_regex"]
                ),
                default_strategy=MergeStrategy(repository_data["default_strategy"]),
                default_automerge=repository_data["default_automerge"],
                default_enable_qa=repository_data["default_enable_qa"],
                default_enable_checks=repository_data["default_enable_checks"],
            )

            repository_ids[repository_data["id"]] = repository.path()
            data.repositories.append(repository)

        # Read pull requests
        for pull_request_data in previous["pull_requests"]:
            status_comment_id = pull_request_data["status_comment_id"]
            if status_comment_id > 2**63:
                status_comment_id = 0

            pull_request = PullRequest(
                repository_path=copy.deepcopy(
                    repository_ids[pull_request_data["repository_id"]]
                ),
                number=pull_request_data["number"],
                qa_status=QaStatus(pull_request_data["qa_status"]),
                status_comment_id=status_comment_id,
                checks_enabled=pull_request_data["checks_enabled"],
                automerge=pull_request_data["automerge"],
                locked=pull_request_data["locked"],
                strategy_override=MergeStrategy(pull_request_data["strategy_override"])
                if pull_request_data["strategy_override"]
                else None,
            )
            data.pull_requests.append(pull_request)

        # Read merge rules
        for merge_rule_data in previous["merge_rules"]:
            merge_rule = MergeRule(
                repository_path=copy.deepcopy(
                    repository_ids[merge_rule_data["repository_id"]]
                ),
                base_branch=RuleBranchFactory.from_str(merge_rule_data["base_branch"]),
                head_branch=RuleBranchFactory.from_str(merge_rule_data["head_branch"]),
                strategy=MergeStrategy(merge_rule_data["strategy"]),
            )
            data.merge_rules.append(merge_rule)

        # External accounts
        for external_account_data in previous["external_accounts"]:
            external_account = ExternalAccount(
                username=external_account_data["username"],
                public_key=external_account_data["public_key"],
                private_key=external_account_data["private_key"],
            )
            data.external_accounts.append(external_account)

        # External account rights
        for external_account_right_data in previous["external_account_rights"]:
            right = ExternalAccountRight(
                repository_path=copy.deepcopy(
                    repository_ids[external_account_right_data["repository_id"]]
                ),
                username=external_account_right_data["username"],
            )
            data.external_account_rights.append(right)

        # Repository rules
        for pull_request_rule_data in previous["pull_request_rules"]:
            repository_rule = RepositoryRule(
                repository_path=copy.deepcopy(
                    repository_ids[pull_request_rule_data["repository_id"]]
                ),
                name=pull_request_rule_data["name"],
                conditions=[
                    RuleConditionFactory.from_dict(condition)
                    for condition in pull_request_rule_data["conditions"]
                ],
                actions=[
                    RuleActionFactory.from_dict(action)
                    for action in pull_request_rule_data["actions"]
                ],
            )
            data.repository_rules.append(repository_rule)

        return data

    async def _generate_data_from_database(self) -> ImportExportData:
        return ImportExportData(
            repositories=await self._repository_db.all(),
            pull_requests=await self._pull_request_db.all(),
            repository_rules=await self._repository_rule_db.all(),
            merge_rules=await self._merge_rule_db.all(),
            external_accounts=await self._external_account_db.all(),
            external_account_rights=await self._external_account_right_db.all(),
        )
