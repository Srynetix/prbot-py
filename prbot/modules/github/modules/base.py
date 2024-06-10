from prbot.modules.github.core import GitHubCore


class GitHubModule:
    _core: GitHubCore

    def __init__(self, core: GitHubCore):
        self._core = core
