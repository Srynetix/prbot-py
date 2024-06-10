import copy
import datetime
from typing import Self

from prbot.modules.github.models import (
    GhApplication,
    GhBranch,
    GhBranchShort,
    GhCheckConclusion,
    GhCheckStatus,
    GhCheckSuite,
    GhCheckSuiteAction,
    GhIssue,
    GhIssueComment,
    GhIssueCommentAction,
    GhIssueState,
    GhPullRequest,
    GhPullRequestAction,
    GhPullRequestShort,
    GhPullRequestState,
    GhRepository,
    GhReview,
    GhReviewAction,
    GhReviewState,
    GhUser,
)
from prbot.modules.github.webhooks.models import (
    GhCheckSuiteEvent,
    GhIssueCommentEvent,
    GhPingEvent,
    GhPullRequestEvent,
    GhReviewEvent,
)


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class GhPingEventBuilder:
    _event: GhPingEvent

    def __init__(self) -> None:
        self._event = GhPingEvent(
            zen="Foo bar baz zen message.",
            hook_id=1234,
            repository=GhRepository(
                name="bar", owner=GhUser(login="foo"), full_name="foo/bar"
            ),
            sender=GhUser(login="sender"),
        )

    def with_zen(self, zen: str) -> Self:
        self._event.zen = zen
        return self

    def with_hook_id(self, hook_id: int) -> Self:
        self._event.hook_id = hook_id
        return self

    def with_repository(self, repository: GhRepository) -> Self:
        self._event.repository = copy.deepcopy(repository)
        return self

    def with_sender(self, sender: GhUser) -> Self:
        self._event.sender = copy.deepcopy(sender)
        return self

    def build(self) -> GhPingEvent:
        return copy.deepcopy(self._event)


class GhPullRequestEventBuilder:
    _event: GhPullRequestEvent

    def __init__(self) -> None:
        self._event = GhPullRequestEvent(
            action=GhPullRequestAction.Assigned,
            number=1,
            pull_request=GhPullRequest(
                number=1,
                state=GhPullRequestState.Open,
                locked=False,
                title="Foo",
                base=GhBranch(ref="foo", sha="abc"),
                head=GhBranch(ref="bar", sha="def"),
                body=None,
                created_at=now(),
                updated_at=now(),
                user=GhUser(login="foo"),
                draft=False,
                requested_reviewers=[],
                labels=[],
            ),
            label=None,
            requested_reviewer=None,
            repository=GhRepository(
                name="bar", full_name="foo/bar", owner=GhUser(login="foo")
            ),
            organization=None,
            sender=GhUser(login="foo"),
        )

    def with_action(self, action: GhPullRequestAction) -> Self:
        self._event.action = action
        return self

    def with_number(self, number: int) -> Self:
        self._event.number = number
        self._event.pull_request.number = number
        return self

    def with_pull_request(self, pr: GhPullRequest) -> Self:
        self._event.pull_request = copy.deepcopy(pr)
        self._event.number = pr.number
        return self

    def with_repository(self, repo: GhRepository) -> Self:
        self._event.repository = copy.deepcopy(repo)
        return self

    def build(self) -> GhPullRequestEvent:
        return copy.deepcopy(self._event)


class GhIssueCommentEventBuilder:
    _event: GhIssueCommentEvent

    def __init__(self) -> None:
        self._event = GhIssueCommentEvent(
            action=GhIssueCommentAction.Created,
            changes=None,
            issue=GhIssue(
                number=1,
                title="Foo",
                user=GhUser(login="foo"),
                body=None,
                created_at=now(),
                labels=[],
                state=GhIssueState.Open,
                updated_at=now(),
            ),
            comment=GhIssueComment(
                body="",
                created_at=now(),
                id=1,
                updated_at=now(),
                user=GhUser(login="foo"),
            ),
            repository=GhRepository(
                name="bar", full_name="foo/bar", owner=GhUser(login="foo")
            ),
            organization=None,
            sender=GhUser(login="foo"),
        )

    def with_repository(self, repository: GhRepository) -> Self:
        self._event.repository = copy.deepcopy(repository)
        return self

    def with_issue(self, issue: GhIssue) -> Self:
        self._event.issue = copy.deepcopy(issue)
        return self

    def with_body(self, value: str) -> Self:
        self._event.comment.body = value
        return self

    def build(self) -> GhIssueCommentEvent:
        return copy.deepcopy(self._event)


class GhReviewEventBuilder:
    _event: GhReviewEvent

    def __init__(self) -> None:
        self._event = GhReviewEvent(
            action=GhReviewAction.Submitted,
            organization=None,
            pull_request=GhPullRequest(
                number=1,
                state=GhPullRequestState.Open,
                locked=False,
                title="Foo",
                base=GhBranch(ref="foo", sha="abc"),
                head=GhBranch(ref="bar", sha="def"),
                body=None,
                created_at=now(),
                updated_at=now(),
                user=GhUser(login="foo"),
                draft=False,
                requested_reviewers=[],
                labels=[],
            ),
            repository=GhRepository(
                name="bar", full_name="foo/bar", owner=GhUser(login="foo")
            ),
            review=GhReview(
                state=GhReviewState.Commented,
                submitted_at=now(),
                user=GhUser(login="rev"),
            ),
            sender=GhUser(login="rev"),
        )

    def with_repository(self, repository: GhRepository) -> Self:
        self._event.repository = copy.deepcopy(repository)
        return self

    def with_pull_request(self, pull_request: GhPullRequest) -> Self:
        self._event.pull_request = copy.deepcopy(pull_request)
        return self

    def with_reviewer(self, login: str) -> Self:
        self._event.review.user.login = login
        return self

    def with_action(self, action: GhReviewAction) -> Self:
        self._event.action = action
        return self

    def with_review_state(self, state: GhReviewState) -> Self:
        self._event.review.state = state
        return self

    def build(self) -> GhReviewEvent:
        return copy.deepcopy(self._event)


class GhCheckSuiteEventBuilder:
    _event: GhCheckSuiteEvent

    def __init__(self) -> None:
        self._event = GhCheckSuiteEvent(
            action=GhCheckSuiteAction.Completed,
            check_suite=GhCheckSuite(
                app=GhApplication(
                    slug="app-slug", name="app-name", owner=GhUser(login="foo")
                ),
                conclusion=None,
                created_at=now(),
                head_branch="head",
                head_sha="abc",
                id=1,
                pull_requests=[
                    GhPullRequestShort(
                        base=GhBranchShort(ref="base", sha="abc"),
                        head=GhBranchShort(ref="head", sha="def"),
                        number=1,
                    )
                ],
                status=GhCheckStatus.InProgress,
                updated_at=now(),
            ),
            organization=None,
            repository=GhRepository(
                name="bar", full_name="foo/bar", owner=GhUser(login="foo")
            ),
            sender=GhUser(login="foo"),
        )

    def with_app(self, application: GhApplication) -> Self:
        self._event.check_suite.app = copy.deepcopy(application)
        return self

    def with_conclusion(self, conclusion: GhCheckConclusion | None) -> Self:
        self._event.check_suite.conclusion = conclusion
        return self

    def with_status(self, status: GhCheckStatus) -> Self:
        self._event.check_suite.status = status
        return self

    def with_pull_request(self, pull_request: GhPullRequestShort) -> Self:
        self._event.check_suite.pull_requests = [copy.deepcopy(pull_request)]
        self._event.check_suite.head_branch = pull_request.head.ref
        self._event.check_suite.head_sha = pull_request.head.sha
        return self

    def with_repository(self, repository: GhRepository) -> Self:
        self._event.repository = copy.deepcopy(repository)
        return self

    def build(self) -> GhCheckSuiteEvent:
        return copy.deepcopy(self._event)


class GhEventBuilder:
    def ping(self) -> GhPingEventBuilder:
        return GhPingEventBuilder()

    def pull_request(self) -> GhPullRequestEventBuilder:
        return GhPullRequestEventBuilder()

    def issue_comment(self) -> GhIssueCommentEventBuilder:
        return GhIssueCommentEventBuilder()

    def review(self) -> GhReviewEventBuilder:
        return GhReviewEventBuilder()

    def check_suite(self) -> GhCheckSuiteEventBuilder:
        return GhCheckSuiteEventBuilder()
