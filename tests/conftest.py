from typing import AsyncGenerator, Callable, Generator

import inject
import pytest
from tortoise import Tortoise
from tortoise.contrib.test import _init_db, getDBConfig

from prbot.config.settings import Settings, set_global_settings
from prbot.core.sync.processor import SyncProcessor, SyncProcessorImplementation
from prbot.core.sync.sync_state import (
    PullRequestSyncStateBuilder,
    PullRequestSyncStateBuilderImplementation,
)
from prbot.injection import inject_instance
from prbot.modules.database.implementations import (
    ExternalAccountDatabaseImplementation,
    ExternalAccountRightDatabaseImplementation,
    MergeRuleDatabaseImplementation,
    PullRequestDatabaseImplementation,
    RepositoryDatabaseImplementation,
    RepositoryRuleDatabaseImplementation,
)
from prbot.modules.database.repository import (
    ExternalAccountDatabase,
    ExternalAccountRightDatabase,
    MergeRuleDatabase,
    PullRequestDatabase,
    RepositoryDatabase,
    RepositoryRuleDatabase,
)
from prbot.modules.gif.client import GifClient, GifClientImplementation
from prbot.modules.github.client import GitHubClient, GitHubClientImplementation
from prbot.modules.lock import LockClient
from tests.utils.http import FakeHttpClient
from tests.utils.lock import FakeLockClient

InjectorCallable = Callable[[inject.Binder], None]
InjectorFixture = Callable[[InjectorCallable], None]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="function", autouse=True)
def bot_settings() -> Generator[Settings, None, None]:
    default_settings = Settings(
        github_webhook_secret="foobar",
        bot_nickname="bot",
        github_personal_token="foo",
        database_url="sqlite://:memory:",
        lock_url="foo",
        tenor_key="nope",
    )

    set_global_settings(default_settings)
    yield default_settings


@pytest.fixture(scope="function", autouse=True)
async def database() -> AsyncGenerator[None, None]:
    config = getDBConfig(app_label="prbot", modules=["prbot.modules.database.models"])
    await _init_db(config)
    yield
    await Tortoise._drop_databases()


@pytest.fixture(scope="function", autouse=True)
async def injector() -> AsyncGenerator[InjectorFixture, None]:
    def default_bind(binder: inject.Binder) -> None:
        binder.bind(LockClient, FakeLockClient())

        # Database
        binder.bind(RepositoryDatabase, RepositoryDatabaseImplementation())
        binder.bind(PullRequestDatabase, PullRequestDatabaseImplementation())
        binder.bind(MergeRuleDatabase, MergeRuleDatabaseImplementation())
        binder.bind(RepositoryRuleDatabase, RepositoryRuleDatabaseImplementation())
        binder.bind(ExternalAccountDatabase, ExternalAccountDatabaseImplementation())
        binder.bind(
            ExternalAccountRightDatabase, ExternalAccountRightDatabaseImplementation()
        )

        # Modules
        binder.bind_to_constructor(
            GifClient, lambda: GifClientImplementation(FakeHttpClient())
        )
        binder.bind_to_constructor(
            GitHubClient, lambda: GitHubClientImplementation(FakeHttpClient())
        )

        # Processors
        binder.bind_to_constructor(
            SyncProcessor,
            lambda: SyncProcessorImplementation(),
        )
        binder.bind_to_constructor(
            PullRequestSyncStateBuilder,
            lambda: PullRequestSyncStateBuilderImplementation(),
        )

    inject.configure(default_bind, clear=True, allow_override=True)

    def inner(bind: InjectorCallable) -> None:
        def local_bind(binder: inject.Binder) -> None:
            binder.install(default_bind)
            bind(binder)

        inject.configure(local_bind, clear=True, allow_override=True)

    yield inner

    github_client = inject_instance(GitHubClient)
    await github_client.aclose()

    gif_client = inject_instance(GifClient)
    await gif_client.aclose()

    lock_client = inject_instance(LockClient)
    await lock_client.aclose()


def get_fake_github_http_client() -> FakeHttpClient:
    client = inject_instance(GitHubClient)
    assert isinstance(client, GitHubClientImplementation)

    core_client = client.core().client
    assert isinstance(core_client, FakeHttpClient)

    return core_client


def get_fake_gif_http_client() -> FakeHttpClient:
    client = inject_instance(GifClient)
    assert isinstance(client, GifClientImplementation)

    core_client = client._client
    assert isinstance(core_client, FakeHttpClient)

    return core_client


def get_fake_lock_client() -> FakeLockClient:
    client = inject_instance(LockClient)
    assert isinstance(client, FakeLockClient)

    return client
