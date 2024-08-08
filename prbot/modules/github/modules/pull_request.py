import structlog

from prbot.core.models import MergeStrategy
from prbot.modules.github.models import (
    GhMergeableState,
    GhMergeStateStatus,
    GhPullRequest,
    GhPullRequestExtraData,
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

    async def get_extra_data(
        self, *, owner: str, name: str, number: int
    ) -> GhPullRequestExtraData:
        graph_query = """
            query {{
                repository(owner: "{owner}", name: "{name}") {{
                    pullRequest(number: {number}) {{
                        reviewDecision
                        mergeable
                        mergeStateStatus
                    }}
                }}
            }}
        """.format(owner=owner, name=name, number=number)

        response = await self._core.request(
            method="POST", path="/graphql", json={"query": graph_query}
        )

        data = response.json()
        decision_raw = data["data"]["repository"]["pullRequest"]["reviewDecision"]
        if decision_raw is not None:
            decision = GhReviewDecision(decision_raw)
        else:
            decision = None

        mergeable_state = GhMergeableState(
            data["data"]["repository"]["pullRequest"]["mergeable"]
        )
        merge_state_status = GhMergeStateStatus(
            data["data"]["repository"]["pullRequest"]["mergeStateStatus"]
        )

        return GhPullRequestExtraData(
            review_decision=decision,
            mergeable_state=mergeable_state,
            merge_state_status=merge_state_status,
        )
