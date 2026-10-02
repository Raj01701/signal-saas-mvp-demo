"""Who a request comes from, for rate limiting, and the narrative quota.

The limit key is the client's address. Behind proxies, ``forwarded_hops`` says how
many of them append to ``X-Forwarded-For``: the entry that many places from the
right was written by the outermost trusted proxy, so a client cannot forge it
(whatever the client sends sits further left). With 0 the header is ignored and the
connecting address is used. Trusting the whole header instead would let any client
pick a new address, and a new rate-limit bucket, with every request.
"""

from __future__ import annotations

import ipaddress

from fastapi import HTTPException, Request
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter


def client_address(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    hops: int = request.app.state.settings.forwarded_hops
    if hops <= 0:
        return peer
    header = ",".join(request.headers.getlist("x-forwarded-for"))
    entries = [entry.strip() for entry in header.split(",") if entry.strip()]
    if len(entries) < hops:
        return peer
    try:
        return str(ipaddress.ip_address(entries[-hops]))
    except ValueError:
        return peer


class NarrativeQuota:
    """A stricter per-client limit for the narrative routes, which may call a paid model."""

    def __init__(self, limit: str) -> None:
        self.text = limit
        self.limit = parse(limit)
        self.limiter = MovingWindowRateLimiter(MemoryStorage())

    def check(self, request: Request) -> None:
        if not self.limiter.hit(self.limit, "narrative", client_address(request)):
            raise HTTPException(429, f"narrative limit of {self.text} reached; try again later")


def narrative_quota(request: Request) -> None:
    """Route dependency: raise 429 once the client has used its narrative quota."""
    quota: NarrativeQuota = request.app.state.narrative_quota
    quota.check(request)
