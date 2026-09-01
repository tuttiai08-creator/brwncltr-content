"""Strip secrets from any string that might be logged."""

from __future__ import annotations

from typing import Iterable


def collect_secrets(*values: str | None) -> list[str]:
    secrets: list[str] = []
    for value in values:
        if value:
            secrets.append(value)
            compact = value.replace(" ", "")
            if compact and compact != value:
                secrets.append(compact)
    return secrets


def redact(text: str, secrets: Iterable[str]) -> str:
    redacted = text
    for secret in sorted({s for s in secrets if s}, key=len, reverse=True):
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted
