import enum
import json
import re
from abc import ABC, abstractmethod
from typing import Any, Self

from pydantic import BaseModel


class RepositoryPath(BaseModel):
    owner: str
    name: str

    @classmethod
    def from_str(cls, value: str) -> Self:
        owner, name = value.split("/")
        return cls(owner=owner, name=name)

    def __str__(self) -> str:
        return f"{self.owner}/{self.name}"


class PullRequestPath(BaseModel):
    owner: str
    name: str
    number: int

    @classmethod
    def from_str(cls, value: str) -> Self:
        repository_path_str, number = value.split("#")
        owner, name = repository_path_str.split("/")
        return cls(owner=owner, name=name, number=int(number))


class ExternalAccount(BaseModel):
    username: str
    public_key: str
    private_key: str


class ExternalAccountRight(BaseModel):
    repository_path: RepositoryPath
    username: str


class MergeStrategy(enum.StrEnum):
    Merge = "merge"
    Squash = "squash"
    Rebase = "rebase"


class RuleBranchType(enum.StrEnum):
    Named = "named"
    Wildcard = "wildcard"


class RuleBranchBase(ABC, BaseModel):
    @abstractmethod
    def get_name(self) -> str: ...


class NamedRuleBranch(RuleBranchBase):
    type: RuleBranchType = RuleBranchType.Named
    value: str

    def get_name(self) -> str:
        return self.value


class WildcardRuleBranch(RuleBranchBase):
    type: RuleBranchType = RuleBranchType.Wildcard

    def get_name(self) -> str:
        return "*"


RuleBranch = NamedRuleBranch | WildcardRuleBranch


class RuleBranchFactory:
    @staticmethod
    def from_str(value: str) -> RuleBranch:
        if value == "*":
            return WildcardRuleBranch()
        else:
            return NamedRuleBranch(value=value)


class MergeRule(BaseModel):
    repository_path: RepositoryPath
    base_branch: RuleBranch
    head_branch: RuleBranch
    strategy: MergeStrategy


class Repository(BaseModel):
    owner: str
    name: str
    manual_interaction: bool = False
    pr_title_validation_regex: re.Pattern[str] = re.compile("")
    default_strategy: MergeStrategy = MergeStrategy.Merge
    default_automerge: bool = False
    default_enable_qa: bool = True
    default_enable_checks: bool = True

    def path(self) -> RepositoryPath:
        return RepositoryPath(owner=self.owner, name=self.name)


class QaStatus(enum.StrEnum):
    Waiting = "waiting"
    Skipped = "skipped"
    Pass = "pass"
    Fail = "fail"


class CheckStatus(enum.StrEnum):
    Waiting = "waiting"
    Skipped = "skipped"
    Pass = "pass"
    Fail = "fail"


class RuleConditionType(enum.StrEnum):
    BaseBranch = "base_branch"
    HeadBranch = "head_branch"
    Author = "author"


class RuleConditionBaseBranch(BaseModel):
    type: RuleConditionType = RuleConditionType.BaseBranch
    value: RuleBranch


class RuleConditionHeadBranch(BaseModel):
    type: RuleConditionType = RuleConditionType.HeadBranch
    value: RuleBranch


class RuleConditionAuthor(BaseModel):
    type: RuleConditionType = RuleConditionType.Author
    value: str


RuleCondition = RuleConditionBaseBranch | RuleConditionHeadBranch | RuleConditionAuthor


class RuleActionType(enum.StrEnum):
    SetAutomerge = "set_automerge"
    SetQaEnabled = "set_qa_enabled"
    SetChecksEnabled = "set_checks_enabled"


class RuleActionSetAutomerge(BaseModel):
    type: RuleActionType = RuleActionType.SetAutomerge
    value: bool


class RuleActionSetQaStatus(BaseModel):
    type: RuleActionType = RuleActionType.SetQaEnabled
    value: QaStatus


class RuleActionSetChecksEnabled(BaseModel):
    type: RuleActionType = RuleActionType.SetChecksEnabled
    value: bool


RuleAction = RuleActionSetAutomerge | RuleActionSetChecksEnabled | RuleActionSetQaStatus


class RuleActionFactory:
    @staticmethod
    def from_str(value: str) -> RuleAction:
        return RuleActionFactory.from_dict(json.loads(value))

    @staticmethod
    def from_dict(dict_obj: dict[str, Any]) -> RuleAction:
        action_type = RuleActionType(dict_obj.get("type", ""))

        if action_type == RuleActionType.SetAutomerge:
            return RuleActionSetAutomerge.model_validate(dict_obj)
        elif action_type == RuleActionType.SetChecksEnabled:
            return RuleActionSetChecksEnabled.model_validate(dict_obj)
        else:
            return RuleActionSetQaStatus.model_validate(dict_obj)

    @staticmethod
    def from_str_many(value: str) -> list[RuleAction]:
        json_data = json.loads(value)
        return [RuleActionFactory.from_dict(entry) for entry in json_data]

    @staticmethod
    def many_to_str(actions: list[RuleAction]) -> str:
        return json.dumps([action.model_dump() for action in actions])


class RuleConditionFactory:
    @staticmethod
    def from_str(value: str) -> RuleCondition:
        return RuleConditionFactory.from_dict(json.loads(value))

    @staticmethod
    def from_dict(dict_obj: dict[str, Any]) -> RuleCondition:
        condition_type = RuleConditionType(dict_obj.get("type", ""))

        if condition_type == RuleConditionType.Author:
            return RuleConditionAuthor.model_validate(dict_obj)
        elif condition_type == RuleConditionType.BaseBranch:
            return RuleConditionBaseBranch.model_validate(dict_obj)
        else:
            return RuleConditionHeadBranch.model_validate(dict_obj)

    @staticmethod
    def from_str_many(value: str) -> list[RuleCondition]:
        json_data = json.loads(value)
        return [RuleConditionFactory.from_dict(entry) for entry in json_data]

    @staticmethod
    def many_to_str(conditions: list[RuleCondition]) -> str:
        return json.dumps([condition.model_dump() for condition in conditions])


class RepositoryRule(BaseModel):
    repository_path: RepositoryPath
    name: str
    conditions: list[RuleCondition]
    actions: list[RuleAction]


class PullRequest(BaseModel):
    repository_path: RepositoryPath
    number: int
    qa_status: QaStatus = QaStatus.Waiting
    status_comment_id: int = 0
    checks_enabled: bool = True
    automerge: bool = False
    locked: bool = False
    strategy_override: MergeStrategy | None = None
