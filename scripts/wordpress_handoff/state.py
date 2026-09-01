"""Canonical per-ID state lookup and CMS write-back. Never sets APPROVED."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .errors import HandoffError

ID_PREFIX_RE = re.compile(r"^(bc-\d{8}-\d+)(?:-|$)")
STATUS_RE = re.compile(r"^- status:\s*(\S+)\s*$", re.MULTILINE)
FIELD_RE = re.compile(r"^- ([a-z_]+):\s*(.*)$")
REQUIRED_EDITORIAL_STATUS = "READY_FOR_REVIEW"
FORBIDDEN_EDITORIAL_WRITE = "APPROVED"


@dataclass
class TaskState:
    task_id_prefix: str
    path: Path
    text: str
    status: str
    fields: dict[str, str]

    @property
    def review_path(self) -> str:
        return (self.fields.get("review_path") or "").strip()

    @property
    def wordpress_post_id(self) -> str:
        return (self.fields.get("wordpress_post_id") or "").strip()

    @property
    def wordpress_slug(self) -> str:
        return (self.fields.get("wordpress_slug") or "").strip()


def normalize_candidate_id(raw: str) -> str:
    value = (raw or "").strip()
    match = ID_PREFIX_RE.match(value)
    if not match:
        raise HandoffError(
            f"Invalid candidate ID {raw!r}. Expected bc-YYYYMMDD-## or "
            "bc-YYYYMMDD-##-slug."
        )
    return match.group(1)


def find_canonical_state(repo_root: Path, candidate_id: str) -> TaskState:
    prefix = normalize_candidate_id(candidate_id)
    state_dir = repo_root / "content" / "state"
    if not state_dir.is_dir():
        raise HandoffError(f"Missing state directory: {state_dir}")
    matches = sorted(
        p
        for p in state_dir.glob(f"{prefix}*.md")
        if p.is_file() and p.name.startswith(prefix)
    )
    # Ignore discovery slates and other non per-ID files.
    per_id = [p for p in matches if _is_per_id_state(p, prefix)]
    if not per_id:
        raise HandoffError(
            f"No canonical per-ID state file for {prefix} under content/state/."
        )
    if len(per_id) > 1:
        names = ", ".join(p.name for p in per_id)
        raise HandoffError(f"Ambiguous per-ID state for {prefix}: {names}")
    path = per_id[0]
    text = path.read_text(encoding="utf-8")
    status_match = STATUS_RE.search(text)
    if not status_match:
        raise HandoffError(f"State file {path.name} has no status field.")
    status = status_match.group(1)
    fields = _parse_fields(text)
    return TaskState(
        task_id_prefix=prefix,
        path=path,
        text=text,
        status=status,
        fields=fields,
    )


def require_ready_for_review(state: TaskState) -> None:
    if state.status != REQUIRED_EDITORIAL_STATUS:
        raise HandoffError(
            f"Candidate {state.task_id_prefix} is {state.status}, not "
            f"{REQUIRED_EDITORIAL_STATUS}. WordPress draft handoff only accepts "
            "canonical per-ID READY_FOR_REVIEW."
        )


def require_no_existing_handoff(state: TaskState) -> None:
    if state.wordpress_post_id:
        raise HandoffError("WORDPRESS DRAFT ALREADY EXISTS")


def resolve_article_path(repo_root: Path, state: TaskState) -> Path:
    relative = state.review_path
    if not relative:
        raise HandoffError(
            f"State {state.path.name} has no review_path. Missing article."
        )
    path = (repo_root / relative).resolve()
    ready_root = (repo_root / "content" / "ready-for-review").resolve()
    try:
        path.relative_to(ready_root)
    except ValueError as exc:
        raise HandoffError(
            f"review_path must be under content/ready-for-review/, got {relative}."
        ) from exc
    if not path.is_file():
        raise HandoffError(f"Missing article at {relative}")
    return path


def write_cms_handoff(
    state: TaskState,
    *,
    post_id: int,
    slug: str,
    wp_status: str,
    edit_url: str,
    handed_off_at: str | None = None,
) -> str:
    if wp_status != "draft":
        raise HandoffError("Refusing to write back a non-draft WordPress status.")
    if state.status == FORBIDDEN_EDITORIAL_WRITE:
        raise HandoffError("Refusing to touch an APPROVED state file.")
    stamp = handed_off_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = stamp[:10]
    new_text = _upsert_field(state.text, "wordpress_post_id", str(post_id))
    new_text = _upsert_field(new_text, "wordpress_status", "draft")
    new_text = _upsert_field(new_text, "wordpress_slug", slug)
    new_text = _upsert_field(new_text, "wordpress_handoff_at", stamp)
    if edit_url:
        new_text = _upsert_field(new_text, "wordpress_edit_url", edit_url)
    log_line = (
        f"- {today}: WordPress draft handoff recorded post_id={post_id} "
        f"status=draft. Editorial status remains {state.status}. Not APPROVED."
    )
    new_text = _append_log(new_text, log_line)
    written_status = STATUS_RE.search(new_text)
    if not written_status or written_status.group(1) != state.status:
        raise HandoffError("Write-back would have changed editorial status; aborting.")
    if written_status.group(1) == FORBIDDEN_EDITORIAL_WRITE:
        raise HandoffError("Refusing to mark editorial state APPROVED.")
    state.path.write_text(new_text, encoding="utf-8")
    state.text = new_text
    state.fields = _parse_fields(new_text)
    return new_text


def _is_per_id_state(path: Path, prefix: str) -> bool:
    name = path.name
    if name in {f"{prefix}.md", f"{prefix}"}:
        return True
    return name.startswith(f"{prefix}-") and name.endswith(".md")


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = FIELD_RE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def _upsert_field(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^- {re.escape(key)}:.*$", re.MULTILINE)
    replacement = f"- {key}: {value}"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    status_line = STATUS_RE.search(text)
    if not status_line:
        raise HandoffError("Cannot write CMS fields: missing status line.")
    insert_at = status_line.end()
    return text[:insert_at] + f"\n{replacement}" + text[insert_at:]


def _append_log(text: str, line: str) -> str:
    if re.search(r"^## Log\s*$", text, re.MULTILINE):
        if not text.endswith("\n"):
            text += "\n"
        return text + line + "\n"
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n## Log\n\n" + line + "\n"
