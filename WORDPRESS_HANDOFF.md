# WordPress draft handoff (v1)

Repo-level tool that creates a **WordPress draft** from **one** candidate whose canonical per-ID state is `READY_FOR_REVIEW`. It is operated later by the BRWNCLTR Publishing Manager bot.

This tool **cannot publish**. It cannot schedule. It creates a draft, or with `--update` replaces an existing **draft** or **pending** post in place. The payload status is always `draft`.

---

## Architecture

```
candidate ID
    → content/state/<bc-…>.md   (must be READY_FOR_REVIEW)
    → review_path article        (must live under content/ready-for-review/)
    → parse ARTICLE_TEMPLATE.md fields
    → formatting-only Markdown → HTML
    → create: POST /wp-json/wp/v2/posts                 (status=draft only)
      update: GET  /wp-json/wp/v2/posts/<id>?context=edit
              POST /wp-json/wp/v2/posts/<id>            (status=draft only)
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

1. Create a **dedicated low-privilege WordPress user** (not an administrator). The live account is a **Contributor**: it can edit its own drafts and cannot publish. That matches this tool. An Editor is stronger than required.
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

Default is dry-run. Create mode validates state + packet, prints the JSON payload, does not call WordPress, and does not write CMS fields.

Update mode (`--update`, no `--apply`) still needs HTTPS credentials. It **GETs** the existing draft and prints a diff (old vs new title, slug, word count, and headings, plus the post id that would be updated). It does not POST and does not write CMS fields.

```bash
python3 scripts/wp_create_draft.py bc-20260901-09 --update
```

`bc-20260901-09` is WordPress draft **12044**. `bc-20260901-10` is draft **12043**. Use `--update` for those ids so a rewrite replaces the draft.

---

## Live `--apply`

```bash
python3 scripts/wp_create_draft.py bc-20260901-10 --apply
```

Requires all three environment variables and **HTTPS**. POSTs `status: draft` only.

There is **no** CLI flag for `publish`, `future`, `private`, or any other status. `--status`, `--publish`, `--schedule` are rejected.

---

## Update an existing draft (`--update`)

`--update` is mutually exclusive with create. Create refuses when `wordpress_post_id` is already set. Update refuses when it is missing, and it never POSTs to the collection URL.

```bash
python3 scripts/wp_create_draft.py bc-20260901-09 --update --apply
```

Before any write, update loads `GET /wp-json/wp/v2/posts/<id>?context=edit` and continues only when that post exists and its status is `draft` or `pending`. `publish`, `future`, `private`, and `trash` are refused, as is any other status. The POST body is the same draft payload as create: title, content, excerpt, slug, `status=draft`, and mapped category/tag ids. Status in that body is `draft` even when the remote post is `pending`.

PUT, PATCH, and DELETE stay forbidden.

Optional slug change on an unpublished draft (packet slug is the default):

```bash
python3 scripts/wp_create_draft.py bc-20260901-09 --update --slug new-slug
```

Dry-run prints the live slug and the slug that would be saved. On `--apply`, if the new slug belongs to a different post, the update stops.

---

## Elementor

The handoff does not set `_elementor_edit_mode`, `_elementor_data`, or `_elementor_template_type`. Body HTML goes in `content`.

---

## Duplicate behavior

Before a live **create**, the tool stops with `WORDPRESS DRAFT ALREADY EXISTS` if:

- the canonical state file already has `wordpress_post_id`, or
- WordPress returns any post for the canonical slug (`GET` with `status=any`, authenticated)

Pass `--update` to replace the recorded draft. Create will not overwrite it.

---

## State write-back

On a successful draft create or in-place update, these fields are added or updated on the per-ID state file:

- `wordpress_post_id`
- `wordpress_status` (always `draft`)
- `wordpress_slug`
- `wordpress_handoff_at` (UTC)
- `wordpress_edit_url` (wp-admin edit URL)

`wordpress_post_id` stays the same on update. `wordpress_handoff_at` is the UTC time of the latest successful create or update. A log line is appended (`recorded` on create, `updated in place` on update). **`status:` remains `READY_FOR_REVIEW`.** `APPROVED` is never set by this tool. The editorial `updated:` date is left as it stands.

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
- create when `wordpress_post_id` is already set
- `--update` when `wordpress_post_id` is missing or not a positive integer
- `--slug` without `--update`, or a slug that is not lowercase hyphenated
- `--apply` or `--update` without credentials
- authenticated requests with a non-HTTPS `WP_BASE_URL`
- create when the slug already exists in WordPress
- update when the post is missing, or its status is not `draft` or `pending`
- update when the new slug belongs to a different post
- WordPress returns a non-draft status

---

## This tool cannot publish

The payload `status` is hardcoded to `draft`. The client `GET`s (duplicate check, or the draft being updated) and `POST`s (create, or update of that same id). It does not PUT, PATCH, or DELETE. It will not publish or schedule. Going live remains a human action in WordPress.
