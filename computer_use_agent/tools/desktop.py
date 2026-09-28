from __future__ import annotations

from pathlib import Path

from ..core.models import ActionResult, Observation
from .base import Observable


class DesktopController(Observable):
    def __init__(self, screenshots_dir: Path, enabled: bool = False):
        self.screenshots_dir = screenshots_dir
        self.enabled = enabled

    def _backend(self):
        if not self.enabled:
            raise RuntimeError("Desktop control is disabled; explicitly enable it after reviewing safety settings")
        try:
            import pyautogui
            pyautogui.PAUSE = 0.1
            pyautogui.FAILSAFE = True
            return pyautogui
        except ImportError as exc:
            raise RuntimeError("Install optional dependency: pip install pyautogui") from exc

    def execute(self, action: str, **args: object) -> ActionResult:
        try:
            gui = self._backend()
            if action == "mouse_click": gui.click(int(args["x"]), int(args["y"]))
            elif action == "keyboard_input": gui.write(str(args["text"]), interval=0.02)
            elif action == "hotkey": gui.hotkey(*list(args["keys"]))
            elif action == "screenshot":
                self.screenshots_dir.mkdir(parents=True, exist_ok=True)
                path = self.screenshots_dir / str(args.get("name", "desktop.png")); gui.screenshot(str(path))
                return ActionResult(True, "Desktop screenshot captured", {"path": str(path)})
            else: return ActionResult(False, "Unknown desktop action", error=action)
            return ActionResult(True, f"Desktop action completed: {action}")
        except Exception as exc:
            return ActionResult(False, f"Desktop action failed: {action}", error=str(exc))

    def observe(self) -> Observation:
        return Observation(active_app="desktop", metadata={"enabled": self.enabled})
