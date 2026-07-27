"""Per-IP rate limiting.

The AI limit is hourly and separate from the analysis limit on purpose: the deterministic
analysis is free to run and should stay generous, while the Claude call costs real money.
A user who exhausts the AI budget still gets every measurement.
"""

from __future__ import annotations

import threading
import time

from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings

# headers_enabled stays off: slowapi injects its X-RateLimit-* headers by mutating a
# Response object, which requires every limited endpoint to either return a Response or
# declare a `response: Response` parameter. Our endpoints return plain dicts (and the
# download routes return their own Response), so the injection path would raise on every
# successful request. Retry-After is set explicitly by the 429 handler in main.py, which
# is the header that actually matters to a client.
limiter = Limiter(key_func=get_remote_address, headers_enabled=False)

THUMBNAILS_LIMIT = f"{settings.rate_limit_thumbnails_per_min}/minute"
ANALYZE_LIMIT = f"{settings.rate_limit_analyze_per_min}/minute"
BATCH_LIMIT = f"{settings.rate_limit_batch_per_hour}/hour"
DOWNLOAD_LIMIT = f"{settings.rate_limit_download_per_min}/minute"


class AiBudget:
    """Hourly per-IP allowance for the Claude call, tracked separately from HTTP limits.

    Exceeding it is not an error: the request proceeds without the AI pass and the
    response carries an ``aiError`` explaining why, exactly like an API outage.
    """

    def __init__(self, per_hour: int) -> None:
        self._per_hour = per_hour
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}

    def allow(self, client: str) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - 3600
        with self._lock:
            hits = [t for t in self._hits.get(client, []) if t > cutoff]
            if len(hits) >= self._per_hour:
                retry_in = int(hits[0] + 3600 - now) + 1
                self._hits[client] = hits
                return False, retry_in
            hits.append(now)
            self._hits[client] = hits

            # Opportunistic sweep so idle clients don't accumulate forever.
            if len(self._hits) > 4096:
                self._hits = {
                    key: [t for t in values if t > cutoff]
                    for key, values in self._hits.items()
                    if any(t > cutoff for t in values)
                }
            return True, 0

    def remaining(self, client: str) -> int:
        cutoff = time.time() - 3600
        with self._lock:
            hits = [t for t in self._hits.get(client, []) if t > cutoff]
        return max(0, self._per_hour - len(hits))


ai_budget = AiBudget(settings.rate_limit_ai_per_hour)
