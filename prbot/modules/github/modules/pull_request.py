import structlog

from prbot.core.models import MergeStrategy
from prbot.modules.github.models import (
    GhPullRequest,
    GhPullRequestMergeRequest,
    GhReviewDecision,
    GhReviewersAddRequest,
    GhReviewersRemoveRequest,
)

from .base import GitHubModule

logger = structlog.get_logger()


class GitHubPullRequestModule(GitHubModule):
    async def get(self, *, owner: str, name: str, number: int) -> GhPullRequest:
        response = await self._core.request(
            method="GET", path=f"/repos/{owner}/{name}/pulls/{number}"
        )
        return GhPullRequest.model_validate(response.json())

    async def add_reviewers(
        self, *, owner: str, name: str, number: int, reviewers: list[str]
    ) -> None:
        await self._core.request(
            method="POST",
            path=f"/repos/{owner}/{name}/pulls/{number}/requested_reviewers",
            json=GhReviewersAddRequest(reviewers=reviewers).model_dump(),
        )

    async def remove_reviewers(
        self, *, owner: str, name: str, number: int, reviewers: list[str]
    ) -> None:
        await self._core.request(
            method="DELETE",
            path=f"/repos/{owner}/{name}/pulls/{number}/requested_reviewers",
            json=GhReviewersRemoveRequest(reviewers=reviewers).model_dump(),
        )

    async def merge(
        self,
        *,
        owner: str,
        name: str,
        number: int,
        commit_title: str,
        commit_message: str,
        strategy: MergeStrategy,
    ) -> None:
        logger.info(
            "Will merge pull request",
            owner=owner,
            name=name,
            number=number,
            strategy=strategy,
        )

        await self._core.request(
            method="PUT",
            path=f"/repos/{owner}/{name}/pulls/{number}/merge",
            json=GhPullRequestMergeRequest(
                commit_title=commit_title,
                commit_message=commit_message,
                merge_method=strategy.value,
            ).model_dump(),
        )

    async def review_decision(
        self, *, owner: str, name: str, number: int
    ) -> GhReviewDecision | None:
        graph_query = """
            query {{
                repository(owner: "{owner}", name: "{name}") {{
                    pullRequest(number: {number}) {{
                        reviewDecision
                    }}
                }}
            }}
        """.format(owner=owner, name=name, number=number)

        response = await self._core.request(
            method="POST", path="/graphql", json={"query": graph_query}
        )

        data = response.json()
        decision = data["data"]["repository"]["pullRequest"]["reviewDecision"]
        if decision is not None:
            return GhReviewDecision(decision)
        return None
