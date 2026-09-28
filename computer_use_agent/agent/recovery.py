from __future__ import annotations

from ..core.models import RecoveryDecision


class RecoveryPolicy:
    def __init__(self, max_retries: int):
        self.max_retries = max_retries

    def decide(self, retry_count: int, *, rejected: bool = False, timed_out: bool = False) -> RecoveryDecision:
        if rejected: return RecoveryDecision.ABORT
        if timed_out: return RecoveryDecision.RESTORE
        if retry_count < self.max_retries: return RecoveryDecision.RETRY
        if retry_count == self.max_retries: return RecoveryDecision.REPLAN
        return RecoveryDecision.ESCALATE
