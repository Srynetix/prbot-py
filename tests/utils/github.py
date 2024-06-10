import datetime
from typing import Any

from prbot.modules.github.models import (
    GhApplication,
    GhBranch,
    GhBranchShort,
    GhCheckConclusion,
    GhCheckRun,
    GhCheckStatus,
    GhPullRequest,
    GhPullRequestShort,
    GhPullRequestState,
    GhUser,
)


def dummy_gh_pull_request(**kwargs: Any) -> GhPullRequest:
    pr = GhPullRequest(
        number=1,
        title="Foobar",
        user=GhUser(login="foo"),
        state=GhPullRequestState.Open,
        base=GhBranch(
            ref="base",
            sha="654321",
        ),
        body=None,
        locked=False,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
        requested_reviewers=[],
        labels=[],
        draft=False,
        head=GhBranch(ref="foo", sha="123456"),
    )

    for k, v in kwargs.items():
        setattr(pr, k, v)

    return pr


def dummy_gh_check_run(**kwargs: Any) -> GhCheckRun:
    run = GhCheckRun(
        app=GhApplication(slug="foo", owner=GhUser(login="foo"), name="foo"),
        head_sha="123456",
        status=GhCheckStatus.Completed,
        id=1,
        started_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00Z"),
        completed_at=datetime.datetime.fromisoformat("2020-01-01T00:00:00Z"),
        conclusion=GhCheckConclusion.Success,
        name="Foo",
        pull_requests=[
            GhPullRequestShort(
                number=1,
                head=GhBranchShort(ref="foo", sha="123456"),
                base=GhBranchShort(ref="bar", sha="654321"),
            )
        ],
    )

    for k, v in kwargs.items():
        setattr(run, k, v)

    return run
