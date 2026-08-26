"""Verify Clerk session JWTs and load the Clerk user profile."""

from __future__ import annotations

from dataclasses import dataclass

import jwt
import requests
from django.conf import settings
from jwt import PyJWKClient

_jwks_client: PyJWKClient | None = None


class ClerkAuthError(Exception):
    """The Clerk session token is missing, invalid, or the user cannot be resolved."""


@dataclass(frozen=True)
class ClerkProfile:
    clerk_user_id: str
    email: str
    first_name: str
    last_name: str
    phone_number: str


def _jwks_client_for_settings() -> PyJWKClient:
    global _jwks_client
    jwks_url = getattr(settings, "CLERK_JWKS_URL", "") or ""
    if not jwks_url:
        raise ClerkAuthError("Clerk is not configured")
    if _jwks_client is None or _jwks_client.uri != jwks_url:
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def verify_clerk_session_token(token: str) -> dict:
    """Decode and verify a Clerk session JWT. Raises ClerkAuthError on failure."""
    if not token or not token.strip():
        raise ClerkAuthError("Missing Clerk session token")

    try:
        client = _jwks_client_for_settings()
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
            leeway=10,
        )
    except ClerkAuthError:
        raise
    except Exception as exc:
        raise ClerkAuthError("Invalid Clerk session token") from exc

    parties = getattr(settings, "CLERK_AUTHORIZED_PARTIES", None) or []
    azp = claims.get("azp")
    if parties and azp and azp not in parties:
        raise ClerkAuthError("Invalid Clerk authorized party")

    if not claims.get("sub"):
        raise ClerkAuthError("Clerk token is missing subject")
    return claims


def fetch_clerk_user(clerk_user_id: str) -> ClerkProfile:
    secret = getattr(settings, "CLERK_SECRET_KEY", "") or ""
    if not secret:
        raise ClerkAuthError("Clerk is not configured")

    response = requests.get(
        f"https://api.clerk.com/v1/users/{clerk_user_id}",
        headers={"Authorization": f"Bearer {secret}"},
        timeout=10,
    )
    if response.status_code != 200:
        raise ClerkAuthError("Could not load Clerk user")

    data = response.json()
    primary_id = data.get("primary_email_address_id")
    emails = data.get("email_addresses") or []
    email = ""
    for item in emails:
        if item.get("id") == primary_id or not email:
            email = (item.get("email_address") or "").strip()
            if item.get("id") == primary_id:
                break
    if not email:
        raise ClerkAuthError("Clerk user has no email")

    phones = data.get("phone_numbers") or []
    phone = ""
    if phones:
        phone = (phones[0].get("phone_number") or "").strip()

    return ClerkProfile(
        clerk_user_id=clerk_user_id,
        email=email,
        first_name=(data.get("first_name") or "").strip(),
        last_name=(data.get("last_name") or "").strip(),
        phone_number=phone,
    )
