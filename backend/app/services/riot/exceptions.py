"""Riot API specific exceptions."""

from __future__ import annotations


class RiotError(Exception):
    """Base class for Riot API errors."""


class RiotRateLimited(RiotError):
    """429 received; backoff requested."""

    def __init__(self, retry_after: float):
        super().__init__(f"rate limited, retry after {retry_after}s")
        self.retry_after = retry_after


class RiotForbidden(RiotError):
    """403 — API key invalid or endpoint blocked (e.g. Mayhem matches)."""


class RiotNotFound(RiotError):
    """404 — resource not found."""


class RiotServerError(RiotError):
    """5xx — Riot upstream issue."""


class RiotKeyExhausted(RiotError):
    """All configured API keys are currently rate-limited."""
