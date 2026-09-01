"""WordPress REST client. POST drafts only. Never PUT/PATCH/publish."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from .errors import HandoffError
from .redact import redact

ALLOWED_METHODS = frozenset({"GET", "POST"})
FORBIDDEN_METHODS = frozenset({"PUT", "PATCH", "DELETE"})


@dataclass
class Credentials:
    base_url: str
    username: str
    app_password: str

    @property
    def origin(self) -> str:
        return self.base_url.rstrip("/")

    def secrets(self) -> list[str]:
        from .redact import collect_secrets

        return collect_secrets(self.app_password, self.username)


@dataclass
class HttpResponse:
    status: int
    body: Any
    headers: dict[str, str] = field(default_factory=dict)


Opener = Callable[[urllib.request.Request], HttpResponse]


class WordPressClient:
    def __init__(
        self,
        credentials: Credentials,
        *,
        api_path: str = "/wp-json/wp/v2/posts",
        timeout_seconds: int = 30,
        opener: Opener | None = None,
    ) -> None:
        self.credentials = credentials
        self.api_path = api_path if api_path.startswith("/") else f"/{api_path}"
        self.timeout_seconds = timeout_seconds
        self._opener = opener or default_opener(timeout_seconds)

    def posts_url(self) -> str:
        return f"{self.credentials.origin}{self.api_path}"

    def find_by_slug(self, slug: str) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode(
            {
                "slug": slug,
                "status": "any",
                "per_page": "10",
                "context": "edit",
            }
        )
        response = self._request("GET", f"{self.posts_url()}?{query}")
        if not isinstance(response.body, list):
            raise HandoffError("WordPress slug lookup returned a non-list body.")
        return response.body

    def create_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("status") != "draft":
            raise HandoffError("Refusing to POST a non-draft WordPress payload.")
        response = self._request("POST", self.posts_url(), payload)
        if response.status not in {200, 201}:
            raise HandoffError(
                f"WordPress draft create failed with HTTP {response.status}."
            )
        if not isinstance(response.body, dict):
            raise HandoffError("WordPress draft create returned a non-object body.")
        returned_status = response.body.get("status")
        if returned_status != "draft":
            raise HandoffError(
                "WordPress did not return status=draft; refusing to continue. "
                "No repository APPROVED write."
            )
        if not response.body.get("id"):
            raise HandoffError("WordPress draft create returned no post id.")
        return response.body

    def _request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> HttpResponse:
        method = method.upper()
        if method in FORBIDDEN_METHODS:
            raise HandoffError(
                f"HTTP {method} is forbidden in v1. Existing WordPress posts "
                "are never updated."
            )
        if method not in ALLOWED_METHODS:
            raise HandoffError(f"HTTP {method} is not allowed.")
        if method == "POST" and payload is None:
            raise HandoffError("POST requires a JSON payload.")
        data = None
        headers = {
            "Accept": "application/json",
            "User-Agent": "brwncltr-wordpress-handoff/1",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        token = _basic_token(self.credentials.username, self.credentials.app_password)
        request.add_header("Authorization", f"Basic {token}")
        try:
            return self._opener(request)
        except HandoffError as exc:
            raise HandoffError(
                redact(str(exc), self.credentials.secrets())
            ) from None
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except OSError:
                body = ""
            message = f"WordPress HTTP {exc.code}"
            if body:
                message = f"{message}: {body[:500]}"
            raise HandoffError(redact(message, self.credentials.secrets())) from None
        except urllib.error.URLError as exc:
            raise HandoffError(
                redact(f"WordPress request failed: {exc}", self.credentials.secrets())
            ) from None


def default_opener(timeout_seconds: int) -> Opener:
    def open_request(request: urllib.request.Request) -> HttpResponse:
        context = ssl.create_default_context()
        with urllib.request.urlopen(
            request, timeout=timeout_seconds, context=context
        ) as response:
            raw = response.read().decode("utf-8")
            body: Any
            if raw.strip():
                body = json.loads(raw)
            else:
                body = None
            headers = {k.lower(): v for k, v in response.headers.items()}
            return HttpResponse(status=response.status, body=body, headers=headers)

    return open_request


def _basic_token(username: str, password: str) -> str:
    import base64

    raw = f"{username}:{password}".encode("utf-8")
    return base64.b64encode(raw).decode("ascii")
