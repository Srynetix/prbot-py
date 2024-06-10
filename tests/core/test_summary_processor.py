import asyncio

import pytest

from prbot.core.models import PullRequest, Repository
from prbot.core.summary.processor import SummaryProcessor
from prbot.injection import inject_instance
from prbot.modules.database.repository import PullRequestDatabase, RepositoryDatabase
from prbot.modules.github.models import GhCommentResponse
from tests.conftest import (
    get_fake_github_http_client,
    get_fake_lock_client,
)
from tests.utils.http import HttpExpectation
from tests.utils.lock import LockExpectation
from tests.utils.sync_state import dummy_sync_state

pytestmark = pytest.mark.anyio


async def test_summary_creation_ok() -> None:
    fake_github = get_fake_github_http_client()
    fake_lock = get_fake_lock_client()

    # Setup database
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)
    repository = await repository_db.create(Repository(owner="owner", name="name"))
    await pull_request_db.create(
        PullRequest(number=1, repository_path=repository.path())
    )

    fake_github.expect(
        HttpExpectation()
        .with_input(
            method="POST",
            url="/repos/owner/name/issues/1/comments",
            json=HttpExpectation.IGNORE,
        )
        .with_output_status(200)
        .with_output_model(GhCommentResponse(id=1))
    )

    fake_lock.expect(
        LockExpectation().with_input_action("lock").with_output_function(lambda k: None)
    )

    processor = SummaryProcessor()
    await processor.process(sync_state=dummy_sync_state(status_comment_id=0))


async def test_summary_creation_ko() -> None:
    fake_lock = get_fake_lock_client()

    def failed_lock(k: str) -> None:
        raise RuntimeError("oh noes")

    fake_lock.expect(
        LockExpectation().with_input_action("lock").with_output_function(failed_lock)
    )

    processor = SummaryProcessor()
    await processor.process(sync_state=dummy_sync_state(status_comment_id=0))


async def test_summary_update() -> None:
    fake_github = get_fake_github_http_client()

    fake_github.expect(
        HttpExpectation()
        .with_input(
            method="PATCH",
            url="/repos/owner/name/issues/comments/1",
            json=HttpExpectation.IGNORE,
        )
        .with_output_status(200)
        .with_output_model(GhCommentResponse(id=1))
    )

    processor = SummaryProcessor()
    await processor.process(sync_state=dummy_sync_state())


async def test_summary_generation_parallel() -> None:
    fake_github = get_fake_github_http_client()
    fake_lock = get_fake_lock_client()

    # Setup database
    repository_db = inject_instance(RepositoryDatabase)
    pull_request_db = inject_instance(PullRequestDatabase)
    repository = await repository_db.create(Repository(owner="owner", name="name"))
    await pull_request_db.create(
        PullRequest(number=1, repository_path=repository.path())
    )

    fake_github.expect(
        HttpExpectation()
        .with_times(1)
        .with_input(
            method="POST",
            url="/repos/owner/name/issues/1/comments",
            json=HttpExpectation.IGNORE,
        )
        .with_output_status(200)
        .with_output_model(GhCommentResponse(id=1))
    )

    fake_lock.expect(
        LockExpectation()
        .with_times(10)
        .with_input_action("lock")
        .with_output_function_as_once_lock()
    )

    async def inner() -> None:
        processor = SummaryProcessor()
        await processor.process(sync_state=dummy_sync_state(status_comment_id=0))

    # Run everything in parallel, fingers crossed.
    await asyncio.gather(*[inner() for _ in range(10)])

    # If everything is alright, no exceptions, because API will only be called once.
