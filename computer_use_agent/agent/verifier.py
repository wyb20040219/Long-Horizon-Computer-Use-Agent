from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from ..core.models import Action, ActionResult, Observation, Verification, VerificationResult


def _navigation_identity(url: str) -> tuple[str, str, int | None, str, str] | None:
    """Return the security-relevant identity of an HTTP(S) navigation URL."""
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or not parsed.hostname:
            return None
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        port = parsed.port
        if (scheme, port) in {("http", 80), ("https", 443)}:
            port = None
        path = parsed.path or "/"
        return scheme, host, port, path, parsed.query
    except (UnicodeError, ValueError):
        return None


def urls_semantically_equal(expected: str, actual: str) -> bool:
    """Compare navigation targets while allowing only a safe HTTP→HTTPS upgrade."""
    expected_identity = _navigation_identity(expected)
    actual_identity = _navigation_identity(actual)
    if expected_identity is None or actual_identity is None:
        return False
    expected_scheme, *expected_target = expected_identity
    actual_scheme, *actual_target = actual_identity
    scheme_matches = expected_scheme == actual_scheme or (expected_scheme == "http" and actual_scheme == "https")
    return scheme_matches and expected_target == actual_target


class Verifier:
    def verify_action(self, action: Action, result: ActionResult, observation: Observation) -> Verification:
        if not result.success:
            return Verification(VerificationResult.FAIL, result.error or result.message, [result.message])
        evidence = [result.message]
        if action.name == "open_url":
            expected = str(action.arguments.get("url", ""))
            if not observation.url or not urls_semantically_equal(expected, observation.url):
                return Verification(VerificationResult.UNCERTAIN, "Browser URL differs after navigation", [str(observation.url)])
            evidence.append(f"url={observation.url}")
        elif action.name == "write_file":
            path = result.data.get("path")
            if not path or not Path(str(path)).exists():
                return Verification(VerificationResult.FAIL, "Output file does not exist", evidence)
            evidence.append(f"file={path}")
        return Verification(VerificationResult.PASS, "Postcondition confirmed", evidence)

    def verify_subtask(self, action_check: Verification) -> Verification:
        return action_check

    def verify_goal(self, completed: int, total: int) -> Verification:
        if total > 0 and completed == total:
            return Verification(VerificationResult.PASS, "Every planned subtask has verified evidence", [f"completed={completed}/{total}"])
        return Verification(VerificationResult.FAIL, "Not all subtasks completed", [f"completed={completed}/{total}"])
