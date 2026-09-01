"""Orchestrate draft-only WordPress handoff for one READY_FOR_REVIEW ID."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import ALLOWED_WP_STATUS, DUPLICATE_MESSAGE
from .client import WordPressClient
from .config import load_config
from .credentials import load_credentials, require_https_for_apply, safe_error_text
from .errors import HandoffError
from .packet import parse_packet
from .payload import build_payload
from .state import (
    find_canonical_state,
    require_no_existing_handoff,
    require_ready_for_review,
    resolve_article_path,
    write_cms_handoff,
)


@dataclass
class HandoffResult:
    dry_run: bool
    candidate_id: str
    payload: dict[str, Any]
    wordpress_post_id: int | None = None
    message: str = ""


def run_handoff(
    repo_root: Path,
    candidate_id: str,
    *,
    apply: bool = False,
    client: WordPressClient | None = None,
    environ: dict[str, str] | None = None,
) -> HandoffResult:
    repo_root = repo_root.resolve()
    config = load_config(repo_root)
    state = find_canonical_state(repo_root, candidate_id)
    require_ready_for_review(state)
    require_no_existing_handoff(state)
    article_path = resolve_article_path(repo_root, state)
    packet = parse_packet(article_path)
    payload = build_payload(packet, config)
    if payload["status"] != ALLOWED_WP_STATUS:
        raise HandoffError("Payload status is not draft; aborting.")

    if not apply:
        return HandoffResult(
            dry_run=True,
            candidate_id=state.task_id_prefix,
            payload=payload,
            message=(
                f"DRY RUN for {state.task_id_prefix}: no network write, "
                "no WordPress POST, editorial status unchanged "
                f"({state.status})."
            ),
        )

    credentials = None
    try:
        credentials = load_credentials(repo_root, environ=environ)
        require_https_for_apply(credentials)
        wp = client or WordPressClient(
            credentials,
            api_path=str(config.get("api_path") or "/wp-json/wp/v2/posts"),
            timeout_seconds=int(config.get("timeout_seconds") or 30),
        )
        existing = wp.find_by_slug(payload["slug"])
        if existing:
            raise HandoffError(DUPLICATE_MESSAGE)
        created = wp.create_draft(payload)
        post_id = int(created["id"])
        slug = str(created.get("slug") or payload["slug"])
        edit_url = admin_edit_url(credentials.base_url, post_id, created)
        write_cms_handoff(
            state,
            post_id=post_id,
            slug=slug,
            wp_status="draft",
            edit_url=edit_url,
        )
        return HandoffResult(
            dry_run=False,
            candidate_id=state.task_id_prefix,
            payload=payload,
            wordpress_post_id=post_id,
            message=(
                f"Created WordPress draft id={post_id} for {state.task_id_prefix}. "
                f"Editorial status remains READY_FOR_REVIEW."
            ),
        )
    except HandoffError as exc:
        raise HandoffError(safe_error_text(str(exc), credentials)) from None


def admin_edit_url(base_url: str, post_id: int, created: dict[str, Any]) -> str:
    del created  # v1 records the admin edit URL only; never a public publish URL.
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return f"{origin}/wp-admin/post.php?post={post_id}&action=edit"


def format_dry_run(result: HandoffResult) -> str:
    pretty = json.dumps(result.payload, indent=2, ensure_ascii=False)
    return f"{result.message}\n\nWordPress payload (status is always draft):\n{pretty}\n"
