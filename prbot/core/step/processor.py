from prbot.core.sync.sync_state import PullRequestSyncState
from prbot.injection import inject_instance
from prbot.modules.github.client import GitHubClient

from .builder import StepLabelBuilder
from .models import StepLabel


class StepLabelProcessor:
    _api: GitHubClient
    _builder: StepLabelBuilder

    def __init__(self) -> None:
        self._api = inject_instance(GitHubClient)
        self._builder = StepLabelBuilder()

    async def process(self, *, sync_state: PullRequestSyncState) -> StepLabel:
        step_label = self._builder.build(sync_state=sync_state)
        await self._replace_step_label(
            owner=sync_state.owner,
            name=sync_state.name,
            number=sync_state.number,
            label=step_label,
        )
        return step_label

    async def _replace_step_label(
        self, *, owner: str, name: str, number: int, label: StepLabel
    ) -> None:
        existing_labels = await self._api.issues().labels(
            owner=owner, name=name, number=number
        )

        new_labels = [
            label for label in existing_labels if not label.startswith("step/")
        ]
        new_labels.append(f"step/{label}")
        new_labels.sort()

        await self._api.issues().replace_labels(
            owner=owner, name=name, number=number, labels=new_labels
        )
