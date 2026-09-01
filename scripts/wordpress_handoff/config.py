"""Load repo-level WordPress handoff config. Taxonomy IDs live here, not in code."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import HandoffError

CONFIG_RELATIVE = Path("config/wordpress-handoff.json")
UNMAPPED_RULES = {"omit", "fail"}


def load_config(repo_root: Path, path: Path | None = None) -> dict[str, Any]:
    config_path = path or (repo_root / CONFIG_RELATIVE)
    if not config_path.is_file():
        raise HandoffError(f"Missing WordPress handoff config: {config_path}")
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HandoffError(f"Invalid WordPress handoff config JSON: {config_path}") from exc
    if not isinstance(data, dict):
        raise HandoffError("WordPress handoff config must be a JSON object.")
    taxonomy = data.get("taxonomy") or {}
    if not isinstance(taxonomy, dict):
        raise HandoffError("config.taxonomy must be an object.")
    for key in ("unmapped_category", "unmapped_tag"):
        rule = taxonomy.get(key, "omit")
        if rule not in UNMAPPED_RULES:
            raise HandoffError(
                f"config.taxonomy.{key} must be 'omit' or 'fail', not {rule!r}."
            )
        taxonomy[key] = rule
    taxonomy.setdefault("categories", {})
    taxonomy.setdefault("tags", {})
    if not isinstance(taxonomy["categories"], dict) or not isinstance(taxonomy["tags"], dict):
        raise HandoffError("taxonomy.categories and taxonomy.tags must be objects.")
    data["taxonomy"] = taxonomy
    data.setdefault("api_path", "/wp-json/wp/v2/posts")
    data.setdefault("timeout_seconds", 30)
    return data


def mapped_term_ids(
    names: list[str],
    mapping: dict[str, Any],
    *,
    kind: str,
    unmapped_rule: str,
) -> list[int]:
    ids: list[int] = []
    for name in names:
        key = name.strip()
        if not key:
            continue
        if key not in mapping:
            if unmapped_rule == "fail":
                raise HandoffError(
                    f"Unmapped WordPress {kind} {key!r}. Add a numeric ID in "
                    f"config/wordpress-handoff.json or do not invent IDs."
                )
            continue
        value = mapping[key]
        if value is None or value == "":
            if unmapped_rule == "fail":
                raise HandoffError(
                    f"WordPress {kind} {key!r} has no ID in config (null/empty). "
                    "Fill a real term ID; do not invent one."
                )
            continue
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise HandoffError(
                f"WordPress {kind} {key!r} mapping must be a positive integer ID, "
                f"not {value!r}."
            )
        ids.append(value)
    return ids
