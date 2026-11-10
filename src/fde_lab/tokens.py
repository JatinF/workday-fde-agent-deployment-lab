"""In-memory token book. Secrets stay out of traces."""

from __future__ import annotations

import re
from collections.abc import Mapping

from fde_lab.models import AccessToken

_BEARER = re.compile(r"Bearer\s+\S+", re.IGNORECASE)
_LAB_TOKEN = re.compile(r"lab-token-\S+")


def redact_text(value: str) -> str:
    value = _BEARER.sub("Bearer [redacted]", value)
    return _LAB_TOKEN.sub("[redacted]", value)


def redact_obj(value: object) -> object:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(key): redact_obj(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_obj(item) for item in value]
    return value


class TokenBook:
    def __init__(self) -> None:
        self._secrets: dict[str, AccessToken] = {}
        self._issued = 0

    def issue(self, subject: str, epoch: int, *, valid: bool = True) -> AccessToken:
        self._issued += 1
        secret = "lab-token-" + subject + "-" + str(epoch) + "-" + str(self._issued)
        token = AccessToken(subject=subject, issued_epoch=epoch, valid=valid, secret=secret)
        self._secrets[secret] = token
        return token

    def authenticate(self, header: str | None) -> AccessToken | None:
        if header is None or not header.startswith("Bearer "):
            return None
        return self._secrets.get(header.removeprefix("Bearer ").strip())


def contains_secret(payload: str, secrets: Mapping[str, object]) -> bool:
    return any(secret and secret in payload for secret in secrets)
