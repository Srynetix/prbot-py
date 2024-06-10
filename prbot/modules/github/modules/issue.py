import structlog

from prbot.modules.github.models import (
    GhCommentRequest,
    GhCommentResponse,
    GhLabelsRequest,
    GhLabelsResponse,
)

from .base import GitHubModule

logger = structlog.get_logger()


class GitHubIssueModule(GitHubModule):
    async def labels(self, *, owner: str, name: str, number: int) -> list[str]:
        labels = await self._core.get_all(
            model_type=GhLabelsResponse,
            path=f"/repos/{owner}/{name}/issues/{number}/labels",
        )

        label_names = [label.name for label in labels]

        logger.info(
            "Fetching GitHub labels",
            owner=owner,
            name=name,
            number=number,
            labels=label_names,
        )

        return label_names

    async def replace_labels(
        self, *, owner: str, name: str, number: int, labels: list[str]
    ) -> None:
        logger.info(
            "Replacing GitHub labels",
            owner=owner,
            name=name,
            number=number,
            labels=labels,
        )

        await self._core.request(
            method="PUT",
            path=f"/repos/{owner}/{name}/issues/{number}/labels",
            json=GhLabelsRequest(labels=labels).model_dump(),
        )

    async def add_labels(
        self, *, owner: str, name: str, number: int, labels: list[str]
    ) -> None:
        logger.info(
            "Replacing GitHub labels",
            owner=owner,
            name=name,
            number=number,
            labels=labels,
        )

        await self._core.request(
            method="POST",
            path=f"/repos/{owner}/{name}/issues/{number}/labels",
            json=GhLabelsRequest(labels=labels).model_dump(),
        )

    async def create_comment(
        self, *, owner: str, name: str, number: int, message: str
    ) -> int:
        logger.info(
            "Creating GitHub comment",
            owner=owner,
            name=name,
            number=number,
            message=message,
        )
        response = await self._core.request(
            method="POST",
            path=f"/repos/{owner}/{name}/issues/{number}/comments",
            json=GhCommentRequest(body=message).model_dump(),
        )

        data = GhCommentResponse.model_validate(response.json())
        return data.id

    async def update_comment(
        self, *, owner: str, name: str, comment_id: int, message: str
    ) -> int:
        logger.info(
            "Updating GitHub comment",
            owner=owner,
            name=name,
            comment_id=comment_id,
            message=message,
        )
        response = await self._core.request(
            method="PATCH",
            path=f"/repos/{owner}/{name}/issues/comments/{comment_id}",
            json=GhCommentRequest(body=message).model_dump(),
        )

        data = GhCommentResponse.model_validate(response.json())
        return data.id
