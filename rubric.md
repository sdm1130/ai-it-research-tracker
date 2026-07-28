# Scoring & Categorization Rubric

Source of truth for how the AI-in-Enterprise-IT research agent evaluates every source and every "opportunity" (a specific, named way AI is reshaping an enterprise IT role, team structure, or operating model). `AGENT_PROMPT.md` references this file every run.

**This file is published verbatim into the artifact** (`<script type="application/json" id="rubric-snapshot">` carries a `fullText` field containing this document). That is what makes edits here actually reach scheduled cloud runs, which cannot read this filesystem. Earlier versions embedded only a lossy summary, so local edits to this file silently never took effect. If you change this file, the next publish propagates it.

---

## 1. Source allowlist & tiers

Only material from institutions on `data/sources.json` is eligible. Five tiers:

1. **Government & intergovernmental** — BLS, Census Bureau, Federal Reserve (Board + regional), GAO, OECD, WEF, EU statistical agencies
2. **Academic & research institutions** — MIT (Sloan, CSAIL, IDE, CISR), Stanford HAI, Wharton, HBS, NBER, Brookings
3. **Top-tier management consulting** — McKinsey (incl. MGI), BCG (incl. BHI), Bain, Deloitte, PwC, EY, Accenture Research
4. **IT analyst firms** — Gartner, Forrester, IDC. In scope, scored lower by default for commercial bias unless methodology is explicitly disclosed.
5. **Preprint servers** — SSRN, arXiv (econ.GN, cs.CY). Earliest signal in this literature, but **not peer-reviewed**; see the reliability ceiling in §3.

Anything not on the allowlist is out — no general news, no vendor blogs, no LinkedIn posts, no press releases, regardless of how the search results look.

## 2. Recency window (hard filter)

Only publications **dated within the trailing 12 months** (rolling, computed against today's date each run) are eligible to enter the catalog. Hard intake filter, not a soft downweight.

An opportunity stays **active** while at least one supporting finding is within the window. When an opportunity's *entire* evidence trail ages out, it moves to "Archived — aged out" (never deleted).

**Evidence freshness** is tracked separately from edit recency. Every opportunity carries a derived `newestEvidenceDate` (the max `publishedDate` across its trail). An opportunity whose newest evidence is **older than 6 months** is flagged `stale: true` — it is still active, but the page marks it, because "last updated" changes on any edit and otherwise disguises a topic that nobody has corroborated in half a year.

## 3. Source Reliability Score (1–5, per individual publication)

| Score | Criteria |
|---|---|
| **5** | Government/central-bank primary data, or peer-reviewed academic research, with disclosed methodology & sample |
| **4** | University research center report (MIT Sloan/CISR, Stanford HAI) or flagship consulting institute research (MGI, BHI) with disclosed methodology |
| **3** | Standard top-tier consulting publication, or an analyst-firm research note with a named, described methodology |
| **2** | Analyst commentary/blog with no disclosed methodology, or a vendor's own case study about its own product |
| **1** | No disclosed methodology and no independence — **excluded entirely** |

**Adjustments (apply all that fit; floor of 1):**
- **−1 if vendor-funded** or the publishing institution has a disclosed conflict of interest (e.g. a cloud provider publishing ROI research on its own AI tools).
- **Preprint ceiling: cap at 3** for anything on SSRN/arXiv that has not yet been peer-reviewed, *regardless of study quality*. Record `peerReviewed: false`. If a later run finds the peer-reviewed version, replace the preprint URL and lift the cap.
- **MGI / BCG Henderson Institute** publications with disclosed methodology score **4**, not the consulting tier default of 3.
- **Analyst firms drop to 2** if the piece is commentary/opinion without a named, described methodology (survey size, panel composition).

## 4. Evidence assessment — TWO axes, not one

The previous single 1–5 "evidence" score conflated *how good the proof is* with *how much of it there is*. That let a topic reach 5 by accumulating ten surveys, and it let four rows from a single BLS release masquerade as four independent corroborations. Both axes below are now scored separately, and the headline number is derived from them.

### 4a. Evidence Strength (1–5) — the best study design in the trail

Judged on the **single strongest** piece of evidence, not the average.

| Score | Criteria |
|---|---|
| **5** | Causal or quasi-experimental identification on real organizational/administrative data (RCT, matched event study, diff-in-diff), **or** an official government statistical series / occupational projection from a national statistical agency |
| **4** | Rigorous non-causal empirical work on real observed data with disclosed methodology (government audit, large-scale job-postings analysis, academic descriptive study), **or** a documented large-enterprise case study with quantified outcomes |
| **3** | Multi-firm survey with disclosed sample size, population, and method |
| **2** | Expert point-of-view, forecast, or framework proposal without empirical backing |
| **1** | Single anecdote or vendor self-claim — **excluded** |

### 4b. Corroboration Breadth (1–5) — how many *independent* sources agree

| Score | Criteria |
|---|---|
| **5** | 5+ independent institutions, spanning 3+ source tiers |
| **4** | 3–4 independent institutions, spanning 2+ tiers |
| **3** | 2 independent institutions |
| **2** | 1 institution, but 2+ genuinely separate studies |
| **1** | A single study |

**Caps:** 3–4 institutions all within *one* tier caps breadth at 3. 5+ institutions spanning only 1–2 tiers caps breadth at 4. Tier diversity matters because consulting firms cite each other and analyst firms share survey panels.

### 4c. The independence rule (this is the one that was being violated)

Breadth counts **distinct institutions**, never evidence rows.

- Multiple rows from the same parent institution count **once** (BLS ×5 = 1 institution; HBR ×4 = 1; Gartner ×3 = 1).
- Rows sharing a `studyId` count as **one study** even across outlets — a single McKinsey survey written up three times is one study, not three.
- Two publications from one institution released the same day on the same dataset (e.g. several Occupational Outlook Handbook pages from one release) are **one study**. Give them a shared `studyId`.
- Every evidence row carries `institution` and `studyId`; breadth is computed from distinct values, not array length.

### 4d. Derived composite — `evidenceScore`

Study design is weighted 2:1 over corroboration, because ten weak studies agreeing is still weak proof:

```
evidenceScore = round_half_up( (2 × evidenceStrength + corroborationBreadth) / 3 )
```

Then apply the contradiction downgrade from §4e. **Only `evidenceStrength ≥ 5` with `corroborationBreadth ≥ 4` can reach a 5.** Both component axes are stored and displayed alongside the composite so the tradeoff stays visible — a lone rigorous causal study (strength 5, breadth 1 → composite 4) reads very differently from a pile of agreeing surveys (strength 3, breadth 5 → composite 4), and the page must show which one you're looking at.

### 4e. Contradicting evidence & the downgrade path

The catalog previously had **no way to score down** — evidence only ever accumulated, so scores ratcheted upward permanently. Every opportunity now carries `contradictingEvidence[]`, populated by the deliberate red-team pass in `AGENT_PROMPT.md`.

**Downgrade threshold.** Contradicting evidence only moves the score if it clears **Source Reliability ≥ 3**. Below that it is still recorded and still sets `contested: true`, but it does not change the number — otherwise a single no-methodology opinion piece could knock a point off an eight-institution finding, which would just reintroduce the old problem with the sign flipped.

- Contradicting evidence, reliability ≥ 3, `evidenceStrength` **≥** the supporting trail's: **−2** (floor 1), `contested: true`
- Contradicting evidence, reliability ≥ 3, strength **<** the supporting trail's: **−1**, `contested: true`
- Contradicting evidence, reliability < 3: **no score change**, `contested: true`
- An opportunity may legitimately settle at a low score and stay in the catalog. "Widely claimed, poorly evidenced" is a finding worth publishing, not a reason to delete.

A finding with no contradicting evidence *because nobody looked* is not the same as one that survived a search. Track `lastRedTeamedDate` per opportunity so the difference is visible.

## 5. Maturity / Adoption ladder

1. **Leading Edge / Experimental** — pilots at a handful of orgs, no proven ROI
2. **Emerging Practice** — early adopters, first case studies, methodology still forming
3. **Growing Adoption** — multiple industry surveys show rising uptake, benchmarks emerging
4. **Common / Mainstream** — majority adoption among comparable enterprises, established playbooks
5. **Legacy / Declining** — being phased out or superseded as a direct result of AI-driven change

Maturity is re-derived from the full trail each run. It describes **how widespread** the shift is; `evidenceScore` describes **how well-proven** it is. They are independent — a mainstream practice can be poorly evidenced.

Note for sorting: *Legacy/Declining* is a terminal state, not the top of the ladder. It sorts adjacent to its adoption peak, never above *Common/Mainstream*.

## 6. Role tags (multi-select — tag every role materially affected)

Product Management · Program/Project Management · Software Engineering · Data Engineering · Data Science/ML Engineering · Cloud/Platform Engineering · Network Engineering · Help Desk/IT Support · IT Operations/SRE · Enterprise/Solution Architecture · QA/Test Engineering · Security/InfoSec · IT Leadership/Org Design & Strategy

**Coverage discipline:** the catalog has historically over-concentrated in *IT Leadership* and *Software Engineering* while leaving *Product Management*, *QA/Test Engineering*, *Data Engineering*, and *Help Desk/IT Support* nearly empty. Each run must consult the coverage heatmap and direct at least one search at an under-covered role. Do not tag a role unless the evidence genuinely speaks to it — the fix for thin coverage is new research, never generous tagging.

## 7. Org-design dimension tags (multi-select)

Team Structure & Span of Control · Operating Model & Governance · Skills & Upskilling Pathways · Workforce Planning & Sizing · Role Redesign/Job Architecture · AI Tooling & Enablement

## 8. Company-size applicability (one per opportunity)

Records the enterprise scale the *evidence* actually covers, so a reader can tell whether a finding transfers to their org:

**Large Enterprise** · **Mid-Market** · **SMB** · **Cross-size / Unspecified**

Default to *Cross-size / Unspecified* unless the underlying sample is explicitly scoped. Most consulting surveys of "global executives" are large-enterprise-weighted — say so when the methodology discloses it, and don't infer it when it doesn't.

## 9. What counts as a distinct "opportunity"

A specific, nameable shift — e.g. "AI code-review copilots collapsing junior/senior review cycles" or "Help desk tiered-support models flattening as AI resolves Tier-1 tickets" — not a broad theme like "AI and IT."

Before creating anything new, check whether the finding corroborates or extends an existing opportunity. Two findings merit separate entries only if the underlying organizational change is genuinely different, not merely a different source restating the same shift.

**Relationships are structured, not prose.** Opportunities link to each other via `relatedTo`, `contradicts`, and `causedBy` arrays of opportunity ids. Writing "see also the related finding on X" inside a summary is not acceptable — encode the edge so the page can render it and so near-duplicates surface mechanically.

## 10. Claim provenance

Every quantified claim in a `summary` or `shortSummary` must be traceable. Numbers cited in prose carry an inline marker `[e:<studyId>]` naming the evidence row they came from, and the same figures are extracted into the opportunity's `metrics[]` array (`{name, value, unit, population, studyId}`) so they can be charted across sources and over time.

A claim whose supporting evidence later ages out or is retracted must be removed from the summary in the same run — provenance markers are what make that mechanical rather than a re-read of every paragraph.
