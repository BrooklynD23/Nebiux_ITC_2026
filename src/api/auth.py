"""Shared admin authorization helpers for privileged API routes."""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from src.settings import get_settings


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def _configured_admin_token() -> str | None:
    configured = (get_settings().admin_api_token or "").strip()
    return configured or None


def get_optional_admin_auth(authorization: str | None = Header(default=None)) -> bool:
    """Return whether the incoming request carries the configured admin token."""
    expected = _configured_admin_token()
    provided = _extract_bearer_token(authorization)
    if expected is None or provided is None:
        return False
    return secrets.compare_digest(provided, expected)


def require_admin_auth(authorization: str | None = Header(default=None)) -> bool:
    """Require a valid admin bearer token for a privileged route."""
    if get_optional_admin_auth(authorization):
        return True
    raise HTTPException(
        status_code=401,
        detail="Admin authorization required.",
    )
