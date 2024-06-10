from pydantic import BaseModel

from prbot.modules.github.models import GhReactionType

from .base import GitHubModule


class GitHubReactionModule(GitHubModule):
    async def add(
        self, *, owner: str, name: str, comment_id: int, reaction: GhReactionType
    ) -> None:
        class _Request(BaseModel):
            content: str

        await self._core.request(
            method="POST",
            path=f"/repos/{owner}/{name}/issues/comments/{comment_id}/reactions",
            json=_Request(content=reaction.value).model_dump(),
        )
