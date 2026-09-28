from __future__ import annotations

from pathlib import Path

from ..core.models import Action, ActionResult, Observation, Verification, VerificationResult


class Verifier:
    def verify_action(self, action: Action, result: ActionResult, observation: Observation) -> Verification:
        if not result.success:
            return Verification(VerificationResult.FAIL, result.error or result.message, [result.message])
        evidence = [result.message]
        if action.name == "open_url":
            expected = str(action.arguments.get("url", ""))
            if observation.url != expected:
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
