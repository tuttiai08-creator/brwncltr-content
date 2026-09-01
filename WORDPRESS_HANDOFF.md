# WordPress draft handoff (v1)

Repo-level tool that creates a **WordPress draft** from **one** candidate whose canonical per-ID state is `READY_FOR_REVIEW`. It is operated later by the BRWNCLTR Publishing Manager bot.

This tool **cannot publish**. It cannot schedule. It cannot change an existing WordPress post.

---

## Architecture

```
candidate ID
    → content/state/<bc-…>.md   (must be READY_FOR_REVIEW)
    → review_path article        (must live under content/ready-for-review/)
    → parse ARTICLE_TEMPLATE.md fields
    → formatting-only Markdown → HTML
    → WordPress REST POST /wp-json/wp/v2/posts  (status=draft only)
    → write CMS metadata back onto the same state file
```

Editorial lifecycle is unchanged. Successful handoff records CMS fields and **leaves status `READY_FOR_REVIEW`**. It never writes `APPROVED`.

| Piece | Path |
| --- | --- |
| CLI | `scripts/wp_create_draft.py` |
| Library | `scripts/wordpress_handoff/` |
| Taxonomy / API config | `config/wordpress-handoff.json` |
| Credential template | `.env.example` |
| Tests | `tests/test_wordpress_handoff.py` |

Python 3 stdlib only. No LLM rewrite. Packet prose, quotes, and caveats are not edited.

---

## Setup

1. Create a **dedicated low-privilege WordPress user** (not an administrator). Grant only what is required to create drafts (typically an Editor or a custom role that can `edit_posts` / create posts, **not** `publish_posts` if your host can deny that capability).
2. In WP Admin → Users → Profile for that user: create an **Application Password**. Store it only in a local `.env` or the bot runtime environment.
3. Copy `.env.example` to `.env` (gitignored) and fill real values.
4. Optionally add WordPress category/tag **numeric IDs** to `config/wordpress-handoff.json`. Do not invent IDs.

---

## Environment variables

| Name | Purpose |
| --- | --- |
| `WP_BASE_URL` | Site origin, e.g. `https://brwncltr.com`. No credentials in the URL. **HTTPS required for `--apply`.** |
| `WP_USERNAME` | Dedicated automation username |
| `WP_APP_PASSWORD` | Application Password |

Never commit `.env`. The CLI never prints `WP_APP_PASSWORD`. Error text is redacted.

---

## Dedicated user and Application Password

Use a user that exists only for this automation. Do not reuse a personal admin account.

Application Passwords are created in WordPress (or via the host’s equivalent) for that user. If the password is leaked, revoke it in WP Admin and issue a new one. Rotate without changing this repo.

---

## Dry-run (default)

```bash
python3 scripts/wp_create_draft.py bc-20260901-10
```

Default is dry-run: validates state + packet, prints the JSON payload, **does not** call WordPress, **does not** write CMS fields.

---

## Live `--apply`

```bash
python3 scripts/wp_create_draft.py bc-20260901-10 --apply
```

Requires all three environment variables and **HTTPS**. POSTs `status: draft` only.

There is **no** CLI flag for `publish`, `future`, `private`, or any other status. `--status`, `--publish`, `--schedule` are rejected.

---

## Duplicate behavior

Before a live create, the tool stops with `WORDPRESS DRAFT ALREADY EXISTS` if:

- the canonical state file already has `wordpress_post_id`, or
- WordPress returns any post for the canonical slug (`GET` with `status=any`, authenticated)

v1 does **not** update or overwrite that post (no PUT/PATCH/DELETE).

---

## State write-back

On a successful draft create only, these fields are added or updated on the per-ID state file:

- `wordpress_post_id`
- `wordpress_status` (always `draft`)
- `wordpress_slug`
- `wordpress_handoff_at` (UTC)
- `wordpress_edit_url` (wp-admin edit URL)

A log line is appended. **`status:` remains `READY_FOR_REVIEW`.** `APPROVED` is never set by this tool.

---

## Taxonomy mapping

`config/wordpress-handoff.json`:

- `taxonomy.categories` / `taxonomy.tags`: maps packet names → WordPress term IDs (positive integers)
- `taxonomy.unmapped_category` / `taxonomy.unmapped_tag`: `omit` (default) or `fail`

v1 default is **omit** unmapped terms so a first run can create a draft without guessing IDs. If you set `fail`, an unmapped category or tag aborts before POST.

Never hardcode term IDs in Python.

---

## Failure behavior (fail closed)

No WordPress write if any of these fail:

- candidate ID invalid / no canonical per-ID state
- state is not `READY_FOR_REVIEW`
- missing `review_path` or article file
- article not under `content/ready-for-review/`
- missing title, slug, excerpt, full draft, or category
- invalid slug
- existing `wordpress_post_id`
- `--apply` without credentials
- `--apply` with non-HTTPS `WP_BASE_URL`
- slug already exists in WordPress
- WordPress returns a non-draft status

---

## This tool cannot publish

The payload `status` is hardcoded to `draft`. The client only `GET`s (duplicate check) and `POST`s (create). It will not publish, schedule, or modify an existing post. Going live remains a human action in WordPress.
