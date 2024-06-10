import inject
import structlog

from prbot.core.sync.processor import SyncProcessor, SyncProcessorImplementation
from prbot.core.sync.sync_state import (
    PullRequestSyncStateBuilder,
    PullRequestSyncStateBuilderImplementation,
)
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
from prbot.modules.http.client import HttpClientImplementation
from prbot.modules.lock import LockClient, LockClientImplementation

logger = structlog.get_logger(__name__)


def _setup_binder(binder: inject.Binder) -> None:
    binder.bind(LockClient, LockClientImplementation())

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
        GitHubClient, lambda: GitHubClientImplementation(HttpClientImplementation())
    )
    binder.bind_to_constructor(
        GifClient, lambda: GifClientImplementation(HttpClientImplementation())
    )

    # Processors and builders
    binder.bind_to_constructor(
        SyncProcessor,
        lambda: SyncProcessorImplementation(),
    )
    binder.bind_to_constructor(
        PullRequestSyncStateBuilder,
        lambda: PullRequestSyncStateBuilderImplementation(),
    )


def setup_injections() -> None:
    inject.configure(_setup_binder)
