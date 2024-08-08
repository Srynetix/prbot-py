import enum


class StepLabel(enum.StrEnum):
    Wip = "wip"
    AwaitingChanges = "awaiting-changes"
    AwaitingChecks = "awaiting-checks"
    AwaitingReview = "awaiting-review"
    AwaitingQa = "awaiting-qa"
    Locked = "locked"
    AwaitingMerge = "awaiting-merge"
    Merged = "merged"
