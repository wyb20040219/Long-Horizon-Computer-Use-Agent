from computer_use_agent.agent.verifier import Verifier
from computer_use_agent.core.models import Action, ActionResult, Observation, VerificationResult


def test_navigation_requires_matching_observation():
    check = Verifier().verify_action(Action("open_url", {"url": "https://example.com"}), ActionResult(True, "ok"), Observation(url="https://other.test"))
    assert check.result == VerificationResult.UNCERTAIN


def test_failed_action_never_passes():
    check = Verifier().verify_action(Action("click"), ActionResult(False, "bad", error="missing"), Observation())
    assert check.result == VerificationResult.FAIL


def test_final_goal_needs_all_subtasks():
    assert Verifier().verify_goal(2, 2).result == VerificationResult.PASS
    assert Verifier().verify_goal(1, 2).result == VerificationResult.FAIL
