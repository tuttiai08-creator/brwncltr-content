# Task state model

Editorial work is a **task** with a stable ID and a single status. Agents update the state file; they do not invent parallel trackers.

CMS integration is optional metadata on the same per-ID state file—**never** a publish trigger and **never** an `APPROVED` write. WordPress draft handoff is documented in [WORDPRESS_HANDOFF.md](WORDPRESS_HANDOFF.md).

---

## States

```
DISCOVERED → RESEARCHING → DRAFTING → READY_FOR_REVIEW → APPROVED
                 ↘           ↙
                   BLOCKED
```

| State | Meaning | Typical location |
| --- | --- | --- |
| **DISCOVERED** | Candidate exists; scored; not deep-researched | `content/state/` only |
| **RESEARCHING** | Sources and notes in progress | `content/state/` + `content/research/` |
| **DRAFTING** | Template being filled from research | `content/state/` + `content/drafts/` |
| **BLOCKED** | Stopped: important facts unverified or policy stop | Same folders; reason required |
| **READY_FOR_REVIEW** | Completeness gate passed; waiting on a human | `content/ready-for-review/` + state |
| **APPROVED** | Human accepted the packet (still not auto-published) | State; CMS draft only in a future system |

`BLOCKED` may be entered from `RESEARCHING` or `DRAFTING`. After a human unblocks, return to `RESEARCHING` or `DRAFTING` as appropriate—not directly to `APPROVED`.

There is no `PUBLISHED` state in this repo yet. Live publication is human + WordPress, outside this OS.

---

## Task ID

Format: `bc-YYYYMMDD-##` (sequence per day) plus a short kebab slug for humans, e.g. `bc-20260830-01-working-label`.

IDs are assigned when a candidate is written to `content/state/`. Do not reuse IDs.

---

## State file convention

Path: `content/state/<task-id>.md`

Minimum fields:

```markdown
# bc-YYYYMMDD-##-short-label

- status: DISCOVERED | RESEARCHING | DRAFTING | BLOCKED | READY_FOR_REVIEW | APPROVED
- created: YYYY-MM-DD
- updated: YYYY-MM-DD
- beat:
- story_type_hypothesis:
- recommendation: pursue | watch | pass | (empty after pursue starts)
- blocked_reason: (required if BLOCKED)
- research_path:
- draft_path:
- review_path:
- wordpress_post_id: (optional; set only after a successful draft create)
- wordpress_status: draft (optional; this repo never writes a public WP status)
- wordpress_slug:
- wordpress_handoff_at:
- wordpress_edit_url:

## Why now

## Sources seen

## Scores

(see STORY_SCORING.md)

## Open questions

## Log

- YYYY-MM-DD: status change or note
```

These `wordpress_*` fields are CMS handoff records. They do **not** change editorial `status`. Agents must not set `status: APPROVED` because a draft exists.

Do not put full article drafts in the state file.

---

## Folder rules

| Folder | Allowed |
| --- | --- |
| `content/research/` | Notes, timelines, quote logs, unverified lists |
| `content/drafts/` | Article template packets in `DRAFTING` or `BLOCKED` |
| `content/ready-for-review/` | Complete packets only |
| `content/state/` | One markdown record per task |

When moving to review, **copy or move** the packet to `content/ready-for-review/` and point `review_path` at it. Do not leave the only copy exclusively in chat.

---

## Transitions (agents)

| From | To | Allowed when |
| --- | --- | --- |
| — | DISCOVERED | Authorized discovery run; candidate recorded |
| DISCOVERED | RESEARCHING | Recommendation `pursue` and owner/agent tasked this ID |
| RESEARCHING | DRAFTING | Enough sourced material to outline without invention |
| RESEARCHING or DRAFTING | BLOCKED | Important fact unverifiable or policy stop |
| BLOCKED | RESEARCHING or DRAFTING | Human or new verification unblocks |
| DRAFTING | READY_FOR_REVIEW | [ARTICLE_TEMPLATE.md](ARTICLE_TEMPLATE.md) completeness gate |
| READY_FOR_REVIEW | APPROVED | **Human only** |
| READY_FOR_REVIEW | DRAFTING | Human requested revisions |

Agents must not jump `DISCOVERED` → `READY_FOR_REVIEW`.
