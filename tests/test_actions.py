from computer_use_agent.core.models import Action
from computer_use_agent.tools.browser import BrowserController
from computer_use_agent.tools.desktop import DesktopController
from computer_use_agent.tools.filesystem import FileSystemController
from computer_use_agent.tools.registry import ActionRegistry


def registry(tmp_path):
    return ActionRegistry(BrowserController(("example.com",), tmp_path, mock=True), DesktopController(tmp_path), FileSystemController(tmp_path, ()))


def test_domain_allowlist_blocks_untrusted_host(tmp_path):
    result = registry(tmp_path).execute(Action("open_url", {"url": "https://evil.invalid"}), lambda _: True)
    assert not result.success and "blocked" in result.message.lower()


def test_files_cannot_escape_workspace(tmp_path):
    result = registry(tmp_path).execute(Action("write_file", {"path": "../escape.txt", "content": "x"}), lambda _: True)
    assert not result.success and "escapes workspace" in result.error


def test_protected_subpath_is_blocked(tmp_path):
    files = FileSystemController(tmp_path, (str(tmp_path / "secrets"),))
    result = files.write_file("secrets/key.txt", "nope")
    assert not result.success and "protected" in result.error


def test_dangerous_action_requires_approval(tmp_path):
    result = registry(tmp_path).execute(Action("mouse_click", {"x": 1, "y": 2}), lambda _: False)
    assert result.data["rejected"] is True


def test_idempotent_write_is_safe(tmp_path):
    action = Action("write_file", {"path": "same.txt", "content": "same"})
    assert registry(tmp_path).execute(action, lambda _: True).success
    again = registry(tmp_path).execute(action, lambda _: True)
    assert again.success and again.data["idempotent"]
