from pydantic import BaseModel

from prbot.modules.github.models import (
    GhCheckSuite,
    GhCheckSuiteAction,
    GhIssue,
    GhIssueComment,
    GhIssueCommentAction,
    GhIssueCommentChanges,
    GhLabel,
    GhPullRequest,
    GhPullRequestAction,
    GhRepository,
    GhReview,
    GhReviewAction,
    GhUser,
)


class GhPingEvent(BaseModel):
    zen: str
    hook_id: int
    repository: GhRepository | None = None
    sender: GhUser | None = None


class GhCheckSuiteEvent(BaseModel):
    action: GhCheckSuiteAction
    check_suite: GhCheckSuite
    repository: GhRepository
    organization: GhUser | None = None
    sender: GhUser


class GhIssueCommentEvent(BaseModel):
    action: GhIssueCommentAction
    changes: GhIssueCommentChanges | None = None
    issue: GhIssue
    comment: GhIssueComment
    repository: GhRepository
    organization: GhUser | None = None
    sender: GhUser


class GhPullRequestEvent(BaseModel):
    action: GhPullRequestAction
    number: int
    pull_request: GhPullRequest
    label: GhLabel | None = None
    requested_reviewer: GhUser | None = None
    repository: GhRepository
    organization: GhUser | None = None
    sender: GhUser


class GhReviewEvent(BaseModel):
    action: GhReviewAction
    review: GhReview
    pull_request: GhPullRequest
    repository: GhRepository
    organization: GhUser | None = None
    sender: GhUser
