from pydantic import BaseModel

from prbot.modules.github.models import GhCommitStatusState

from .base import GitHubModule


class GitHubStatusModule(GitHubModule):
    async def update(
        self,
        *,
        owner: str,
        name: str,
        commit_ref: str,
        state: GhCommitStatusState,
        title: str,
        body: str,
    ) -> None:
        MAX_DESCRIPTION_LEN = 139

        class _Request(BaseModel):
            state: str
            description: str
            context: str

        await self._core.request(
            method="POST",
            path=f"/repos/{owner}/{name}/statuses/{commit_ref}",
            json=_Request(
                state=state.value, description=body[:MAX_DESCRIPTION_LEN], context=title
            ).model_dump(),
        )
