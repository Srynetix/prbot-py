import copy
import enum
from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field


class GhUser(BaseModel):
    login: str


class GhRepository(BaseModel):
    name: str
    full_name: str
    owner: GhUser


class GhApplication(BaseModel):
    slug: str
    owner: GhUser
    name: str


class GhLabel(BaseModel):
    name: str
    color: str | None = None
    description: str | None = None


class GhBranch(BaseModel):
    ref: str
    sha: str
    label: str | None = None
    user: GhUser | None = None


class GhBranchShort(BaseModel):
    ref: str
    sha: str


class GhIssueCommentAction(enum.StrEnum):
    Created = "created"
    Edited = "edited"
    Deleted = "deleted"


class GhIssueCommentChangesBody(BaseModel):
    from_: str = Field(validation_alias=AliasChoices("from"))


class GhIssueCommentChanges(BaseModel):
    body: GhIssueCommentChangesBody


class GhIssueComment(BaseModel):
    id: int
    user: GhUser
    created_at: datetime
    updated_at: datetime
    body: str


class GhIssueState(enum.StrEnum):
    Open = "open"
    Closed = "closed"


class GhPullRequestState(enum.StrEnum):
    Open = "open"
    Closed = "closed"
    Merged = "merged"

    def to_issue_state(self) -> GhIssueState:
        if self == self.Open:
            return GhIssueState.Open
        return GhIssueState.Closed


class GhIssue(BaseModel):
    number: int
    title: str
    user: GhUser
    labels: list[GhLabel]
    state: GhIssueState
    created_at: datetime
    updated_at: datetime
    body: str | None = None


class GhPullRequestAction(enum.StrEnum):
    Assigned = "assigned"
    Closed = "closed"
    ConvertedToDraft = "converted_to_draft"
    Edited = "edited"
    Labeled = "labeled"
    Locked = "locked"
    Opened = "opened"
    Reopened = "reopened"
    ReadyForReview = "ready_for_review"
    ReviewRequested = "review_requested"
    ReviewRequestRemoved = "review_request_removed"
    Synchronize = "synchronize"
    Unassigned = "unassigned"
    Unlabeled = "unlabeled"
    Unlocked = "unlocked"


class GhMergeStrategy(enum.StrEnum):
    Merge = "merge"
    Squash = "squash"
    Rebase = "rebase"


class GhMergeableState(enum.StrEnum):
    Conflicting = "CONFLICTING"
    Mergeable = "MERGEABLE"
    Unknown = "UNKNOWN"


class GhMergeStateStatus(enum.StrEnum):
    Behind = "BEHIND"
    Blocked = "BLOCKED"
    Clean = "CLEAN"
    Dirty = "DIRTY"
    Draft = "DRAFT"
    HasHooks = "HAS_HOOKS"
    Unknown = "UNKNOWN"
    Unstable = "UNSTABLE"


class GhPullRequestShort(BaseModel):
    number: int
    head: GhBranchShort
    base: GhBranchShort


class GhPullRequest(BaseModel):
    number: int
    state: GhPullRequestState
    locked: bool
    title: str
    user: GhUser
    body: str | None = None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    merged_at: datetime | None = None
    requested_reviewers: list[GhUser]
    labels: list[GhLabel]
    draft: bool
    head: GhBranch
    base: GhBranch
    merged: bool | None = None

    def to_short_format(self) -> GhPullRequestShort:
        return GhPullRequestShort(
            number=self.number,
            head=GhBranchShort(ref=self.head.ref, sha=self.head.sha),
            base=GhBranchShort(ref=self.base.ref, sha=self.base.sha),
        )

    def to_issue(self) -> GhIssue:
        return GhIssue(
            body=self.body,
            created_at=self.created_at,
            labels=copy.deepcopy(self.labels),
            number=self.number,
            state=self.state.to_issue_state(),
            title=self.title,
            updated_at=self.updated_at,
            user=copy.deepcopy(self.user),
        )


class GhCheckSuiteAction(enum.StrEnum):
    Completed = "completed"
    Requested = "requested"
    Rerequested = "rerequested"


class GhCheckStatus(enum.StrEnum):
    Completed = "completed"
    InProgress = "in_progress"
    Queued = "queued"
    Requested = "requested"
    Pending = "pending"


class GhCheckConclusion(enum.StrEnum):
    ActionRequired = "action_required"
    Cancelled = "cancelled"
    Failure = "failure"
    Neutral = "neutral"
    Skipped = "skipped"
    Stale = "stale"
    StartupFailure = "startup_failure"
    Success = "success"
    TimedOut = "timed_out"


class GhCheckRun(BaseModel):
    id: int
    name: str
    head_sha: str
    status: GhCheckStatus
    conclusion: GhCheckConclusion | None = None
    pull_requests: list[GhPullRequestShort]
    app: GhApplication
    started_at: datetime
    completed_at: datetime | None = None


class GhCheckSuite(BaseModel):
    id: int
    head_branch: str
    head_sha: str
    status: GhCheckStatus
    conclusion: GhCheckConclusion | None = None
    pull_requests: list[GhPullRequestShort]
    app: GhApplication
    created_at: datetime
    updated_at: datetime


class GhReviewState(enum.StrEnum):
    Approved = "approved"
    ChangesRequested = "changes_requested"
    Commented = "commented"
    Dismissed = "dismissed"
    Pending = "pending"


class GhReviewDecision(enum.StrEnum):
    Approved = "APPROVED"
    ChangesRequested = "CHANGES_REQUESTED"
    ReviewRequired = "REVIEW_REQUIRED"


class GhApiReviewState(enum.StrEnum):
    Approved = "APPROVED"
    ChangesRequested = "CHANGES_REQUESTED"
    Commented = "COMMENTED"
    Dismissed = "DISMISSED"
    Pending = "PENDING"

    def to_review_state(self) -> GhReviewState:
        return GhReviewState[self.name]


class GhApiCheckSuiteResponse(BaseModel):
    check_runs: list[GhCheckRun]


class GhReviewAction(enum.StrEnum):
    Submitted = "submitted"
    Edited = "edited"
    Dismissed = "dismissed"


class GhReview(BaseModel):
    user: GhUser
    submitted_at: datetime | None = None
    state: GhReviewState


class GhApiReview(BaseModel):
    user: GhUser
    submitted_at: datetime
    state: GhApiReviewState

    def to_review(self) -> GhReview:
        return GhReview(
            user=self.user,
            submitted_at=self.submitted_at,
            state=self.state.to_review_state(),
        )


class GhCommitStatusState(enum.StrEnum):
    Error = "error"
    Failure = "failure"
    Pending = "pending"
    Success = "success"


class GhCommitStatusItem(BaseModel):
    state: GhCommitStatusState
    context: str
    created_at: datetime
    updated_at: datetime


class GhCommitStatus(BaseModel):
    state: GhCommitStatusState
    items: list[GhCommitStatusItem]


class GhReactionType(enum.StrEnum):
    PlusOne = "+1"
    MinusOne = "-1"
    Laugh = "laugh"
    Confused = "confused"
    Heart = "heart"
    Hooray = "hooray"
    Rocket = "rocket"
    Eyes = "eyes"


class GhCommentRequest(BaseModel):
    body: str


class GhCommentResponse(BaseModel):
    id: int


class GhLabelsRequest(BaseModel):
    labels: list[str]


class GhLabelsResponse(BaseModel):
    name: str


class GhReviewersAddRequest(BaseModel):
    reviewers: list[str]


class GhReviewersRemoveRequest(BaseModel):
    reviewers: list[str]


class GhInstallationAccessTokenResponse(BaseModel):
    token: str
    expires_at: datetime


class GhRepositoryInstallation(BaseModel):
    id: int


class GhRepositoryUserPermission(BaseModel):
    permission: str
    role_name: str


class GhPullRequestMergeRequest(BaseModel):
    commit_title: str
    commit_message: str
    merge_method: str


class GhPullRequestExtraData(BaseModel):
    review_decision: GhReviewDecision | None
    mergeable_state: GhMergeableState
    merge_state_status: GhMergeStateStatus
