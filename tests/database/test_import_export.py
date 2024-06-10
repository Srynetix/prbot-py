from io import BytesIO

import pytest

from prbot.core.models import (
    ExternalAccount,
    ExternalAccountRight,
    MergeRule,
    MergeStrategy,
    NamedRuleBranch,
    PullRequest,
    QaStatus,
    Repository,
    RepositoryRule,
    RuleActionSetQaStatus,
    RuleConditionAuthor,
    WildcardRuleBranch,
)
from prbot.injection import inject_instance
from prbot.modules.database.import_export import ImportExportData, ImportExportProcessor
from prbot.modules.database.repository import (
    ExternalAccountDatabase,
    ExternalAccountRightDatabase,
    MergeRuleDatabase,
    PullRequestDatabase,
    RepositoryDatabase,
    RepositoryRuleDatabase,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
async def initial_data() -> ImportExportData:
    repository = Repository(owner="owner", name="name")

    pull_request = PullRequest(repository_path=repository.path(), number=1)

    merge_rule = MergeRule(
        repository_path=repository.path(),
        base_branch=WildcardRuleBranch(),
        head_branch=NamedRuleBranch(value="foo"),
        strategy=MergeStrategy.Rebase,
    )

    repository_rule = RepositoryRule(
        repository_path=repository.path(),
        name="Foo",
        conditions=[RuleConditionAuthor(value="foo")],
        actions=[RuleActionSetQaStatus(value=QaStatus.Pass)],
    )

    external_account = ExternalAccount(
        username="foo", public_key="foo", private_key="foo"
    )

    external_account_right = ExternalAccountRight(
        repository_path=repository.path(), username="foo"
    )

    return ImportExportData(
        repositories=[repository],
        pull_requests=[pull_request],
        repository_rules=[repository_rule],
        merge_rules=[merge_rule],
        external_accounts=[external_account],
        external_account_rights=[external_account_right],
    )


@pytest.fixture
async def with_initialized_db(initial_data: ImportExportData) -> None:
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)
    merge_rule_db = inject_instance(MergeRuleDatabase)
    repository_rule_db = inject_instance(RepositoryRuleDatabase)
    external_account_db = inject_instance(ExternalAccountDatabase)
    external_account_right_db = inject_instance(ExternalAccountRightDatabase)

    await repository_db.create(initial_data.repositories[0])
    await pull_request_db.create(initial_data.pull_requests[0])
    await merge_rule_db.create(initial_data.merge_rules[0])
    await repository_rule_db.create(initial_data.repository_rules[0])
    await external_account_db.create(initial_data.external_accounts[0])
    await external_account_right_db.create(initial_data.external_account_rights[0])


async def test_export_data_empty() -> None:
    stream = BytesIO()
    processor = ImportExportProcessor()
    await processor.export_data(stream)

    empty_data = ImportExportData(
        repositories=[],
        pull_requests=[],
        merge_rules=[],
        repository_rules=[],
        external_accounts=[],
        external_account_rights=[],
    )
    assert ImportExportData.model_validate_json(stream.getvalue()) == empty_data


async def test_export_data_values(
    initial_data: ImportExportData, with_initialized_db: None
) -> None:
    stream = BytesIO()
    processor = ImportExportProcessor()
    await processor.export_data(stream)

    assert ImportExportData.model_validate_json(stream.getvalue()) == initial_data


async def test_import_data_new(initial_data: ImportExportData) -> None:
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)
    merge_rule_db = inject_instance(MergeRuleDatabase)
    repository_rule_db = inject_instance(RepositoryRuleDatabase)
    external_account_db = inject_instance(ExternalAccountDatabase)
    external_account_right_db = inject_instance(ExternalAccountRightDatabase)

    stream = BytesIO()
    stream.write(initial_data.model_dump_json().encode())
    stream.seek(0)

    processor = ImportExportProcessor()
    await processor.import_data(stream)

    assert [await repository_db.all()] == [initial_data.repositories]
    assert [await pull_request_db.all()] == [initial_data.pull_requests]
    assert [await merge_rule_db.all()] == [initial_data.merge_rules]
    assert [await repository_rule_db.all()] == [initial_data.repository_rules]
    assert [await external_account_db.all()] == [initial_data.external_accounts]
    assert [await external_account_right_db.all()] == [
        initial_data.external_account_rights
    ]


async def test_import_data_existing(
    initial_data: ImportExportData, with_initialized_db: None
) -> None:
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)
    merge_rule_db = inject_instance(MergeRuleDatabase)
    repository_rule_db = inject_instance(RepositoryRuleDatabase)
    external_account_db = inject_instance(ExternalAccountDatabase)
    external_account_right_db = inject_instance(ExternalAccountRightDatabase)

    stream = BytesIO()
    stream.write(initial_data.model_dump_json().encode())
    stream.seek(0)

    processor = ImportExportProcessor()
    await processor.import_data(stream)

    assert [await repository_db.all()] == [initial_data.repositories]
    assert [await pull_request_db.all()] == [initial_data.pull_requests]
    assert [await merge_rule_db.all()] == [initial_data.merge_rules]
    assert [await repository_rule_db.all()] == [initial_data.repository_rules]
    assert [await external_account_db.all()] == [initial_data.external_accounts]
    assert [await external_account_right_db.all()] == [
        initial_data.external_account_rights
    ]
