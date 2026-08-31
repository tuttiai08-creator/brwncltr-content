# Story scoring

Qualitative framework for **candidates** (discovery) and a light re-score before drafting.

**Do not invent search volume, traffic, ranking, or revenue numbers.** Do not paste fake Google/Keyword Planner data. Shareability is an editorial judgment, not a metric API.

Scores are 1–5 integers plus a short **note** (required). The note matters more than the number.

---

## Scale

| Score | Meaning |
| --- | --- |
| **1** | Poor fit or fatal weakness |
| **2** | Weak; probably pass unless a rare editorial reason |
| **3** | Acceptable; proceed only with a clear angle |
| **4** | Strong; worth research time |
| **5** | Exceptional fit; still must obey sourcing rules |

There is **no weighted total that overrides a 1** on source quality, cultural flattening risk, or “we would only rewrite.” A single disqualifying note can veto a high average.

---

## Dimensions

### Audience relevance

How clearly this serves brwncltr readers (South Asian culture/media + diaspora), including owner-priority geographies when set.

- 1: Generic internet story with a thin South Asian mention
- 3: Relevant to a real slice of the audience
- 5: Core readers would feel this is *for them*

### Timeliness

Is there a real now—or a durable reason to publish this week?

- 1: Stale, or fake urgency
- 3: Reasonable window
- 5: Clear, honest peg and we can still be useful inside the window

### Cultural relevance

Does this engage culture, identity, craft, or community **with specificity**?

- 1: Extractive or flattening
- 3: Real cultural stake
- 5: Illuminates a community, form, or practice with care

### Strength of angle

Is there a point of view or question beyond the topic noun?

- 1: “X happened” with nothing to add
- 3: Workable frame
- 5: Distinct, supportable angle other coverage missed or muddled

### Source quality

Can this be reported without invention?

- 1: Rumors, unsourced virality, or inaccessible-only sources
- 3: Decent secondary; primary possible
- 5: Strong primary path (official, on-the-record, documents, the work itself)

A **1** here generally means `pass` or `watch`, not `pursue`.

### Originality

Would we be rewriting?

- 1: National/international coverage already complete and we have no add
- 3: Room for a diaspora, regional, or craft add
- 5: Clear original reporting opportunity or a necessary correction/explainer

### Potential usefulness / shareability

Would a reader **save, send, or use** this (understand a fight, pick what to watch, learn a history, avoid a bad claim)?

- 1: Empty calories
- 3: Interesting to a niche
- 5: Genuinely useful or resonant—**without** sensationalism

This is not “will it go viral.” Outrage bait scores **low**.

### Fit with brwncltr

Beat match, story type honesty, and house sensibility (curious, specific, not tabloid).

- 1: Wrong publication
- 3: Plausible
- 5: Obviously on-strategy

---

## How to record a score

In the task state file:

```text
audience_relevance: 4 — …
timeliness: 3 — …
cultural_relevance: 4 — …
strength_of_angle: 3 — …
source_quality: 4 — …
originality: 3 — …
usefulness_shareability: 3 — …
fit_with_brwncltr: 4 — …

veto: none | source_quality | rewrite_only | flattening_risk | other: …
recommendation: pursue | watch | pass
```

Optional: `confidence: low | medium | high` reflecting how complete the signal set was—not a traffic forecast.

---

## Re-score

After research, if source quality or originality drops, **change the recommendation**. Do not draft a `pass` story to avoid wasting the outline.
