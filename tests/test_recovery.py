from computer_use_agent.agent.recovery import RecoveryPolicy
from computer_use_agent.core.models import RecoveryDecision


def test_recovery_is_bounded():
    policy = RecoveryPolicy(max_retries=2)
    assert policy.decide(0) == RecoveryDecision.RETRY
    assert policy.decide(2) == RecoveryDecision.REPLAN
    assert policy.decide(3) == RecoveryDecision.ESCALATE


def test_rejection_aborts_and_timeout_restores():
    policy = RecoveryPolicy(2)
    assert policy.decide(0, rejected=True) == RecoveryDecision.ABORT
    assert policy.decide(0, timed_out=True) == RecoveryDecision.RESTORE
