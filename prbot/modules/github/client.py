from abc import ABC, abstractmethod
from typing import override

from prbot.config.settings import get_global_settings
from prbot.modules.http.client import HttpClient

from .core import AuthenticationTypeEnum, GitHubClientNotAuthenticated, GitHubCore
from .modules import check_run, commit_status, issue, pull_request, reaction, repository


class GitHubClient(ABC):
    @abstractmethod
    def core(self) -> GitHubCore: ...
    @abstractmethod
    def repositories(self) -> repository.GitHubRepositoryModule: ...
    @abstractmethod
    def pull_requests(self) -> pull_request.GitHubPullRequestModule: ...
    @abstractmethod
    def issues(self) -> issue.GitHubIssueModule: ...
    @abstractmethod
    def check_runs(self) -> check_run.GitHubCheckRunModule: ...
    @abstractmethod
    def commit_statuses(self) -> commit_status.GitHubStatusModule: ...
    @abstractmethod
    def reactions(self) -> reaction.GitHubReactionModule: ...

    async def aclose(self) -> None:
        await self.core().aclose()

    async def setup_client_for_repository(self, *, owner: str, name: str) -> None:
        """
        Setup the GitHub client to work with a specific repository.

        - If the client is not authenticated, it will raise an exception,
        - If the client is in "app" mode, it will look for an installation ID and
          generate an installation access token,
        - If the client is already in "installation" mode or "user" mode, it will do nothing.
        """

        if self.core().authentication_type.type == AuthenticationTypeEnum.Anonymous:
            raise GitHubClientNotAuthenticated()
        elif self.core().authentication_type.type == AuthenticationTypeEnum.App:
            installation = await self.repositories().installation(
                owner=owner, name=name
            )
            await self.core().upgrade_app_authentication(
                installation_id=installation.id
            )


class GitHubClientImplementation(GitHubClient):
    _core: GitHubCore
    _repositories: repository.GitHubRepositoryModule
    _pull_requests: pull_request.GitHubPullRequestModule
    _issues: issue.GitHubIssueModule
    _check_runs: check_run.GitHubCheckRunModule
    _commit_statuses: commit_status.GitHubStatusModule
    _reactions: reaction.GitHubReactionModule

    @override
    def core(self) -> GitHubCore:
        return self._core

    @override
    def repositories(self) -> repository.GitHubRepositoryModule:
        return self._repositories

    @override
    def pull_requests(self) -> pull_request.GitHubPullRequestModule:
        return self._pull_requests

    @override
    def issues(self) -> issue.GitHubIssueModule:
        return self._issues

    @override
    def check_runs(self) -> check_run.GitHubCheckRunModule:
        return self._check_runs

    @override
    def commit_statuses(self) -> commit_status.GitHubStatusModule:
        return self._commit_statuses

    @override
    def reactions(self) -> reaction.GitHubReactionModule:
        return self._reactions

    def __init__(self, client: HttpClient) -> None:
        headers = {
            "Accept": "application/vnd.github.squirrel-girl-preview",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self._core = GitHubCore(client)
        self._core.client.configure(headers=headers, base_url="https://api.github.com")

        self._repositories = repository.GitHubRepositoryModule(self._core)
        self._pull_requests = pull_request.GitHubPullRequestModule(self._core)
        self._issues = issue.GitHubIssueModule(self._core)
        self._check_runs = check_run.GitHubCheckRunModule(self._core)
        self._commit_statuses = commit_status.GitHubStatusModule(self._core)
        self._reactions = reaction.GitHubReactionModule(self._core)

        # Configure authentication
        settings = get_global_settings()
        if (
            settings.github_app_client_id != ""
            and settings.github_app_private_key != ""
        ):
            self._core.set_app_authentication(
                client_id=settings.github_app_client_id,
                private_key=settings.github_app_private_key,
            )
        elif settings.github_personal_token != "":
            self._core.set_user_authentication(
                personal_token=settings.github_personal_token
            )
