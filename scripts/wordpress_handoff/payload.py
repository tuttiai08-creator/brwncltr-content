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
ELEMENTOR_META_KEYS = (
    "_elementor_edit_mode",
    "_elementor_data",
    "_elementor_template_type",
)


def reject_elementor_fields(payload: dict[str, Any]) -> None:
    """Fail if a payload would set Elementor editor meta. Content stays Gutenberg/HTML."""
    found = _elementor_keys(payload)
    if found:
        names = ", ".join(found)
        raise HandoffError(
            "Refusing to set Elementor fields "
            f"({names}). Draft handoff does not set _elementor_edit_mode, "
            "_elementor_data, or _elementor_template_type."
        )


def _elementor_keys(value: Any, found: list[str] | None = None) -> list[str]:
    if found is None:
        found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ELEMENTOR_META_KEYS and key not in found:
                found.append(key)
            _elementor_keys(item, found)
    elif isinstance(value, list):
        for item in value:
            _elementor_keys(item, found)
    return found


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
    reject_elementor_fields(payload)
    return payload
