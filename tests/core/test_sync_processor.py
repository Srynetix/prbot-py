from typing import override
from unittest import mock

import inject
import pytest

from prbot.core.models import Repository
from prbot.core.sync.processor import (
    SyncProcessorImplementation,
    SyncProcessorResultSuccess,
)
from prbot.core.sync.sync_state import PullRequestSyncStateBuilder
from prbot.injection import inject_instance
from prbot.modules.database.repository import PullRequestDatabase, RepositoryDatabase
from prbot.modules.github.client import GitHubClient
from prbot.modules.github.core import GitHubCore
from prbot.modules.github.models import GhCommitStatusState, GhRepository, GhUser
from prbot.modules.github.modules.check_run import GitHubCheckRunModule
from prbot.modules.github.modules.commit_status import GitHubStatusModule
from prbot.modules.github.modules.issue import GitHubIssueModule
from prbot.modules.github.modules.pull_request import GitHubPullRequestModule
from prbot.modules.github.modules.reaction import GitHubReactionModule
from prbot.modules.github.modules.repository import GitHubRepositoryModule
from tests.conftest import InjectorFixture
from tests.utils.http import FakeHttpClient
from tests.utils.sync_state import (
    create_local_builder,
    dummy_sync_state,
)

pytestmark = pytest.mark.anyio


class MockGitHubClient(GitHubClient):
    _core: GitHubCore

    repositories_mock: mock.AsyncMock
    pull_requests_mock: mock.AsyncMock
    issues_mock: mock.AsyncMock
    check_runs_mock: mock.AsyncMock
    commit_statuses_mock: mock.AsyncMock
    reactions_mock: mock.AsyncMock

    def __init__(self) -> None:
        self.repositories_mock = mock.AsyncMock(GitHubRepositoryModule)
        self.pull_requests_mock = mock.AsyncMock(GitHubPullRequestModule)
        self.issues_mock = mock.AsyncMock(GitHubIssueModule)
        self.check_runs_mock = mock.AsyncMock(GitHubCheckRunModule)
        self.commit_statuses_mock = mock.AsyncMock(GitHubStatusModule)
        self.reactions_mock = mock.AsyncMock(GitHubReactionModule)

        self._core = GitHubCore(FakeHttpClient())
        self._core.set_user_authentication(personal_token="foo")

    @override
    def core(self) -> GitHubCore:
        return self._core

    @override
    def repositories(self) -> GitHubRepositoryModule:
        return self.repositories_mock

    @override
    def pull_requests(self) -> GitHubPullRequestModule:
        return self.pull_requests_mock

    @override
    def issues(self) -> GitHubIssueModule:
        return self.issues_mock

    @override
    def check_runs(self) -> GitHubCheckRunModule:
        return self.check_runs_mock

    @override
    def commit_statuses(self) -> GitHubStatusModule:
        return self.commit_statuses_mock

    @override
    def reactions(self) -> GitHubReactionModule:
        return self.reactions_mock


async def test_sync_processor(injector: InjectorFixture) -> None:
    gh_client = MockGitHubClient()
    gh_client.repositories_mock.get.return_value = GhRepository(
        owner=GhUser(login="foo"), name="bar", full_name="foo/bar"
    )

    def bind(binder: inject.Binder) -> None:
        binder.bind(GitHubClient, gh_client)
        binder.bind_to_constructor(
            PullRequestSyncStateBuilder,
            lambda: create_local_builder(dummy_sync_state()),
        )

    injector(bind)

    sync_processor = SyncProcessorImplementation()
    result = await sync_processor.process(
        owner="owner", name="name", number=1, force_creation=True
    )
    assert isinstance(result, SyncProcessorResultSuccess)

    gh_client.repositories_mock.get.assert_called_with(owner="owner", name="name")
    gh_client.commit_statuses_mock.update.assert_called_with(
        owner="owner",
        name="name",
        commit_ref="123456",
        state=GhCommitStatusState.Success,
        title="Validation",
        body="All good",
    )
    gh_client.issues_mock.labels.assert_called_with(
        owner="owner", name="name", number=1
    )
    gh_client.issues_mock.replace_labels.assert_called_with(
        owner="owner", name="name", number=1, labels=["step/awaiting-merge"]
    )
    gh_client.issues_mock.update_comment.assert_called_with(
        owner="owner", name="name", comment_id=1, message=result.summary
    )


async def test_manual_interaction() -> None:
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)

    await repository_db.create(
        Repository(owner="owner", name="name", manual_interaction=True)
    )

    sync_processor = SyncProcessorImplementation()
    await sync_processor.process(
        owner="owner", name="name", number=1, force_creation=False
    )

    # Pull request will not be synchronized
    assert (await pull_request_db.get(owner="owner", name="name", number=1)) is None
