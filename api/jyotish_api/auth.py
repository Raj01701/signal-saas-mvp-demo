"""Supabase access tokens: verified locally, never sent anywhere.

Set ``JYOTISH_API_SUPABASE_JWT_SECRET`` (projects signing with HS256) or
``JYOTISH_API_SUPABASE_JWKS_URL`` (asymmetric signing keys). The token's ``sub`` is the
user id; the first request from a user creates their account row.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from jyotish_api.config import ApiSettings
from jyotish_api.db import User, sessions

bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def verify_token(token: str, settings: ApiSettings) -> dict[str, Any]:
    options: jwt.types.Options = {"require": ["sub", "exp"]}
    try:
        if settings.supabase_jwt_secret:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=settings.supabase_audience,
                options=options,
            )
        if settings.supabase_jwks_url:
            key = _jwks_client(settings.supabase_jwks_url).get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                key.key,
                algorithms=["RS256", "ES256"],
                audience=settings.supabase_audience,
                options=options,
            )
    except jwt.PyJWTError as error:
        raise HTTPException(status_code=401, detail=f"invalid token: {error}") from error
    raise HTTPException(status_code=503, detail="authentication is not configured")


def get_session(request: Request) -> Any:
    yield from sessions(request.app.state.sessions)


SessionDep = Annotated[Session, Depends(get_session)]


def current_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="sign in required")
    claims = verify_token(credentials.credentials, request.app.state.settings)
    user = session.get(User, claims["sub"])
    if user is None:
        user = User(id=claims["sub"], email=claims.get("email"))
        session.add(user)
        session.flush()
    return user


CurrentUser = Annotated[User, Depends(current_user)]
