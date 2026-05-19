"""Async HTTP client for the Riot Games API.

Handles:
  - Key rotation (multiple keys for higher aggregate throughput).
  - Rate limiting via RiotRateLimiter (shared per region).
  - Retry on 429 / 5xx with tenacity.
  - Region cluster routing (match-v5 lives at americas/asia/europe/sea;
    summoner-v4 / league-v4 live at platform host).
"""

from __future__ import annotations

import itertools
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger
from app.services.riot.exceptions import (
    RiotError,
    RiotForbidden,
    RiotKeyExhausted,
    RiotNotFound,
    RiotRateLimited,
    RiotServerError,
)
from app.services.riot.rate_limiter import RiotRateLimiter
from app.settings import get_settings

log = get_logger(__name__)


# Platform -> regional cluster routing
PLATFORM_TO_CLUSTER: dict[str, str] = {
    "NA1": "americas", "BR1": "americas", "LA1": "americas", "LA2": "americas",
    "KR": "asia", "JP1": "asia",
    "EUW1": "europe", "EUN1": "europe", "TR1": "europe", "RU": "europe",
    "OC1": "sea", "SG2": "sea", "TH2": "sea", "TW2": "sea", "VN2": "sea", "PH2": "sea",
}


def platform_to_cluster(platform: str) -> str:
    return PLATFORM_TO_CLUSTER.get(platform.upper(), "asia")


class RiotClient:
    """Singleton-ish client. Construct once at app startup."""

    def __init__(
        self,
        api_keys: list[str],
        rate_limiter: RiotRateLimiter | None = None,
        timeout: float = 10.0,
    ) -> None:
        if not api_keys:
            raise ValueError("at least one Riot API key is required")
        self._keys = list(api_keys)
        self._key_cycle = itertools.cycle(self._keys)
        self._rate_limiter = rate_limiter or RiotRateLimiter()
        self._http = httpx.AsyncClient(
            timeout=timeout,
            http2=True,
            headers={"User-Agent": "lolhelper/0.1"},
        )

    async def close(self) -> None:
        await self._http.aclose()

    # --- Low-level GET --------------------------------------------------------

    async def _get(
        self,
        host: str,  # e.g. "asia.api.riotgames.com" or "kr.api.riotgames.com"
        path: str,
        *,
        region_key: str,  # for rate-limiter bucketing
        method_id: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        await self._rate_limiter.acquire(region_key, method_id)
        api_key = next(self._key_cycle)
        url = f"https://{host}{path}"
        try:
            resp = await self._http.get(
                url,
                params=params,
                headers={"X-Riot-Token": api_key},
            )
        except httpx.HTTPError as e:
            raise RiotError(f"transport error: {e}") from e

        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            raise RiotNotFound(f"{url} {params}")
        if resp.status_code == 403:
            raise RiotForbidden(f"{url} forbidden (key invalid or endpoint blocked)")
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", "1"))
            log.warning("riot.rate_limited", url=url, retry_after=retry_after)
            raise RiotRateLimited(retry_after)
        if 500 <= resp.status_code < 600:
            raise RiotServerError(f"{resp.status_code} {url}")
        raise RiotError(f"unexpected {resp.status_code} {url}: {resp.text[:200]}")

    async def get(
        self,
        host: str,
        path: str,
        *,
        region_key: str,
        method_id: str | None = None,
        params: dict[str, Any] | None = None,
        max_attempts: int = 5,
    ) -> Any:
        """GET with exponential backoff retry on 429 / 5xx."""
        attempts = AsyncRetrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=30.0),
            retry=retry_if_exception_type((RiotRateLimited, RiotServerError)),
            reraise=True,
        )
        async for attempt in attempts:
            with attempt:
                return await self._get(
                    host, path, region_key=region_key, method_id=method_id, params=params
                )
        # Should be unreachable; tenacity reraises on exhaustion
        raise RiotKeyExhausted("retries exhausted")

    # --- High-level endpoints -------------------------------------------------

    async def get_match(self, match_id: str, *, cluster: str) -> dict[str, Any]:
        """match-v5 detail. `cluster` = americas/asia/europe/sea."""
        host = f"{cluster}.api.riotgames.com"
        return await self.get(
            host,
            f"/lol/match/v5/matches/{match_id}",
            region_key=cluster,
            method_id="match-v5-detail",
        )

    async def get_match_ids_by_puuid(
        self,
        puuid: str,
        *,
        cluster: str,
        queue: int | None = None,
        start: int = 0,
        count: int = 20,
        start_time: int | None = None,
    ) -> list[str]:
        """Match-V5 ids by puuid. `start_time` is Unix epoch seconds (inclusive)."""
        host = f"{cluster}.api.riotgames.com"
        params: dict[str, Any] = {"start": start, "count": count}
        if queue is not None:
            params["queue"] = queue
        if start_time is not None:
            params["startTime"] = start_time
        return await self.get(
            host,
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
            region_key=cluster,
            method_id="match-v5-ids",
            params=params,
        )

    async def get_summoner_by_puuid(self, puuid: str, *, platform: str) -> dict[str, Any]:
        host = f"{platform.lower()}.api.riotgames.com"
        return await self.get(
            host,
            f"/lol/summoner/v4/summoners/by-puuid/{puuid}",
            region_key=platform.upper(),
            method_id="summoner-v4-puuid",
        )

    async def get_account_by_riot_id(
        self, game_name: str, tag_line: str, *, cluster: str
    ) -> dict[str, Any]:
        host = f"{cluster}.api.riotgames.com"
        return await self.get(
            host,
            f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}",
            region_key=cluster,
            method_id="account-v1",
        )

    async def get_challenger_league(
        self, *, platform: str, queue: str = "RANKED_SOLO_5x5"
    ) -> dict[str, Any]:
        host = f"{platform.lower()}.api.riotgames.com"
        return await self.get(
            host,
            f"/lol/league/v4/challengerleagues/by-queue/{queue}",
            region_key=platform.upper(),
            method_id="league-v4-challenger",
        )

    async def get_grandmaster_league(
        self, *, platform: str, queue: str = "RANKED_SOLO_5x5"
    ) -> dict[str, Any]:
        host = f"{platform.lower()}.api.riotgames.com"
        return await self.get(
            host,
            f"/lol/league/v4/grandmasterleagues/by-queue/{queue}",
            region_key=platform.upper(),
            method_id="league-v4-grandmaster",
        )

    async def get_master_league(
        self, *, platform: str, queue: str = "RANKED_SOLO_5x5"
    ) -> dict[str, Any]:
        host = f"{platform.lower()}.api.riotgames.com"
        return await self.get(
            host,
            f"/lol/league/v4/masterleagues/by-queue/{queue}",
            region_key=platform.upper(),
            method_id="league-v4-master",
        )


# --- Module-level accessor ----------------------------------------------------

_client: RiotClient | None = None


def get_riot_client() -> RiotClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = RiotClient(
            api_keys=settings.riot_api_keys,
            timeout=settings.riot_request_timeout_seconds,
        )
    return _client


async def close_riot_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
