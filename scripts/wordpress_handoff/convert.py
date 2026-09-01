"""Deterministic Markdown → WordPress HTML. Formatting only; no rewrite."""

from __future__ import annotations

import html
import re

HEADING_LINE = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
UL_LINE = re.compile(r"^[-*]\s+(.+)$")
OL_LINE = re.compile(r"^(\d+)\.\s+(.+)$")
INLINE_CODE = re.compile(r"`([^`]+)`")
INLINE_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def markdown_to_plain(text: str) -> str:
    """Unwrap emphasis/links for title/excerpt. Does not change wording."""
    work = INLINE_CODE.sub(r"\1", text)
    work = INLINE_LINK.sub(r"\1", work)
    work = BOLD.sub(r"\1", work)
    work = ITALIC.sub(r"\1", work)
    return work.strip()


def markdown_to_wp_html(markdown_text: str) -> str:
    """Convert article body Markdown to HTML without changing wording."""
    lines = markdown_text.replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    paragraph: list[str] = []
    ul_items: list[str] = []
    ol_items: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(paragraph).strip()
            if text:
                blocks.append(f"<p>{inline(text)}</p>")
        paragraph = []

    def flush_ul() -> None:
        nonlocal ul_items
        if ul_items:
            inner = "".join(f"<li>{inline(item)}</li>" for item in ul_items)
            blocks.append(f"<ul>{inner}</ul>")
        ul_items = []

    def flush_ol() -> None:
        nonlocal ol_items
        if ol_items:
            inner = "".join(f"<li>{inline(item)}</li>" for item in ol_items)
            blocks.append(f"<ol>{inner}</ol>")
        ol_items = []

    def flush_lists() -> None:
        flush_ul()
        flush_ol()

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_paragraph()
            flush_lists()
            continue
        heading = HEADING_LINE.match(line)
        if heading:
            flush_paragraph()
            flush_lists()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            continue
        ul = UL_LINE.match(line)
        if ul:
            flush_paragraph()
            flush_ol()
            ul_items.append(ul.group(1))
            continue
        ol = OL_LINE.match(line)
        if ol:
            flush_paragraph()
            flush_ul()
            ol_items.append(ol.group(2))
            continue
        flush_lists()
        paragraph.append(line.strip())

    flush_paragraph()
    flush_lists()
    return "\n".join(blocks)


def inline(text: str) -> str:
    placeholders: list[str] = []

    def hold(html_fragment: str) -> str:
        token = f"\x00H{len(placeholders)}\x00"
        placeholders.append(html_fragment)
        return token

    def code_sub(match: re.Match[str]) -> str:
        return hold(f"<code>{html.escape(match.group(1))}</code>")

    def link_sub(match: re.Match[str]) -> str:
        label = html.escape(match.group(1))
        href = html.escape(match.group(2), quote=True)
        return hold(f'<a href="{href}">{label}</a>')

    work = INLINE_CODE.sub(code_sub, text)
    work = INLINE_LINK.sub(link_sub, work)
    work = html.escape(work)
    work = BOLD.sub(r"<strong>\1</strong>", work)
    work = ITALIC.sub(r"<em>\1</em>", work)
    for index, fragment in enumerate(placeholders):
        work = work.replace(f"\x00H{index}\x00", fragment)
    return work
