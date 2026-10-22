"""Small client for the market REST API: auth, retries, 429 back-off, readable errors."""
import time

import httpx


class MarketError(Exception):
    """An error the market returned: {"error": {code, message, field, hint, allowed}}."""

    def __init__(self, status: int, body: dict):
        err = body.get("error", {}) if isinstance(body, dict) else {}
        self.status = status
        self.code = err.get("code", f"HTTP_{status}")
        self.message = err.get("message", str(body))
        self.hint = err.get("hint")
        self.allowed = err.get("allowed")
        super().__init__(f"{self.code}: {self.message}" + (f" (hint: {self.hint})" if self.hint else ""))


class Market:
    def __init__(self, base_url: str, key: str, timeout: float = 10.0):
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout,
                                 headers={"Authorization": f"Bearer {key}", "User-Agent": "coffee-starter/1.0"})

    def call(self, method: str, path: str, json=None, params=None, tries: int = 4):
        for attempt in range(tries):
            try:
                r = self.http.request(method, path, json=json, params=params)
            except httpx.TransportError:            # server busy or network blip: wait and retry
                if attempt == tries - 1:
                    raise
                time.sleep(1 + attempt)
                continue
            if r.status_code == 429 or r.status_code >= 500:
                if attempt == tries - 1:
                    break
                time.sleep(float(r.headers.get("Retry-After", 1 + attempt)))
                continue
            break
        body = r.json() if r.content else {}
        if r.status_code >= 400:
            raise MarketError(r.status_code, body)
        return body

    def state(self) -> dict:
        return self.call("GET", "/v1/state")

    def calendar(self) -> dict:
        return self.call("GET", "/v1/calendar")

    def appraise(self, items: list[dict]) -> dict:
        return self.call("POST", "/v1/appraisals", json={"items": items})

    def offer_batch(self, offers: list[dict], replace_existing: bool = True) -> dict:
        return self.call("POST", "/v1/offers:batch", json={"offers": offers, "replace_existing": replace_existing})

    def offer(self, o: dict) -> dict:
        return self.call("POST", "/v1/offers", json=o)
