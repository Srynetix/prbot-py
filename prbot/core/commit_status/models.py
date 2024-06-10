from pydantic import BaseModel

from prbot.modules.github.models import (
    GhCommitStatusState,
)


class StatusMessage(BaseModel):
    state: GhCommitStatusState
    title: str
    message: str
