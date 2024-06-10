from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "external_account" (
    "username" VARCHAR(255) NOT NULL  PRIMARY KEY,
    "public_key" TEXT NOT NULL,
    "private_key" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "repository" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "owner" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "manual_interaction" BOOL NOT NULL,
    "pr_title_validation_regex" TEXT NOT NULL,
    "default_strategy" VARCHAR(255) NOT NULL,
    "default_automerge" BOOL NOT NULL,
    "default_enable_qa" BOOL NOT NULL,
    "default_enable_checks" BOOL NOT NULL,
    CONSTRAINT "uid_repository_name_27b9e3" UNIQUE ("name", "owner")
);
CREATE TABLE IF NOT EXISTS "external_account_right" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "account_id" VARCHAR(255) NOT NULL REFERENCES "external_account" ("username") ON DELETE CASCADE,
    "repository_id" INT NOT NULL REFERENCES "repository" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_external_ac_account_6dc5f7" UNIQUE ("account_id", "repository_id")
);
CREATE TABLE IF NOT EXISTS "merge_rule" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "base_branch" VARCHAR(255) NOT NULL,
    "head_branch" VARCHAR(255) NOT NULL,
    "strategy" VARCHAR(255) NOT NULL,
    "repository_id" INT NOT NULL REFERENCES "repository" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_merge_rule_reposit_16b34c" UNIQUE ("repository_id", "base_branch", "head_branch")
);
CREATE TABLE IF NOT EXISTS "pull_request" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "number" INT NOT NULL,
    "qa_status" VARCHAR(255) NOT NULL,
    "status_comment_id" BIGINT NOT NULL,
    "checks_enabled" BOOL NOT NULL,
    "automerge" BOOL NOT NULL,
    "locked" BOOL NOT NULL,
    "strategy_override" VARCHAR(255),
    "repository_id" INT NOT NULL REFERENCES "repository" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_pull_reques_reposit_4cb284" UNIQUE ("repository_id", "number")
);
CREATE TABLE IF NOT EXISTS "repository_rule" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "conditions" TEXT NOT NULL,
    "actions" TEXT NOT NULL,
    "repository_id" INT NOT NULL REFERENCES "repository" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_repository__reposit_06635d" UNIQUE ("repository_id", "name")
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
