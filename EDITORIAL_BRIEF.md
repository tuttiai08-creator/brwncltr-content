# Editorial brief — brwncltr

Source of truth for Grok Bot discovery and writing agents. Bind this file together with `EDITORIAL_RULES.md`, `STORY_DISCOVERY.md`, `STORY_SCORING.md`, `ARTICLE_TEMPLATE.md`, `AGENTS.md`, and `TASK_STATE.md`.

Where a field is not owner-confirmed, agents must not fill the gap. Use only:

**TODO — OWNER INPUT REQUIRED**

This brief does not contain story ideas. Live-web discovery is authorized only under **Live-web authorization** below. Deep research and drafting still require owner approval per **Human reviewer**.

---

## Live-web authorization

Live web research is allowed for **story discovery**.

- Publicly accessible sources only.
- Do not use hacked, leaked, private, paywall-bypassed, embargoed, or access-controlled material.

---

## Publication name

brwncltr

## Website/domain

[brwncltr.com](https://brwncltr.com)

## Publication mission

South Asian culture and media publication. Consistently identify timely, worthwhile stories; research them responsibly; produce strong publish-ready drafts; eventually hand off WordPress **drafts** only after human editorial approval.

Cultural relevance and editorial value matter more than generating traffic.

## Primary audience

Confirmed at publication level only: readers of South Asian culture and media coverage, including diaspora life as an editorial area.

Specific audience definition (age, cities, platforms, subscriber vs new reader, in-region vs diaspora weight): **TODO — OWNER INPUT REQUIRED**

## Priority geographies/diasporas

- **Primary emphasis:** South Asian diaspora audiences in the United States, Canada, and United Kingdom.
- Major stories originating in South Asia may still be considered when they have **clear relevance** to diaspora readers or broader South Asian culture.
- Do **not** artificially force a diaspora angle onto a story where one does not exist.

## Priority editorial beats

Established major areas (from `EDITORIAL_STRATEGY.md`). A piece may span more than one; pick a primary beat.

- South Asian culture
- Diaspora life and identity
- Entertainment
- Music / film / television
- Business / creators / entrepreneurship
- Fashion / lifestyle (where relevant)
- Internet / current conversations
- Community stories

**First-run weighting (prioritize):**

- South Asian culture
- Diaspora life and identity
- Entertainment / music / film / television
- Creators, business, and entrepreneurship
- Internet and current conversations

Fashion / lifestyle and community stories remain in the beat catalog; they are not first-run priorities unless they clearly sit inside a prioritized beat.

## First discovery-run priorities

- Use the geographies, beat weighting, time window, volume caps, source/social rules, and human-reviewer gate in this brief.
- Existing `EDITORIAL_RULES.md` and safety rules remain controlling.
- No extra blanket topic ban for the first run (see **Do-not-cover topics**).
- Discovery output is candidates + scores + pursue/watch/pass only. Do not deep-research or draft without owner approval.

## Discovery time window

- Prioritize developments from roughly the **previous 7–14 days**.
- Evergreen stories may enter the slate **only** when there is a credible current hook.

## Story mix preferences

Story **types** in use: news, analysis, explainer, feature, list/guide, opinion. Do not disguise opinion as news.

Preferred mix per run or per week (counts or ratios): **TODO — OWNER INPUT REQUIRED**

## Candidate volume per discovery run

- Maximum **10–15** candidates per discovery run.
- Recommend no more than **5** as `PURSUE`.

## Source policy

Confirmed (`EDITORIAL_RULES.md` / `STORY_DISCOVERY.md`):

- Do not fabricate sources, quotes, facts, statistics, dates, or reactions.
- Prefer primary sources when available.
- Attribute factual claims taken from other reporting.
- Do not invent anonymous “sources say.”
- Do not scrape private groups.
- Discovery: publicly accessible sources only. Do not use hacked, leaked, private, paywall-bypassed, embargoed, or access-controlled material.
- Viral claims must be verified before they are repeated as fact.
- Do not rewrite another publication with nothing useful to add.

Named outlet allowlist / blocklist (optional refinement): **TODO — OWNER INPUT REQUIRED**

Anonymous / off-record policy beyond “do not invent”: **TODO — OWNER INPUT REQUIRED**

## Social-platform policy

**X, Instagram, TikTok, YouTube, and Reddit** are all allowed for discovery.

They may establish:

- what a person/account publicly posted
- what conversation is occurring
- possible story leads

They do **not** by themselves establish:

- that a broader factual claim is true
- that a viewpoint is representative
- that something is genuinely widespread or viral

Material claims require appropriate verification.

Private, hacked, leaked, embargoed, or access-controlled material remains out of scope.

### X

Allowed for discovery under the rules above.

### Instagram

Allowed for discovery under the rules above.

### TikTok

Allowed for discovery under the rules above.

### YouTube

Allowed for discovery under the rules above.

### Reddit

Allowed for discovery under the rules above. Public posts/threads only.

## Peer/competitor outlet policy

Other South Asian and mainstream culture/media outlets may be monitored to understand the current editorial conversation.

Do **not** simply rewrite or summarize another outlet’s reporting.

A candidate should have an independent angle, additional sourcing, useful context, original analysis, or another defensible reason for brwncltr to cover it.

Named peer list (optional): **TODO — OWNER INPUT REQUIRED**

## Do-not-cover topics

No additional blanket topic prohibition for the first discovery run.

Existing editorial and safety rules remain controlling (`EDITORIAL_RULES.md`, `AGENTS.md`).

## Handle-with-care topics

Apply heightened sourcing and human-review standards to:

- caste
- religion
- communal conflict
- crime
- accusations / allegations
- ongoing legal proceedings
- death or violence
- health claims
- politics and elections

Discovery may identify these topics. The system must **flag them as sensitive** and must **not** advance them casually. They do not move to deep research or drafting without owner approval.

## Language policy

English-first for v1.

Non-English sources may be used as **discovery signals**.

Do not rely on machine translation as the **sole** basis for a material factual claim.

Until a fuller translation policy is approved, material claims should be verifiable through an English-language source or a directly understandable primary source.

## Translation policy

Confirmed for discovery/material claims: see **Language policy**. If a translation is used, note original language and who translated when meaning is load-bearing. Do not invent translations.

Staff vs machine translation workflow for drafts: **TODO — OWNER INPUT REQUIRED**

## Embargo/leak/exclusive policy

Do not use hacked, leaked, private, embargoed, or improperly obtained material.

Never invent an exclusive, embargo, or leak. Never claim access that did not occur.

## Voice/tone

Confirmed constraints only: do not flatten South Asian communities into one culture; preserve distinctions among countries, religions, languages, diasporas, regions, and communities when relevant; do not manufacture controversy or sensationalize for clicks; distinguish reporting from interpretation.

House voice (register, humor, how celebrity is handled, India-as-default, etc.): **TODO — OWNER INPUT REQUIRED**

## Voice samples

**TODO — OWNER INPUT REQUIRED**

(URLs or files of published brwncltr pieces agents must match.)

## Archive/internal-link policy

Confirmed: do not invent published URLs. If the archive is unknown, mark `[ARCHIVE UNKNOWN]`.

How agents access the live archive (sitemap, export, CMS, URL list): **TODO — OWNER INPUT REQUIRED**

## Human reviewer

**Owner approval is required** before a discovery candidate advances to deep research or drafting.

Discovery runs stop at scored candidates (`DISCOVERED` + pursue/watch/pass). Do not start `RESEARCHING` or `DRAFTING` without that approval.

Named reviewer contact / delivery channel for draft packets: **TODO — OWNER INPUT REQUIRED**

## Publishing rule

Human review is required before publication. Agents never publish. Agents never mark `APPROVED` unless a named human has already approved in-band.

Future CMS jobs, if built, may create **WordPress drafts only** after `APPROVED`. Going live is human-only.

## CMS

Not connected. Do not build or call WordPress (or any CMS) until the owner asks.

Intended later: WordPress draft handoff after approval. Credentials, site, and field mapping: **TODO — OWNER INPUT REQUIRED**
