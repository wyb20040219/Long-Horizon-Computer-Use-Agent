from __future__ import annotations

import json
import threading
from pathlib import Path

from .models import StepTrace


class TraceWriter:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, trace: StepTrace) -> None:
        line = json.dumps(trace.to_dict(), ensure_ascii=False)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
