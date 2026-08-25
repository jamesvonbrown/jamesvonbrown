"""Shared API dependencies: auth and session."""

from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, Query, status
from sqlmodel import Session

from ..config import Settings, get_settings
from ..db import effective_settings, get_session


def get_db() -> Session:
    yield from get_session()


def settings_dep(session: Session = Depends(get_db)) -> Settings:
    """Config with the phone-editable overrides applied."""
    return effective_settings(session)


async def require_token(
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None, include_in_schema=False),
) -> str:
    """Single shared bearer token.

    A query-parameter fallback exists so the phone can be onboarded from one
    tapped link, which then stores the token locally. That's a deliberate
    trade: query strings can end up in proxy logs, so the link is a bootstrap
    convenience and the header is what the app uses from then on.
    """
    configured = get_settings().api_token
    if not configured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Server has no API token set. Run `flipscan init`.",
        )

    supplied = None
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    elif token:
        supplied = token.strip()

    # Constant-time compare: a plain `==` on a secret leaks its prefix through
    # timing, and this endpoint is reachable from the internet.
    if not supplied or not secrets.compare_digest(supplied, configured):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return supplied
