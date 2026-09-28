from __future__ import annotations

from pathlib import Path

from ..core.models import ActionResult


class FileSystemController:
    def __init__(self, workspace: Path, protected_paths: tuple[str, ...]):
        self.workspace = workspace.resolve()
        self.protected = tuple(Path(p).resolve() for p in protected_paths)

    def resolve(self, raw_path: str) -> Path:
        candidate = (self.workspace / raw_path).resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise PermissionError("Path escapes workspace")
        # Ancestor protections (for example the user's home) must not make an
        # explicitly selected workspace unusable. Only protected entries that
        # are themselves inside the workspace can further restrict it.
        protected_inside_workspace = (item for item in self.protected if item == self.workspace or self.workspace in item.parents)
        if any(candidate == item or item in candidate.parents for item in protected_inside_workspace):
            raise PermissionError("Path is protected")
        return candidate

    def read_file(self, path: str) -> ActionResult:
        try:
            target = self.resolve(path)
            return ActionResult(True, "File read", {"path": str(target), "content": target.read_text(encoding="utf-8")})
        except Exception as exc:
            return ActionResult(False, "File read failed", error=str(exc))

    def write_file(self, path: str, content: str, overwrite: bool = False) -> ActionResult:
        try:
            target = self.resolve(path)
            if target.exists() and not overwrite:
                if target.read_text(encoding="utf-8") == content:
                    return ActionResult(True, "File already contains requested content", {"path": str(target), "bytes": len(content.encode("utf-8")), "idempotent": True})
                return ActionResult(False, "Overwrite requires approval", {"approval_required": True}, "file exists")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ActionResult(True, "File written", {"path": str(target), "bytes": len(content.encode("utf-8"))})
        except Exception as exc:
            return ActionResult(False, "File write failed", error=str(exc))
