from __future__ import annotations

import json
import os
from typing import Any, Protocol
from urllib.request import Request, urlopen


class LLMClient(Protocol):
    def complete_json(self, system: str, prompt: str) -> dict[str, Any] | list[Any]: ...


class OpenAICompatibleClient:
    """Small dependency-free OpenAI-compatible chat client."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured; use --dry-run for the deterministic mock")

    def complete_json(self, system: str, prompt: str) -> dict[str, Any] | list[Any]:
        body = json.dumps({"model": self.model, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}).encode()
        request = Request(f"{self.base_url}/chat/completions", data=body, method="POST", headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
        return json.loads(payload["choices"][0]["message"]["content"])


class MockLLMClient:
    def complete_json(self, system: str, prompt: str) -> dict[str, Any]:
        return {"mode": "mock", "summary": "Deterministic planning is active."}
