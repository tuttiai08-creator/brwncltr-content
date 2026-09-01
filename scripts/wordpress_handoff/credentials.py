"""Load and validate WP credentials. Never log the application password."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from .client import Credentials
from .envfile import load_dotenv
from .errors import HandoffError
from .redact import collect_secrets, redact

ENV_KEYS = ("WP_BASE_URL", "WP_USERNAME", "WP_APP_PASSWORD")


def load_credentials(repo_root: Path, environ: dict[str, str] | None = None) -> Credentials:
    env = dict(os.environ if environ is None else environ)
    file_values = load_dotenv(repo_root / ".env")
    for key, value in file_values.items():
        env.setdefault(key, value)
    missing = [key for key in ENV_KEYS if not (env.get(key) or "").strip()]
    if missing:
        raise HandoffError(
            "Missing WordPress credentials: " + ", ".join(missing) + ". "
            "Set them in the environment or a local .env (not committed)."
        )
    base = env["WP_BASE_URL"].strip().rstrip("/")
    username = env["WP_USERNAME"].strip()
    password = env["WP_APP_PASSWORD"].strip()
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HandoffError("WP_BASE_URL must be an absolute http(s) URL.")
    if parsed.username or parsed.password:
        raise HandoffError(
            "WP_BASE_URL must not include credentials. Use WP_USERNAME and "
            "WP_APP_PASSWORD."
        )
    return Credentials(base_url=base, username=username, app_password=password)


def require_https_for_apply(credentials: Credentials) -> None:
    parsed = urlparse(credentials.base_url)
    if parsed.scheme.lower() != "https":
        raise HandoffError("Live --apply requires HTTPS WP_BASE_URL.")


def safe_error_text(message: str, credentials: Credentials | None) -> str:
    secrets = credentials.secrets() if credentials else []
    extra = collect_secrets(
        *(os.environ.get(key) for key in ENV_KEYS)
    )
    return redact(message, list(secrets) + extra)
