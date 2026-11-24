"""Orchestrate draft-only WordPress handoff for one READY_FOR_REVIEW ID.

Create posts a new draft. Update rewrites an existing draft or pending post
in place. Neither path publishes.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import ALLOWED_WP_STATUS, DUPLICATE_MESSAGE
from .client import WordPressClient
from .config import load_config
from .credentials import (
    load_credentials,
    require_https,
    require_https_for_apply,
    safe_error_text,
)
from .errors import HandoffError
from .packet import parse_packet
from .payload import build_payload, reject_elementor_fields
from .state import (
    find_canonical_state,
    require_existing_post_id,
    require_no_existing_handoff,
    require_ready_for_review,
    resolve_article_path,
    write_cms_handoff,
)

UPDATABLE_REMOTE_STATUSES = frozenset({"draft", "pending"})
_SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_HTML_HEADING_RE = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass
class HandoffResult:
    dry_run: bool
    candidate_id: str
    payload: dict[str, Any]
    wordpress_post_id: int | None = None
    message: str = ""
    mode: str = "create"


def run_handoff(
    repo_root: Path,
    candidate_id: str,
    *,
    apply: bool = False,
    client: WordPressClient | None = None,
    environ: dict[str, str] | None = None,
    update: bool = False,
    slug: str | None = None,
) -> HandoffResult:
    if not update and slug is not None:
        raise HandoffError(
            "--slug applies only with --update. "
            "Create mode reads the slug from the packet."
        )
    repo_root = repo_root.resolve()
    if update:
        return _run_update(
            repo_root,
            candidate_id,
            apply=apply,
            client=client,
            environ=environ,
            slug=slug,
        )
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
        created_slug = str(created.get("slug") or payload["slug"])
        edit_url = admin_edit_url(credentials.base_url, post_id, created)
        write_cms_handoff(
            state,
            post_id=post_id,
            slug=created_slug,
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


def _run_update(
    repo_root: Path,
    candidate_id: str,
    *,
    apply: bool,
    client: WordPressClient | None,
    environ: dict[str, str] | None,
    slug: str | None,
) -> HandoffResult:
    config = load_config(repo_root)
    state = find_canonical_state(repo_root, candidate_id)
    require_ready_for_review(state)
    post_id = require_existing_post_id(state)
    article_path = resolve_article_path(repo_root, state)
    packet = parse_packet(article_path)
    payload = build_payload(packet, config)
    apply_slug_override(payload, slug)
    if payload.get("status") != ALLOWED_WP_STATUS:
        raise HandoffError("Payload status is not draft; aborting.")
    reject_elementor_fields(payload)

    credentials = None
    try:
        credentials = load_credentials(repo_root, environ=environ)
        require_https(
            credentials,
            message="Authenticated WordPress requests require HTTPS WP_BASE_URL.",
        )
        wp = client or WordPressClient(
            credentials,
            api_path=str(config.get("api_path") or "/wp-json/wp/v2/posts"),
            timeout_seconds=int(config.get("timeout_seconds") or 30),
        )
        existing = wp.get_post(post_id)
        require_updatable_remote_status(existing, post_id)
        remote_id = existing.get("id")
        if remote_id is not None and _positive_post_id(remote_id) != post_id:
            raise HandoffError(
                f"Refusing update: WordPress returned post {remote_id} "
                f"for requested id {post_id}."
            )
        if not apply:
            return HandoffResult(
                dry_run=True,
                candidate_id=state.task_id_prefix,
                payload=payload,
                wordpress_post_id=post_id,
                mode="update",
                message=format_update_diff(
                    candidate_id=state.task_id_prefix,
                    post_id=post_id,
                    existing=existing,
                    payload=payload,
                    editorial_status=state.status,
                ),
            )
        new_slug = str(payload["slug"])
        old_slug = str(existing.get("slug") or "")
        if new_slug != old_slug:
            taken = _other_post_id(wp.find_by_slug(new_slug), post_id)
            if taken is not None:
                raise HandoffError(
                    f"Refusing update: slug {new_slug!r} already belongs to "
                    f"WordPress post {taken}."
                )
        updated = wp.update_draft(post_id, payload)
        slug_written = str(updated.get("slug") or new_slug)
        edit_url = admin_edit_url(credentials.base_url, post_id, updated)
        write_cms_handoff(
            state,
            post_id=post_id,
            slug=slug_written,
            wp_status="draft",
            edit_url=edit_url,
            action="update",
        )
        return HandoffResult(
            dry_run=False,
            candidate_id=state.task_id_prefix,
            payload=payload,
            wordpress_post_id=post_id,
            mode="update",
            message=(
                f"Updated WordPress draft id={post_id} for {state.task_id_prefix}. "
                "Editorial status remains READY_FOR_REVIEW."
            ),
        )
    except HandoffError as exc:
        raise HandoffError(safe_error_text(str(exc), credentials)) from None


def apply_slug_override(payload: dict[str, Any], slug: str | None) -> None:
    if slug is None:
        return
    value = slug.strip()
    if not _SLUG_RE.fullmatch(value):
        raise HandoffError(
            f"Slug {value!r} must be lowercase hyphenated (a-z, 0-9, hyphens)."
        )
    payload["slug"] = value


def require_updatable_remote_status(post: dict[str, Any], post_id: int) -> str:
    status = post.get("status")
    if not isinstance(status, str) or status not in UPDATABLE_REMOTE_STATUSES:
        raise HandoffError(
            f"Refusing update: WordPress post {post_id} has status {status!r}. "
            "Only draft or pending can be updated in place. "
            "publish, future, private, and trash are refused."
        )
    return status


def format_update_diff(
    *,
    candidate_id: str,
    post_id: int,
    existing: dict[str, Any],
    payload: dict[str, Any],
    editorial_status: str,
) -> str:
    old_title = plain_text(existing.get("title"))
    new_title = plain_text(payload.get("title"))
    old_slug = str(existing.get("slug") or "")
    new_slug = str(payload.get("slug") or "")
    old_content = wp_field_text(existing.get("content"))
    new_content = wp_field_text(payload.get("content"))
    lines = [
        f"UPDATE DRY RUN for {candidate_id}: post ID {post_id} will be updated.",
        "No WordPress write. Payload status is draft. "
        f"Editorial status remains {editorial_status}.",
        "",
        "Title:",
        f"  old: {old_title}",
        f"  new: {new_title}",
        "Slug:",
        f"  old: {old_slug}",
        f"  new: {new_slug}",
        "Word count:",
        f"  old: {count_words(old_content)}",
        f"  new: {count_words(new_content)}",
        "Headings:",
        "  old:",
        *_heading_lines(extract_headings(old_content)),
        "  new:",
        *_heading_lines(extract_headings(new_content)),
    ]
    if old_slug != new_slug:
        lines.extend(
            [
                "",
                f"Slug change on unpublished draft: {old_slug} -> {new_slug}",
            ]
        )
    return "\n".join(lines)


def wp_field_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        raw = value.get("raw")
        if isinstance(raw, str) and raw.strip():
            return raw
        rendered = value.get("rendered")
        if isinstance(rendered, str):
            return rendered
    return ""


def plain_text(value: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", wp_field_text(value))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def count_words(text: str) -> int:
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = html.unescape(plain).replace("\u00a0", " ")
    return len(re.findall(r"\S+", plain))


def extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for match in _HTML_HEADING_RE.finditer(text):
        inner = re.sub(r"<[^>]+>", "", match.group(2))
        inner = html.unescape(inner)
        inner = re.sub(r"\s+", " ", inner).strip()
        headings.append(f"h{match.group(1)}: {inner}")
    if headings or re.search(r"<h[1-6]\b", text, flags=re.IGNORECASE):
        return headings
    for line in text.splitlines():
        match = _MARKDOWN_HEADING_RE.match(line)
        if match:
            headings.append(f"h{len(match.group(1))}: {match.group(2).strip()}")
    return headings


def _heading_lines(headings: list[str]) -> list[str]:
    if not headings:
        return ["    (none)"]
    return [f"    - {item}" for item in headings]


def _positive_post_id(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit() and int(value) > 0:
        return int(value)
    return None


def _other_post_id(posts: list[Any], post_id: int) -> int | None:
    for post in posts:
        if not isinstance(post, dict):
            continue
        other = _positive_post_id(post.get("id"))
        if other is not None and other != post_id:
            return other
    return None
