from prbot.modules.github.models import GhApiCheckSuiteResponse, GhCheckRun

from .base import GitHubModule


class GitHubCheckRunModule(GitHubModule):
    async def for_commit(
        self, *, owner: str, name: str, commit_sha: str
    ) -> list[GhCheckRun]:
        return await self._core.get_all(
            root_type=GhApiCheckSuiteResponse,
            model_type=GhCheckRun,
            extract_fn=lambda root: root.check_runs,
            path=f"/repos/{owner}/{name}/commits/{commit_sha}/check-runs",
        )
