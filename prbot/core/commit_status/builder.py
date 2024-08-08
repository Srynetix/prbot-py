from typing import ClassVar

from prbot.core.models import (
    CheckStatus,
    QaStatus,
)
from prbot.core.sync.sync_state import PullRequestSyncState
from prbot.modules.github.models import (
    GhCommitStatusState,
)

from .models import StatusMessage


class CommitStatusBuilder:
    VALIDATION_STATUS_MESSAGE: ClassVar[str] = "Validation"

    def build(self, *, sync_state: PullRequestSyncState) -> StatusMessage:
        title = self.VALIDATION_STATUS_MESSAGE
        state = GhCommitStatusState.Success
        message = "All good"

        if sync_state.merged:
            message = "PR merged"
            state = GhCommitStatusState.Success
        elif sync_state.wip:
            message = "PR is still in WIP"
            state = GhCommitStatusState.Pending
        elif sync_state.valid_pr_title:
            if sync_state.check_status == CheckStatus.Fail:
                message = "Checks failed"
                state = GhCommitStatusState.Failure
            elif sync_state.check_status == CheckStatus.Waiting:
                message = "Waiting for checks"
                state = GhCommitStatusState.Pending
            else:
                if sync_state.changes_requested:
                    message = "Changes required"
                    state = GhCommitStatusState.Failure
                elif not sync_state.can_merge:
                    message = "PR is not mergeable yet"
                    state = GhCommitStatusState.Pending
                elif sync_state.review_required:
                    message = "Waiting on reviews"
                    state = GhCommitStatusState.Pending
                else:
                    if sync_state.qa_status == QaStatus.Fail:
                        message = "Did not pass QA"
                        state = GhCommitStatusState.Failure
                    elif sync_state.qa_status == QaStatus.Waiting:
                        message = "Waiting for QA"
                        state = GhCommitStatusState.Pending
                    else:
                        if sync_state.locked:
                            message = "PR ready to merge, but is merge locked"
                            state = GhCommitStatusState.Failure
        else:
            message = "PR title is not valid"
            state = GhCommitStatusState.Failure

        return StatusMessage(state=state, title=title, message=message)
