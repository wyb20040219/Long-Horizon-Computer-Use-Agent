from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urlparse

from ..core.models import ActionResult, Observation
from .base import Observable


class BrowserController(Observable):
    """Playwright adapter with a zero-dependency deterministic mock mode."""

    def __init__(self, allowed_domains: tuple[str, ...], screenshots_dir: Path, mock: bool = False, headless: bool = True):
        self.allowed_domains = allowed_domains
        self.screenshots_dir = screenshots_dir
        self.mock = mock
        self.headless = headless
        self._playwright = self._browser = self._page = None
        self._mock_url = "about:blank"
        self._mock_title = ""
        self._mock_text = ""

    def _allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        return any(host == domain or host.endswith("." + domain) for domain in self.allowed_domains)

    def start(self) -> None:
        if self.mock or self._page is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is optional. Install with: pip install playwright && playwright install chromium") from exc
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()

    def execute(self, action: str, **args: object) -> ActionResult:
        try:
            if action == "open_url":
                url = str(args["url"])
                if not self._allowed(url):
                    return ActionResult(False, "Domain blocked by policy", error=f"Domain not allowed: {urlparse(url).hostname}")
                if self.mock:
                    self._mock_url = url
                    self._mock_title = "Example Domain" if "example.com" in url else "Mock Page"
                    self._mock_text = "Example Domain This domain is for use in illustrative examples."
                else:
                    self.start(); self._page.goto(url, wait_until="domcontentloaded")
            elif action == "click":
                if not self.mock: self.start(); self._page.locator(str(args["selector"])).click()
            elif action == "type":
                if not self.mock: self.start(); self._page.locator(str(args["selector"])).fill(str(args["text"]))
            elif action == "scroll":
                if not self.mock: self.start(); self._page.mouse.wheel(0, int(args.get("delta", 600)))
            elif action == "back":
                if not self.mock: self.start(); self._page.go_back()
            elif action == "refresh":
                if not self.mock: self.start(); self._page.reload()
            elif action == "wait":
                seconds = min(float(args.get("seconds", 1)), 10.0)
                if self.mock: time.sleep(min(seconds, 0.01))
                else: self.start(); self._page.wait_for_timeout(seconds * 1000)
            elif action == "assert_text":
                expected = str(args["text"])
                actual = self.observe().page_text
                if expected not in actual:
                    return ActionResult(False, "Expected text was not found", {"expected": expected}, "text mismatch")
            else:
                return ActionResult(False, "Unknown browser action", error=action)
            return ActionResult(True, f"Browser action completed: {action}", {"url": self.observe().url})
        except Exception as exc:
            return ActionResult(False, f"Browser action failed: {action}", error=str(exc))

    def observe(self) -> Observation:
        if self.mock:
            return Observation(url=self._mock_url, title=self._mock_title, page_text=self._mock_text, active_app="mock-browser")
        self.start()
        return Observation(url=self._page.url, title=self._page.title(), page_text=self._page.locator("body").inner_text()[:20000], active_app="browser")

    def screenshot(self, name: str) -> ActionResult:
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        path = self.screenshots_dir / name
        if self.mock:
            path.write_bytes(b"")
        else:
            self.start(); self._page.screenshot(path=str(path), full_page=False)
        return ActionResult(True, "Screenshot captured", {"path": str(path)})

    def close(self) -> None:
        if self._browser: self._browser.close()
        if self._playwright: self._playwright.stop()
