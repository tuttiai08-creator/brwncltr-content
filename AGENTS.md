# Agent operating rules

This file is binding for any autonomous or assisted agent working in this repository (Cursor agents, Grok Bots, future research/writing jobs).

Human editors own publication. Agents produce **reviewable artifacts** and stop at the edges below.

---

## Mission

Help brwncltr identify worthwhile stories, research them, and draft to the article template—**without** inventing reality or shipping live posts.

Read, in order, before any editorial task:

1. [README.md](README.md)
2. [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) — owner-input source of truth (discovery gate and later-stage TODOs)
3. [EDITORIAL_RULES.md](EDITORIAL_RULES.md)
4. [EDITORIAL_STRATEGY.md](EDITORIAL_STRATEGY.md)
5. The file for the current task ([STORY_DISCOVERY.md](STORY_DISCOVERY.md), [STORY_SCORING.md](STORY_SCORING.md), [ARTICLE_TEMPLATE.md](ARTICLE_TEMPLATE.md), [TASK_STATE.md](TASK_STATE.md))

---

## Research before writing

- Do not draft from memory of “how these stories usually go.”
- Discovery and research are separate tasks unless the owner explicitly chains **one** candidate ID.
- Writing may only use claims documented in `content/research/` (or the research section of the packet) with sources.

---

## One contained editorial task at a time

A single run should be one of:

- Improve operating docs (no live topics)
- Discover and score candidates (when [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) authorizes discovery-only; stop at `DISCOVERED`)
- Deep-research **one** task ID
- Draft **one** task ID from research
- Move **one** packet to ready-for-review if the completeness gate passes
- Resolve editor comments on **one** ID

Do not discover 20 stories and draft three in the same run.

---

## Never invent facts or quotes

See [EDITORIAL_RULES.md](EDITORIAL_RULES.md). If a fact is missing, omit it, mark `[NEED SOURCE]`, or set `BLOCKED`.

---

## Never publish automatically

- No WordPress publish (integration is not built; do not add it unless asked).
- No “posting” social as if live.
- `APPROVED` is a **human** state. Agents may suggest it is ready; they may not mark `APPROVED` unless the owner’s documented process says a named human already approved in-band.

---

## Preserve research / draft / review states

- Follow [TASK_STATE.md](TASK_STATE.md).
- Put files in the correct folders.
- Do not delete history of sources when updating notes; append and date new checks.
- Status changes must be visible in the state file.

---

## BLOCKED

If an **important** fact cannot be verified (load-bearing for the lede, accusation, statistic, quote, or identity of a person/community):

1. Stop drafting as if it were true.
2. Set state `BLOCKED`.
3. List exactly what is unknown, what was tried, and what a human must decide.
4. Leave the artifact reviewable (partial draft + notes), not empty.

“Important” includes anything that would be unfair, defamatory, or flattening if guessed.

---

## Do not overwrite published or editorial work without explicit approval

Do not replace, silently edit, or “improve” files that are:

- `READY_FOR_REVIEW` or `APPROVED`
- clearly marked as human-edited
- described as published on the live site

without the owner/editor saying to revise that ID.

If you find an error, **add a dated note** and wait.

---

## Reviewable artifacts

Every run should leave something a human can audit:

- State file with scores, sources, dates
- Research notes with URLs and retrieval dates
- Drafts that map claims to sources
- Explicit `BLOCKED` reasons

Do not leave work only in chat.

---

## Out of scope unless the owner asks

- Live discovery except when [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) authorizes a discovery-only run (see [STORY_DISCOVERY.md](STORY_DISCOVERY.md) gate)
- Deep research or drafting of a candidate without owner approval of that ID
- Writing articles during OS-only phases or during discovery-only runs
- CMS / WordPress
- Scraping private or login-walled community spaces
- Contacting sources while impersonating staff

---

## Safety defaults

- No medical, legal, or investment advice as fact.
- No caste, communal, or criminal allegations without sourced, attributed reporting and human authorization.
- No sexual content involving minors (ever).
- No instructions that would help harassment or doxxing.
