"""Authentication: verify a bearer JWT and map it to a local user.

- dev mode: HS256 tokens signed with DEV_JWT_SECRET (see /api/v1/dev/token).
- oidc mode: tokens from any OIDC issuer, verified against its JWKS. This is how
  Supabase Auth (hosted) and a bank's own SSO (self-hosted: Azure AD, Okta) plug in.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from fastapi import HTTPException, status

from app.config import get_settings

DEV_ISSUER = "riskwise-dev"


@dataclass(frozen=True)
class Identity:
    issuer: str
    subject: str
    email: str
    name: str


def _unauthorized(detail: str = "Invalid or missing credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def mint_dev_token(subject: str, email: str, name: str = "", hours: int = 12) -> str:
    settings = get_settings()
    if settings.auth_mode != "dev" or settings.env == "prod":
        raise RuntimeError("Dev tokens are disabled")
    now = datetime.now(UTC)
    payload = {
        "iss": DEV_ISSUER,
        "sub": subject,
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + timedelta(hours=hours),
    }
    return jwt.encode(payload, settings.dev_jwt_secret, algorithm="HS256")


def verify_token(token: str) -> Identity:
    settings = get_settings()
    try:
        if settings.auth_mode == "dev":
            if settings.env == "prod":
                raise _unauthorized("Dev auth is not allowed in production")
            claims = jwt.decode(
                token,
                settings.dev_jwt_secret,
                algorithms=["HS256"],
                issuer=DEV_ISSUER,
                options={"require": ["exp", "sub", "iss"]},
            )
        else:
            if not settings.oidc_jwks_url or not settings.oidc_issuer:
                raise _unauthorized("OIDC is not configured")
            signing_key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                issuer=settings.oidc_issuer,
                audience=settings.oidc_audience or None,
                options={
                    "require": ["exp", "sub", "iss"],
                    "verify_aud": bool(settings.oidc_audience),
                },
            )
    except jwt.PyJWTError as exc:
        raise _unauthorized() from exc

    return Identity(
        issuer=str(claims["iss"]),
        subject=str(claims["sub"]),
        email=str(claims.get("email") or claims.get("preferred_username") or ""),
        name=str(claims.get("name") or ""),
    )
