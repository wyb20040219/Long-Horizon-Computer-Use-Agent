from __future__ import annotations

from collections.abc import Callable

from ..core.models import Action, ActionResult
from .browser import BrowserController
from .desktop import DesktopController
from .filesystem import FileSystemController


class ActionRegistry:
    BROWSER = {"open_url", "click", "type", "scroll", "back", "refresh", "wait", "assert_text"}
    DESKTOP = {"mouse_click", "keyboard_input", "hotkey", "screenshot"}
    FILE = {"read_file", "write_file"}
    DANGEROUS = {"mouse_click", "keyboard_input", "hotkey"}

    def __init__(self, browser: BrowserController, desktop: DesktopController, files: FileSystemController):
        self.browser, self.desktop, self.files = browser, desktop, files

    def execute(self, action: Action, approve: Callable[[Action], bool]) -> ActionResult:
        if action.requires_approval or action.name in self.DANGEROUS or (action.name == "write_file" and bool(action.arguments.get("overwrite"))):
            if not approve(action):
                return ActionResult(False, "Action rejected by human", {"rejected": True}, "approval rejected")
        if action.name in self.BROWSER:
            return self.browser.execute(action.name, **action.arguments)
        if action.name in self.DESKTOP:
            return self.desktop.execute(action.name, **action.arguments)
        if action.name == "read_file": return self.files.read_file(**action.arguments)
        if action.name == "write_file": return self.files.write_file(**action.arguments)
        return ActionResult(False, "Action is not registered", error=action.name)
