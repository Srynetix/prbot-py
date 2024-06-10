from prbot.core.models import CheckStatus, QaStatus
from prbot.core.step.models import StepLabel
from prbot.core.sync.sync_state import PullRequestSyncState


class StepLabelBuilder:
    def build(self, *, sync_state: PullRequestSyncState) -> StepLabel:
        if sync_state.wip:
            return StepLabel.Wip

        elif sync_state.valid_pr_title:
            if sync_state.check_status in [CheckStatus.Pass, CheckStatus.Skipped]:
                if sync_state.changes_requested or (
                    not sync_state.mergeable and not sync_state.merged
                ):
                    return StepLabel.AwaitingChanges

                elif sync_state.review_required:
                    return StepLabel.AwaitingReview

                else:
                    if sync_state.qa_status == QaStatus.Fail:
                        return StepLabel.AwaitingChanges
                    elif sync_state.qa_status == QaStatus.Waiting:
                        return StepLabel.AwaitingQa
                    else:
                        if sync_state.locked:
                            return StepLabel.Locked
                        else:
                            return StepLabel.AwaitingMerge

            elif sync_state.check_status == CheckStatus.Waiting:
                return StepLabel.AwaitingChecks
            else:
                return StepLabel.AwaitingChanges

        else:
            return StepLabel.AwaitingChanges
