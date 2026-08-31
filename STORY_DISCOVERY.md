# Story discovery — process for future research agents

This document is a **method**. It does **not** contain story ideas, slates, or current-events research.

A discovery run produces **candidate records** in `content/state/` with status `DISCOVERED` (and scores). It does **not** produce article drafts.

---

## Goal of discovery

Find **timely and worthwhile** candidates that fit [EDITORIAL_STRATEGY.md](EDITORIAL_STRATEGY.md), then **evaluate** them honestly—including the option to **pass**.

Success is a short list of scored candidates with sources and a clear pursue / watch / pass recommendation—not a pile of headlines.

---

## Discovery authorization gate

**[EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) is the owner-input source of truth** for whether a discovery-only run is authorized.

A **discovery-only** run may proceed when the **discovery-stage** requirements in that brief are complete (live-web authorization, geographies, first-run beat weighting, time window, candidate volume, source/social/peer/do-not-cover/handle-with-care/language/embargo rules, and the owner-approval stop before research/drafting).

The following are **not** blockers for `DISCOVERED`-state topic discovery, even if still marked TODO in the brief:

- Voice samples
- Archive / internal-link access
- Detailed audience persona
- Story-mix ratios
- Translation workflow for drafts
- Off-record / anonymous-source policy beyond “do not invent”
- Named outlet allowlist (optional)
- CMS setup
- House voice beyond the confirmed constraints
- Named reviewer contact channel for draft packets

Those unresolved items **may become blockers** before deep research, drafting, review, or publishing, when they are relevant to that later stage. Do not invent the missing policy; stop or mark `BLOCKED` at that later stage.

**First discovery run (and any discovery-only run until the owner says otherwise):**

- Stop at `DISCOVERED`.
- Produce scored candidates with `pursue` / `watch` / `pass` recommendations only.
- **No candidate may advance to deep research (`RESEARCHING`) or drafting (`DRAFTING`) without owner approval.**
- Do not chain discover-then-research in the same run.

Live-web, sourcing, social-platform, sensitivity, language, and leak/embargo rules in [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) remain controlling. Do not invent audience size, traffic, or unstated house customs.

---

## Discovery loop (when authorized)

Work **one contained task** at a time (see [AGENTS.md](AGENTS.md)). Scope from the brief: beats, 7–14 day window, US/Canada/UK diaspora emphasis, volume caps.

1. **Scope the run** — write beat(s), time window, geography, and exclusions into the state file.
2. **Collect signals** — publicly accessible sources only, per the brief. Record URL, date retrieved, and what the source actually says.
3. **Normalize candidates** — one person/event/work per candidate; no bundling unrelated items into a fake “moment.”
4. **Evaluate** against the criteria in this file and the brief.
5. **Score** using [STORY_SCORING.md](STORY_SCORING.md).
6. **Recommend** pursue / watch / pass, with one paragraph of reasoning. Flag handle-with-care topics as sensitive.
7. **Stop at `DISCOVERED`.** Do not deep-research or draft any ID in this run.

---

## Allowed signal classes

Use these classes when collecting publicly accessible signals. Live web use is allowed only when [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) authorizes discovery.

| Class | Role | Caution |
| --- | --- | --- |
| Official primary | Filings, court docs, company/gov/artist posts, release dates from rights holders | Still quote accurately; screenshots are not a substitute for the URL/date |
| Established reporting | Named publications with bylines | Attribute; do not treat one outlet as proof of a social trend |
| Community and local | Neighborhood orgs, campus papers, specialist newsletters | High value; verify reach and claims |
| Platform primary | A named person’s own post, video, or newsletter | Establishes *what they posted*, not that a broader claim is true |
| Aggregated “conversation” | Trends, Reddit, quote-tweets | Weakest class; never sufficient alone for a news claim |

**Not discovery:** inventing a topic because it “feels” on-brand; scraping private groups; using hacked, leaked, private, paywall-bypassed, embargoed, or access-controlled material (see the brief).

---

## Evaluation criteria

Score and narrate each candidate on **all** of the following. A pass on one criterion can kill the story.

### 1. Timeliness

- What **changed** (release, ruling, statement, event, death, deal)? Do not use leaks or embargoed material.
- Is the useful window **hours**, **days**, or **evergreen-with-a-hook**?
- If we would publish after the window, is there a durable explainer/feature version—or should we pass?

### 2. South Asian / diaspora relevance

- Who is this **for**, and which **named** communities, countries, languages, or diaspora geographies are implicated?
- Is relevance **central** or decorative (a South Asian extra in an otherwise generic Hollywood item)?
- Does the framing risk collapsing many peoples into one?

### 3. Audience fit

- Match to [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) geographies (US/Canada/UK diaspora emphasis; South Asia origin only with clear diaspora or cultural relevance; no forced diaspora angle) and the working audience in [EDITORIAL_STRATEGY.md](EDITORIAL_STRATEGY.md). A detailed audience persona is not required at discovery.
- Would a regular brwncltr reader recognize why this is on the site?
- Guides and lists must have a **use** (watch, cook, understand, attend, avoid a scam)—not a keyword dump.

### 4. Originality / angle

- What have others already said (list 2–5 existing pieces if they exist, with URLs)?
- What could brwncltr add: **specificity, primary voices, history, craft, diaspora reading, correction of a viral error**?
- If the answer is “same headline, shorter,” **pass**.

### 5. Source availability

- Primary sources: yes / no / maybe (who to contact; do **not** pretend interviews happened).
- Secondary: named outlets only.
- Are there **paywalls, language barriers, or safety issues** (sources at risk)? Flag them.

### 6. Can we add something useful?

Explicit test: **If we did not publish, would readers only miss a rewrite?** If yes, pass. Useful additions include verification, context, a community the nationals ignored, or a clear explainer of a confusing object (bill, platform change, award rule).

### 7. Longevity vs time sensitivity

Label each candidate:

- **Time-sensitive news** — ship fast or skip; do not sit in research for a week.
- **News with a feature tail** — short news possible; longer piece later with new reporting.
- **Durable** — culture, craft, community; “why now” can be a release, anniversary, or a documented shift—not a fake news peg.

---

## Recommendation labels

| Label | Meaning |
| --- | --- |
| **pursue** | Angle + sources look sufficient to *recommend* deep research — **does not** enter `RESEARCHING` until the owner approves that ID |
| **watch** | Real, but wait for a fact, date, or primary (embargo, ruling, release) |
| **pass** | Weak fit, unsourced, duplicative, or unsafe to do well |

Agents must not upgrade `pass` to `pursue` to fill a quota.

---

## Output of a discovery task

For each candidate, write a state record (see [TASK_STATE.md](TASK_STATE.md)) including:

- Working title (descriptive, not a publish headline)
- Beat(s) and hypothesized story type
- Why-now in one or two sentences
- Source list with retrieval dates
- Scores + narrative
- Recommendation
- Open questions
- Sensitive-topic flag when the candidate touches handle-with-care subjects in the brief
- `BLOCKED` if evaluation itself cannot proceed (e.g. the only available material is embargoed or access-controlled)

**Do not** fill [ARTICLE_TEMPLATE.md](ARTICLE_TEMPLATE.md) during discovery.

Cap: **10–15** candidates; recommend **no more than 5** as `pursue`.

---

## What is not required before discovery

Do not wait on drafting-stage TODOs in [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md). If those are still open, discovery-only may still run; later stages may not.

If discovery-stage fields in the brief are incomplete, do **not** invent them — improve the OS or wait. With the current brief, discovery-stage fields are complete enough to authorize a discovery-only run.
