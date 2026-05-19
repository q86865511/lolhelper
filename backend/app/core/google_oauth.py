"""Google OAuth 2.0 (OIDC) authorization-code helpers.

Minimal manual flow:
  1. Build the authorize URL with state + nonce (no library, just URL params).
  2. After Google redirects back with `code`, POST to Google's token endpoint
     to exchange the code for an access token + ID token.
  3. Decode the ID token (signed by Google) to extract sub / email / name.

We use `httpx` directly to avoid pulling in heavy OAuth client libraries.
For MVP we trust Google's ID token after decoding (it travels over TLS from
google.com directly); a hardened version would verify the JWT signature
against Google's JWKs.
"""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.settings import Settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def build_authorize_url(settings: Settings, state: str, nonce: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def gen_state_nonce() -> tuple[str, str]:
    return secrets.token_urlsafe(24), secrets.token_urlsafe(24)


async def exchange_code(code: str, settings: Settings) -> dict[str, Any]:
    """Exchange authorization code for tokens. Returns the raw token response."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret.get_secret_value(),
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


def decode_id_token(id_token: str) -> dict[str, Any]:
    """Decode Google ID token without verifying signature.

    OK for MVP: the token came from a TLS-protected exchange with Google,
    so a MITM would need to break TLS. For hardened deploys, verify against
    https://www.googleapis.com/oauth2/v3/certs.
    """
    return jwt.decode(id_token, options={"verify_signature": False})


async def fetch_userinfo(access_token: str) -> dict[str, Any]:
    """Optional: hit /userinfo for the freshest profile. Not strictly needed
    when the ID token already has `email`, `name`, `picture`."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()
