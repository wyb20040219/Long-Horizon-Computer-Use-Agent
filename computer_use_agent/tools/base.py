from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.models import ActionResult, Observation


class Tool(ABC):
    @abstractmethod
    def execute(self, **arguments: object) -> ActionResult: ...


class Observable(ABC):
    @abstractmethod
    def observe(self) -> Observation: ...
