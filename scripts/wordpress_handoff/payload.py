"""WordPress REST payload. Status is always draft; no other status exists."""

from __future__ import annotations

from typing import Any

from . import ALLOWED_WP_STATUS
from .config import mapped_term_ids
from .convert import markdown_to_plain, markdown_to_wp_html
from .errors import HandoffError
from .packet import ArticlePacket

FORBIDDEN_STATUSES = frozenset(
    {"publish", "future", "private", "pending", "public"}
)


def build_payload(
    packet: ArticlePacket,
    config: dict[str, Any],
    *,
    status: str | None = None,
) -> dict[str, Any]:
    if status is not None:
        raise HandoffError(
            "WordPress status cannot be selected. This tool only creates drafts."
        )
    taxonomy = config["taxonomy"]
    categories = mapped_term_ids(
        [packet.category],
        taxonomy.get("categories") or {},
        kind="category",
        unmapped_rule=taxonomy.get("unmapped_category", "omit"),
    )
    tags = mapped_term_ids(
        packet.tags,
        taxonomy.get("tags") or {},
        kind="tag",
        unmapped_rule=taxonomy.get("unmapped_tag", "omit"),
    )
    payload: dict[str, Any] = {
        "title": markdown_to_plain(packet.title),
        "slug": packet.slug,
        "excerpt": markdown_to_plain(packet.excerpt),
        "content": markdown_to_wp_html(packet.body_markdown),
        "status": ALLOWED_WP_STATUS,
    }
    if payload["status"] != "draft" or payload["status"] in FORBIDDEN_STATUSES:
        raise HandoffError("Refusing to send a non-draft WordPress status.")
    if categories:
        payload["categories"] = categories
    if tags:
        payload["tags"] = tags
    return payload
