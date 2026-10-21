import base64
import hashlib
import hmac
import secrets
import re

COOKIE_NAME = "__Host-ys_traveler"
COOKIE_MAX_AGE_S = 180 * 24 * 3600
_SUBJECT_PREFIX = "ya-sale-traveler:"


def _signature(token: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), token.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def new_cookie(secret: str) -> str:
    """A random anonymous id, signed so a visitor can only ever present one the server issued."""
    token = secrets.token_urlsafe(18)
    return f"{token}.{_signature(token, secret)}"


def subject_of(cookie: str | None, secret: str) -> str | None:
    """The memory subject for a valid cookie; None for a missing, malformed or forged one."""
    if not cookie or cookie.count(".") != 1:
        return None
    token, signature = cookie.split(".")
    if not re.fullmatch(r"[A-Za-z0-9_-]{24}", token) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", signature):
        return None
    if not hmac.compare_digest(signature, _signature(token, secret)):
        return None
    return _SUBJECT_PREFIX + token
