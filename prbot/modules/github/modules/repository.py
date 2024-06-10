import structlog

from prbot.modules.github.models import (
    GhRepository,
    GhRepositoryInstallation,
    GhRepositoryUserPermission,
)

from .base import GitHubModule

logger = structlog.get_logger()


class GitHubRepositoryModule(GitHubModule):
    async def get(self, *, owner: str, name: str) -> GhRepository:
        response = await self._core.request(method="GET", path=f"/repos/{owner}/{name}")
        return GhRepository.model_validate(response.json())

    async def installation(self, *, owner: str, name: str) -> GhRepositoryInstallation:
        response = await self._core.request(
            method="GET", path=f"/repos/{owner}/{name}/installation"
        )
        installation = GhRepositoryInstallation.model_validate(response.json())

        logger.info(
            "Fetching repository installation",
            owner=owner,
            name=name,
            installation_id=installation.id,
        )
        return installation

    async def user_permission(
        self, *, owner: str, name: str, username: str
    ) -> GhRepositoryUserPermission:
        response = await self._core.request(
            method="GET", path=f"/repos/{owner}/{name}/installation"
        )
        permission = GhRepositoryUserPermission.model_validate(response.json())

        logger.info(
            "Fetching user permission on repository",
            owner=owner,
            name=name,
            username=username,
        )
        return permission
