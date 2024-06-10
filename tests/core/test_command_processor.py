import pytest

from prbot.core.commands.commands import (
    AssignReviewers,
    CommandContext,
    SetAutomerge,
    SetChecksEnabled,
    SetLocked,
    SetQa,
    UnassignReviewers,
)
from prbot.core.message import generate_message_footer
from prbot.core.models import PullRequest, QaStatus, Repository
from prbot.injection import inject_instance
from prbot.modules.database.repository import PullRequestDatabase, RepositoryDatabase
from prbot.modules.github.models import (
    GhReactionType,
    GhReviewersAddRequest,
    GhReviewersRemoveRequest,
)
from tests.conftest import get_fake_github_http_client
from tests.utils.http import FakeHttpClient, HttpExpectation

pytestmark = pytest.mark.anyio


@pytest.fixture
async def command_ctx() -> CommandContext:
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)

    repository = await repository_db.create(Repository(owner="owner", name="name"))
    pull_request = await pull_request_db.create(
        PullRequest(repository_path=repository.path(), number=1)
    )

    return CommandContext(
        owner=repository.owner,
        name=repository.name,
        number=pull_request.number,
        author="foo",
        comment_id=1,
        command="command",
    )


class Arrange:
    fake_client_api: FakeHttpClient

    def __init__(self) -> None:
        self.fake_client_api = get_fake_github_http_client()

    def with_reaction(self, reaction: GhReactionType) -> None:
        self.fake_client_api.expect(
            HttpExpectation()
            .with_input(
                method="POST", url="/repos/owner/name/issues/comments/1/reactions"
            )
            .with_input_json({"content": reaction.value})
            .with_output_status(200)
        )

    def with_comment(self, message: str) -> None:
        self.fake_client_api.expect(
            HttpExpectation()
            .with_input(method="POST", url="/repos/owner/name/issues/1/comments")
            .with_input_json(
                {"body": f"> command\n\n{message}\n{generate_message_footer()}"}
            )
            .with_output_status(200)
            .with_output_json({"id": 1})
        )

    async def with_pull_request(self) -> PullRequest:
        pr_db = inject_instance(PullRequestDatabase)
        return await pr_db.get_or_raise(owner="owner", name="name", number=1)


@pytest.fixture()
async def arrange() -> Arrange:
    return Arrange()


async def test_set_qa_pass(arrange: Arrange, command_ctx: CommandContext) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("QA status is marked as **pass** by **foo**.")

    output = await SetQa(QaStatus.Pass).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.qa_status == QaStatus.Pass


async def test_set_qa_fail(arrange: Arrange, command_ctx: CommandContext) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("QA status is marked as **fail** by **foo**.")

    output = await SetQa(QaStatus.Fail).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.qa_status == QaStatus.Fail


async def test_set_qa_waiting(arrange: Arrange, command_ctx: CommandContext) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("QA status is marked as **waiting** by **foo**.")

    output = await SetQa(QaStatus.Waiting).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.qa_status == QaStatus.Waiting


async def test_set_qa_skipped(arrange: Arrange, command_ctx: CommandContext) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("QA status is marked as **skipped** by **foo**.")

    output = await SetQa(QaStatus.Skipped).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.qa_status == QaStatus.Skipped


async def test_set_checks_enabled(
    arrange: Arrange, command_ctx: CommandContext
) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("Checks were enabled by **foo**.")

    output = await SetChecksEnabled(True).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.checks_enabled is True


async def test_set_checks_disabled(
    arrange: Arrange, command_ctx: CommandContext
) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("Checks were disabled by **foo**.")

    output = await SetChecksEnabled(False).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.checks_enabled is False


async def test_set_automerge_enabled(
    arrange: Arrange, command_ctx: CommandContext
) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("Pull request automerge is enabled.")

    output = await SetAutomerge(True).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.automerge is True


async def test_set_automerge_disabled(
    arrange: Arrange, command_ctx: CommandContext
) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("Pull request automerge is disabled.")

    output = await SetAutomerge(False).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.automerge is False


async def test_set_locked(arrange: Arrange, command_ctx: CommandContext) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("Pull request is now locked.")

    output = await SetLocked(True, comment=None).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.locked is True


async def test_set_locked_with_comment(
    arrange: Arrange, command_ctx: CommandContext
) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("Pull request is now locked: foobar.")

    output = await SetLocked(True, comment="foobar").process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.locked is True


async def test_set_unlocked(arrange: Arrange, command_ctx: CommandContext) -> None:
    arrange.with_reaction(GhReactionType.Eyes)
    arrange.with_comment("Pull request is now unlocked.")

    output = await SetLocked(False, comment=None).process(command_ctx)
    assert output.needs_sync is True

    pr = await arrange.with_pull_request()
    assert pr.locked is False


async def test_assign_reviewers(arrange: Arrange, command_ctx: CommandContext) -> None:
    arrange.with_reaction(GhReactionType.Eyes)

    arrange.fake_client_api.expect(
        HttpExpectation()
        .with_input(
            method="POST",
            url="/repos/owner/name/pulls/1/requested_reviewers",
            json=GhReviewersAddRequest(reviewers=["foo"]).model_dump(),
        )
        .with_output_status(200)
    )

    output = await AssignReviewers(["foo"]).process(command_ctx)
    assert output.needs_sync is True


async def test_unassign_reviewers(
    arrange: Arrange, command_ctx: CommandContext
) -> None:
    arrange.with_reaction(GhReactionType.Eyes)

    arrange.fake_client_api.expect(
        HttpExpectation()
        .with_input(
            method="DELETE",
            url="/repos/owner/name/pulls/1/requested_reviewers",
            json=GhReviewersRemoveRequest(reviewers=["foo"]).model_dump(),
        )
        .with_output_status(200)
    )

    output = await UnassignReviewers(["foo"]).process(command_ctx)
    assert output.needs_sync is True
