from tortoise import fields
from tortoise.models import Model


class RepositoryModel(Model):
    id = fields.IntField(primary_key=True)
    owner = fields.CharField(max_length=255)
    name = fields.CharField(max_length=255)
    manual_interaction = fields.BooleanField()
    pr_title_validation_regex = fields.TextField()
    default_strategy = fields.CharField(max_length=255)
    default_automerge = fields.BooleanField()
    default_enable_qa = fields.BooleanField()
    default_enable_checks = fields.BooleanField()

    class Meta:
        table = "repository"
        unique_together = [("name", "owner")]


class PullRequestModel(Model):
    id = fields.IntField(primary_key=True)
    repository = fields.ForeignKeyField(
        "prbot.RepositoryModel", related_name="pull_requests"
    )
    number = fields.IntField()
    qa_status = fields.CharField(max_length=255)
    status_comment_id = fields.BigIntField()
    checks_enabled = fields.BooleanField()
    automerge = fields.BooleanField()
    locked = fields.BooleanField()
    strategy_override = fields.CharField(max_length=255, null=True)

    # For typing
    repository_id: int

    class Meta:
        table = "pull_request"
        unique_together = [("repository", "number")]


class RepositoryRuleModel(Model):
    id = fields.IntField(primary_key=True)
    repository = fields.ForeignKeyField(
        "prbot.RepositoryModel", related_name="repository_rules"
    )
    name = fields.CharField(max_length=255)
    conditions = fields.TextField()
    actions = fields.TextField()

    # For typing
    repository_id: int

    class Meta:
        table = "repository_rule"
        unique_together = [("repository", "name")]


class MergeRuleModel(Model):
    id = fields.IntField(primary_key=True)
    repository = fields.ForeignKeyField(
        "prbot.RepositoryModel", related_name="merge_rules"
    )
    base_branch = fields.CharField(max_length=255)
    head_branch = fields.CharField(max_length=255)
    strategy = fields.CharField(max_length=255)

    # For typing
    repository_id: int

    class Meta:
        table = "merge_rule"
        unique_together = [("repository", "base_branch", "head_branch")]


class ExternalAccountModel(Model):
    username = fields.CharField(max_length=255, primary_key=True, unique=True)
    public_key = fields.TextField()
    private_key = fields.TextField()

    class Meta:
        table = "external_account"


class ExternalAccountRightModel(Model):
    id = fields.IntField(primary_key=True)
    account = fields.ForeignKeyField(
        "prbot.ExternalAccountModel", related_name="rights"
    )
    repository = fields.ForeignKeyField("prbot.RepositoryModel", related_name="rights")

    # For typing
    repository_id: int

    class Meta:
        table = "external_account_right"
        unique_together = [("account", "repository")]
