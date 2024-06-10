import enum


class GhEventType(enum.StrEnum):
    CheckSuite = "check_suite"
    IssueComment = "issue_comment"
    Ping = "ping"
    PullRequest = "pull_request"
    PullRequestReview = "pull_request_review"
