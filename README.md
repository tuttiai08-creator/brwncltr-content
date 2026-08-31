# brwncltr editorial operating system

This repository is the **foundational operating system** for autonomous editorial work at [brwncltr.com](https://brwncltr.com): a South Asian culture and media publication.

It is **not** a CMS, a scraper, or a publishing pipeline. It is the written contract that future research and writing agents (and human editors) follow from story discovery through human-approved publication.

**Current scope (this repo today)**

- Strategy, rules, discovery process, scoring, templates, and agent constraints
- Empty content folders for future research notes, drafts, and review packets
- A task-state model that preserves editorial stages

**Explicitly out of scope until the owner says otherwise**

- Deep research or drafting without owner approval of a specific candidate ID
- Article writing (except when a later task is explicitly authorized)
- WordPress or any CMS connection
- Automatic publication

Discovery-only live scanning is authorized when [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) says the discovery-stage requirements are complete; it stops at `DISCOVERED`.

---

## Purpose

The system exists so brwncltr can **consistently**:

1. **Identify** timely, worthwhile stories that fit South Asian culture, diaspora life, and related media—not merely what is trending.
2. **Research** those stories responsibly: primary sources first, viral claims checked, communities not flattened, facts not invented.
3. **Produce** strong, publish-ready drafts that an editor can review as complete packets (angle, sources, draft, SEO, social).
4. **Hand off** to WordPress as *drafts only*, with **human editorial approval required** before anything goes live.

Cultural relevance and editorial value come before traffic. Volume is not the goal. Repeatable quality is.

---

## Workflow: discovery through publication

Agents and humans move work through named states. Artifacts stay in this repo (or a future CMS) until a human approves publication.

```
DISCOVERED → RESEARCHING → DRAFTING → BLOCKED → READY_FOR_REVIEW → APPROVED
                                                      ↑
                                         (BLOCKED may return here
                                          after facts are resolved)
```

`BLOCKED` can occur from `RESEARCHING` or `DRAFTING`. It is not a failure; it is a stop when important facts cannot be verified. See [TASK_STATE.md](TASK_STATE.md).

| Stage | Who | What happens | Where it lives |
| --- | --- | --- | --- |
| **Discover** | Research agent (future) | Scan signals; score candidates; do **not** write the article | `content/state/` (candidate records) |
| **Evaluate** | Research agent + optional human | Apply [STORY_DISCOVERY.md](STORY_DISCOVERY.md) and [STORY_SCORING.md](STORY_SCORING.md); recommend pursue / pass / watch | Same |
| **Research** | Research agent | Gather sources, notes, open questions; never invent | `content/research/` |
| **Draft** | Writing agent | Fill [ARTICLE_TEMPLATE.md](ARTICLE_TEMPLATE.md) from research only | `content/drafts/` |
| **Block** | Any agent | Stop; mark `BLOCKED`; list what cannot be verified | State file + research notes |
| **Review** | Human editor | Packet moves to ready-for-review; facts, voice, fairness, legal/sensitivity | `content/ready-for-review/` |
| **Approve** | Human editor | Status `APPROVED`; only then may a future WordPress job create a **draft** (not publish) | State + CMS (not built yet) |
| **Publish** | Human only | Live on brwncltr.com | WordPress (not connected) |

No agent publishes. No agent overwrites published or in-review work without explicit owner/editor approval.

---

## Document map

| File | Use |
| --- | --- |
| [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) | Owner-input source of truth; discovery authorization gate |
| [EDITORIAL_STRATEGY.md](EDITORIAL_STRATEGY.md) | Beats, story types, what “worth covering” means |
| [STORY_DISCOVERY.md](STORY_DISCOVERY.md) | How future agents find and evaluate candidates (no live ideas in this file) |
| [STORY_SCORING.md](STORY_SCORING.md) | Qualitative scores; no invented traffic metrics |
| [EDITORIAL_RULES.md](EDITORIAL_RULES.md) | Non-negotiable accuracy, sourcing, and cultural care |
| [ARTICLE_TEMPLATE.md](ARTICLE_TEMPLATE.md) | Required fields for every draft packet |
| [AGENTS.md](AGENTS.md) | Operating rules for autonomous agents |
| [TASK_STATE.md](TASK_STATE.md) | States, file conventions, what each artifact must contain |

---

## Content directories

| Path | Purpose |
| --- | --- |
| `content/research/` | Source lists, notes, verification status—**not** finished articles |
| `content/drafts/` | In-progress packets using the article template |
| `content/ready-for-review/` | Complete packets waiting for a human |
| `content/state/` | Task records (`DISCOVERED` … `APPROVED`) |

Each directory is git-tracked via `.gitkeep` until real work exists.

---

## What this system does not do yet

- This repo does not itself contain story slates; a Grok Bot may write `DISCOVERED` candidates only when the brief authorizes discovery-only.
- It does not deep-research or write articles until the owner approves a candidate ID.
- It does not talk to WordPress.
- It does not invent search volume, traffic, or SEO rankings.

When a Grok Bot (or any agent) runs discovery, [EDITORIAL_BRIEF.md](EDITORIAL_BRIEF.md) is the owner-input source of truth. A discovery-only run may proceed when that brief’s **discovery-stage** requirements are complete; it must stop at `DISCOVERED`. Drafting-stage TODOs are not discovery blockers. See [STORY_DISCOVERY.md](STORY_DISCOVERY.md).
