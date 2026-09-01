"""Parse ARTICLE_TEMPLATE packets. No invented fields."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .errors import HandoffError

HEADING_RE = re.compile(r"^## (.+?)\s*$", re.MULTILINE)


@dataclass
class ArticlePacket:
    path: Path
    title: str
    slug: str
    excerpt: str
    body_markdown: str
    category: str
    tags: list[str]
    task_id: str
    packet_state: str


def parse_packet(path: Path) -> ArticlePacket:
    if not path.is_file():
        raise HandoffError(f"Missing article at {path}")
    text = path.read_text(encoding="utf-8")
    sections = _sections(text)
    title = _first_line(sections.get("Proposed headline", "")) or _document_title(text)
    slug = _first_line(sections.get("Slug", ""))
    excerpt = _paragraph(sections.get("Excerpt", ""))
    body = sections.get("Full draft", "").strip()
    category = _first_line(sections.get("Category", ""))
    tags = _comma_list(sections.get("Tags", ""))
    meta = _metadata_table(sections.get("Packet metadata", ""))
    missing: list[str] = []
    if not title:
        missing.append("title (Proposed headline)")
    if not slug:
        missing.append("slug")
    if not excerpt:
        missing.append("excerpt")
    if not body:
        missing.append("full draft body")
    if not category:
        missing.append("category")
    if missing:
        raise HandoffError("Missing required article metadata: " + ", ".join(missing))
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise HandoffError(
            f"Slug {slug!r} must be lowercase hyphenated (a-z, 0-9, hyphens)."
        )
    return ArticlePacket(
        path=path,
        title=title,
        slug=slug,
        excerpt=excerpt,
        body_markdown=body,
        category=category,
        tags=tags,
        task_id=meta.get("Task ID", ""),
        packet_state=meta.get("State", ""),
    )


def _sections(text: str) -> dict[str, str]:
    matches = list(HEADING_RE.finditer(text))
    out: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        out[match.group(1).strip()] = text[start:end].strip()
    return out


def _document_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _first_line(block: str) -> str:
    for line in block.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _paragraph(block: str) -> str:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    return " ".join(lines)


def _comma_list(block: str) -> list[str]:
    raw = _paragraph(block)
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _metadata_table(block: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in block.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0] not in {"Field", "---"} and not set(cells[0]) <= {"-"}:
            meta[cells[0]] = cells[1]
    return meta
