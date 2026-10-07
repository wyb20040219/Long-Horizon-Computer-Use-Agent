import pytest

from computer_use_agent.agent.verifier import Verifier, urls_semantically_equal
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


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ("https://example.com", "https://example.com/"),
        ("https://EXAMPLE.com/path", "https://example.COM/path"),
        ("https://example.com:443/path", "https://example.com/path"),
        ("http://example.com:80/path", "http://example.com/path"),
        ("http://example.com/path", "https://example.com/path"),
    ],
)
def test_navigation_url_normalization(expected, actual):
    assert urls_semantically_equal(expected, actual)


@pytest.mark.parametrize(
    ("expected", "actual"),
    [
        ("https://example.com/path", "http://example.com/path"),
        ("https://example.com/path", "https://example.com/other"),
        ("https://example.com/path?a=1", "https://example.com/path?a=2"),
        ("https://example.com", "https://example.org/"),
    ],
)
def test_navigation_url_comparison_rejects_different_targets(expected, actual):
    assert not urls_semantically_equal(expected, actual)


def test_verifier_accepts_browser_added_trailing_slash():
    check = Verifier().verify_action(
        Action("open_url", {"url": "https://example.com"}),
        ActionResult(True, "ok"),
        Observation(url="https://example.com/", title="Example Domain", page_text="body"),
    )
    assert check.result == VerificationResult.PASS


def test_navigation_rejects_lookalike_subdomain_attack():
    result = urls_semantically_equal(
        "https://example.com",
        "https://example.com.evil.test/",
    )

    assert not result
