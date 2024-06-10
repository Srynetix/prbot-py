from prbot.core.commit_status.builder import CommitStatusBuilder
from prbot.core.message import generate_message_footer
from prbot.core.models import CheckStatus, MergeStrategy, QaStatus, RepositoryRule
from prbot.core.sync.sync_state import PullRequestSyncState


class SummaryBuilder:
    def build(self, *, sync_state: PullRequestSyncState) -> str:
        return (
            f"_This is an auto-generated message summarizing this pull request._\n"
            f"\n"
            f"{self._generate_rules(sync_state=sync_state)}\n"
            f"\n"
            f"{self._generate_checks(sync_state=sync_state)}\n"
            f"\n"
            f"{self._generate_config(sync_state=sync_state)}\n"
            f"\n"
            f"{self._generate_footer(sync_state=sync_state)}\n"
            f"{generate_message_footer()}"
        )

    def _generate_rules(self, sync_state: PullRequestSyncState) -> str:
        return (
            f":pencil: &mdash; **Rules**\n"
            f"\n"
            f"{self._generate_rules_valid_title_message(valid_pr_title=sync_state.valid_pr_title)}\n"
            f"{self._generate_rules_title_regex_message(title_regex=sync_state.title_regex)}\n"
            f"{self._generate_rules_merge_strategy_message(strategy=sync_state.merge_strategy)}\n"
            f"{self._generate_rules_rule_list_message(rules=sync_state.rules)}"
        )

    def _generate_rules_valid_title_message(self, *, valid_pr_title: bool) -> str:
        title_is_valid = (
            "_valid!_ :heavy_check_mark:" if valid_pr_title else "_invalid!_ :x:"
        )

        return f"> - :speech_balloon: **Title validation**: {title_is_valid}"

    def _generate_rules_title_regex_message(self, *, title_regex: str) -> str:
        validation_rgx = title_regex if title_regex != "" else "None"

        return f">   - _Rule_: {validation_rgx}"

    def _generate_rules_rule_list_message(self, *, rules: list[RepositoryRule]) -> str:
        rule_text = ", ".join(rule.name for rule in rules) if len(rules) > 0 else "None"

        return f"> - :straight_ruler: **Pull request rules**: _{rule_text}_"

    def _generate_rules_merge_strategy_message(self, *, strategy: MergeStrategy) -> str:
        strategy_name = strategy.value.capitalize()
        return f"> - :twisted_rightwards_arrows: **Merge strategy**: _{strategy_name}_"

    def _generate_checks(self, *, sync_state: PullRequestSyncState) -> str:
        return (
            f":speech_balloon: &mdash; **Status comment**\n"
            f"\n"
            f"{self._generate_checks_wip_message(wip=sync_state.wip)}\n"
            f"{self._generate_checks_check_message(check_status=sync_state.check_status)}\n"
            f"{self._generate_checks_review_message(sync_state=sync_state)}\n"
            f"{self._generate_checks_qa_message(qa_status=sync_state.qa_status)}\n"
            f"{self._generate_checks_lock_message(locked=sync_state.locked)}\n"
            f"{self._generate_checks_mergeable_message(sync_state=sync_state)}"
        )

    def _generate_checks_wip_message(self, *, wip: bool) -> str:
        wip_message = ""
        if wip:
            wip_message = "Yes :x:"
        else:
            wip_message = "No :heavy_check_mark:"

        return f"> - :construction: **WIP?**: {wip_message}"

    def _generate_checks_check_message(self, *, check_status: CheckStatus) -> str:
        check_message = ""
        if check_status == CheckStatus.Pass:
            check_message = "_passed_! :heavy_check_mark:"
        elif check_status == CheckStatus.Waiting:
            check_message = "_waiting_... :clock2:"
        elif check_status == CheckStatus.Fail:
            check_message = "_failed_. :x:"
        else:
            check_message = "_skipped_. :heavy_check_mark:"

        return f"> - :checkered_flag: **Checks**: {check_message}"

    def _generate_checks_review_message(
        self, *, sync_state: PullRequestSyncState
    ) -> str:
        code_review_message = ""
        if sync_state.changes_requested:
            code_review_message = "_waiting on change requests..._ :x:"
        elif sync_state.review_required:
            code_review_message = "_waiting..._ :clock2:"
        elif sync_state.review_skipped:
            code_review_message = "_skipped._ :heavy_check_mark:"
        else:
            code_review_message = "_passed!_ :heavy_check_mark:"

        return f"> - :mag: **Code reviews**: {code_review_message}"

    def _generate_checks_qa_message(self, *, qa_status: QaStatus) -> str:
        qa_message = ""
        if qa_status == QaStatus.Pass:
            qa_message = "_passed_! :heavy_check_mark:"
        elif qa_status == QaStatus.Waiting:
            qa_message = "_waiting_... :clock2:"
        elif qa_status == QaStatus.Fail:
            qa_message = "_failed_. :x:"
        else:
            qa_message = "_skipped_. :heavy_check_mark:"

        return f"> - :test_tube: **QA**: {qa_message}"

    def _generate_checks_lock_message(self, *, locked: bool) -> str:
        lock_message = ""
        if locked:
            lock_message = "Yes :x:"
        else:
            lock_message = "No :heavy_check_mark:"

        return f"> - :lock: **Locked?**: {lock_message}"

    def _generate_checks_mergeable_message(
        self, *, sync_state: PullRequestSyncState
    ) -> str:
        mergeable_message = ""
        if sync_state.mergeable or sync_state.merged:
            mergeable_message = "Yes :heavy_check_mark:"
        else:
            mergeable_message = "No :x:"

        return f"> - :twisted_rightwards_arrows: **Mergeable?**: {mergeable_message}"

    def _generate_config(self, *, sync_state: PullRequestSyncState) -> str:
        return (
            f":gear: &mdash; **Configuration**\n"
            f"\n"
            f"{self._generate_config_automerge_message(automerge=sync_state.automerge)}"
        )

    def _generate_config_automerge_message(self, *, automerge: bool) -> str:
        automerge_message = ""
        if automerge:
            automerge_message = "Yes :heavy_check_mark:"
        else:
            automerge_message = "No :x:"

        return f"> - :twisted_rightwards_arrows: **Automerge**: {automerge_message}"

    def _generate_footer(self, *, sync_state: PullRequestSyncState) -> str:
        status_message = CommitStatusBuilder().build(sync_state=sync_state)

        return (
            ":scroll: &mdash; **Current status**\n"
            "\n"
            "> {status_state}: {status_message}\n"
            "\n"
            "[_See checks output by clicking this link :triangular_flag_on_post:_]({check_url})".format(
                status_state=status_message.state.name,
                status_message=status_message.message,
                check_url=sync_state.check_url,
            )
        )
