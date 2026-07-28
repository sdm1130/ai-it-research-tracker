# Standing Agent Instructions — AI in Enterprise IT: Research Tracker

You are running the weekly (or manually-triggered) research update for a living catalog of how AI is reshaping roles, teams, and operating models inside enterprise IT organizations. This file is self-contained — follow it exactly whether you're a scheduled cloud routine with no memory of any prior conversation, or a manual run. Read this whole file before doing anything.

## 0. Establish state

Try first: read these local files.
- `/Users/steve/Claude/ai_research/rubric.md` — scoring rubric, categories, tags (authoritative, human-edited)
- `/Users/steve/Claude/ai_research/data/sources.json` — source allowlist
- `/Users/steve/Claude/ai_research/data/opportunities.json` — current catalog
- `/Users/steve/Claude/ai_research/data/config.json` — holds `artifactUrl` and `artifactFilePath`

**If those files are not reachable** (isolated cloud sandbox with no access to this Mac), WebFetch the `artifactUrl` and recover state from the embedded snapshots. Since schema v2 those snapshots are **lossless**:

- `<script type="application/json" id="rubric-snapshot">` carries `fullText` — the complete verbatim `rubric.md`. Read it and follow it as the authoritative rubric.
- `<script type="application/json" id="sources-snapshot">` carries `fullSource` — the complete verbatim `sources.json`, including every `note` and `tracking` field.
- `<script type="application/json" id="opportunities-snapshot">` carries the full catalog.

> Historical note, do not repeat: earlier versions embedded only a *summarised* rubric — dropping the conflict-of-interest adjustment, the tier scoring notes, and the dedup guidance. Cloud runs therefore silently scored against a rubric the human had never approved, and local `rubric.md` edits never took effect. Whenever you republish, the full text must go back in.

## 1. Search — allowlist only, 12-month window only

For each institution in `sources.json`, use domain-restricted `WebSearch` (`allowed_domains` set to that institution's domains) to find new or updated publications on AI's effect on enterprise IT team structure, role design, skills, staffing models, and operating models — across the full role spectrum in rubric.md §6, not just software engineering.

Discard at intake anything: off-allowlist; published more than 12 months before today; or reliability 1 (no methodology *and* no independence).

**Priority sources.** `Census Bureau BTOS` and `MIT CISR` are flagged in `sources.json` and must be searched every run. BTOS measures *actual firm-level adoption*; the catalog is otherwise heavily weighted toward stated intentions. CISR is the one research center dedicated to exactly this topic.

**Coverage-directed search.** Before searching, compute the role × dimension coverage matrix from the current catalog. The catalog has historically over-concentrated in *IT Leadership* and *Software Engineering* while *Product Management*, *QA/Test Engineering*, *Data Engineering*, and *Help Desk/IT Support* stayed nearly empty. **Direct at least one search per run at an under-covered role.** Never close a gap by tagging generously — only by finding real evidence.

**Citation chasing.** Domain-restricted keyword search is one-hop and misses adjacent work. For the two strongest new findings each run, follow their reference lists and look for later work citing them, then check whether any of those are on the allowlist.

**Re-verification.** Once per month (or whenever `lastVerified` on an evidence row is >90 days old), re-fetch existing evidence URLs. Check for 404s, revisions, corrections, and retractions. Update `whatItShows` if the underlying publication changed; remove the row and note it in the log if it was withdrawn. A frozen citation that has since been retracted is worse than no citation.

**Source tracking.** For every institution searched, update its `tracking` block in `sources.json`: `lastSearched` = today; `lastYield` = today if a qualifying finding was admitted; otherwise increment `consecutiveEmptyRuns`. Report any source at `consecutiveEmptyRuns >= 6` in the findings log as possibly dead.

## 2. Score every candidate finding

Per `rubric.md` §3–4:

1. **Source Reliability (1–5)** for the specific publication — start from its tier's `baseReliability`, then apply every adjustment: −1 vendor-funded/COI; **preprints capped at 3** with `peerReviewed: false`; MGI/BHI with disclosed methodology → 4; analyst firms → 2 without a named methodology.
2. **Evidence Strength (1–5)** — the design of the *single strongest* study in the trail (rubric §4a). Government statistical series and causal/quasi-experimental work on real data score 5. Multi-firm surveys score 3. Forecasts and framework proposals score 2.
3. **Corroboration Breadth (1–5)** — see the independence rule below.
4. **Composite**: `evidenceScore = round_half_up((2 × evidenceStrength + corroborationBreadth) / 3)`, then apply the §4e contradiction downgrade. Store all three numbers plus `evidenceStrengthRationale` and `breadthBasis`.

### The independence rule — do not get this wrong

Breadth counts **distinct institutions**, never evidence rows.

- Assign every evidence row an `institution` (normalised parent — "BLS Occupational Outlook Handbook" and "BLS Economics Daily" are both `U.S. Bureau of Labor Statistics`) and a `studyId`.
- Rows sharing a `studyId` count once. Same institution + same publication date on the same dataset = **one study** — e.g. several Occupational Outlook Handbook pages from a single release.
- Compute `breadthBasis` = `{independentInstitutions, distinctStudies, tiersRepresented}` and derive breadth from that, never from `len(evidence)`.

This is the rule that was previously violated: five BLS rows and four HBR rows were being counted as five and four independent corroborations, manufacturing consensus that did not exist.

## 3. Red-team pass — mandatory, every run

The loop is otherwise structurally confirmation-biased: it only ever searches for material supporting what is already in the catalog.

For every opportunity with `evidenceScore >= 4`, **actively search for disconfirming evidence** — findings that the effect is absent, reversed, smaller than claimed, or explained by something other than AI. Phrase queries against the thesis ("AI hiring rebound", "no productivity gain", "agent pilot failure", "declines predate AI").

- Record what you find in `contradictingEvidence[]` with a `contradicts` field explaining precisely what it undercuts.
- Apply the §4e downgrade — **only if the contradicting source clears reliability ≥ 3**. Below that, record it and set `contested: true`, but leave the score alone.
- Set `lastRedTeamedDate` on every opportunity you red-teamed, **including those whose thesis survived**. "No contradicting evidence found" and "nobody looked" must be distinguishable.
- An opportunity may legitimately settle at a low score and stay. "Widely claimed, poorly evidenced" is a publishable finding.

## 4. Merge into the catalog — don't just append

For each finding:

1. Check whether it corroborates/extends an **existing** opportunity (rubric §9). Be conservative about near-duplicates — consult `relatedTo` edges to spot neighbours.
2. If yes: append to `evidence[]`, then **re-derive** `evidenceStrength`, `corroborationBreadth`, `evidenceScore`, and `maturity` from the full updated trail. Bump `lastUpdated`.
3. If no: create a new opportunity (schema in `opportunities.json._readme`) with `firstSeen` = `lastUpdated` = today. Only create it if founding evidence clears reliability ≥ 3 and is not a single anecdotal/vendor claim.
4. Recompute derived fields on every touched opportunity: `newestEvidenceDate` (max evidence date), `stale` (newest evidence > 6 months old), `breadthBasis`.
5. Set `companySize` per rubric §8 — the scale the *evidence* actually covers. Default `Cross-size / Unspecified`; do not infer large-enterprise from a survey that doesn't disclose it.
6. Maintain `relatedTo` as **structured, symmetric edges**. Never write "see also the related finding on X" in prose — encode the edge.
7. Archive (`status: "archived_aged_out"`, moved to `archived[]`) any opportunity whose entire evidence trail is older than 12 months.

### Summaries — rewrite, never accrete

Summaries were previously growing without bound (one reached seven paragraphs by appending a new one each run).

- `summary`: **hard cap 4 paragraphs.** When new evidence arrives, **rewrite the whole summary from the full evidence trail** — do not append a paragraph. If it no longer fits in four, the opportunity is probably two opportunities.
- `shortSummary`: exactly ~2 plain sentences, always kept in sync with `summary`.
- **Claim provenance (rubric §10):** every quantified claim in prose carries an inline `[e:<studyId>]` marker, and the same figure goes into `metrics[]` as `{name, value, unit, population, studyId}`. When evidence ages out or is retracted, its claims must be removed from the summary in the same run — the markers are what make that mechanical.

## 5. Regenerate and publish the Artifact

Take the current `site/artifact.html` (or the raw HTML you WebFetched) and modify **only** the contents of the three `<script type="application/json">` snapshot blocks:

- `opportunities-snapshot` — the updated catalog
- `rubric-snapshot` — must carry `fullText` with the complete verbatim `rubric.md`
- `sources-snapshot` — must carry `fullSource` with the complete verbatim `sources.json`

Do not rewrite the surrounding HTML, CSS, or rendering `<script>`. The page renders everything dynamically from that data — masthead counts, What's New, coverage heatmap, timeline, cards with two-axis scores, contested badges, evidence trails, filters, CSV export. The layout is a deliberate, human-reviewed choice.

Publish via the `Artifact` tool:
- Pass `config.json.artifactUrl` as `url` so the same page updates in place — **never** omit it, or you fork a duplicate page.
- Keep `favicon` and page `<title>` stable across every republish.

## 5b. Mirror to GitHub Pages — every run, local or scheduled

A public standalone copy is served at **https://sdm1130.github.io/ai-it-research-tracker/** from `sdm1130/ai-it-research-tracker` (`main` branch, root, file `index.html`).

```bash
python3 site/build.py          # regenerate site/artifact.html first
python3 site/publish_pages.py  # wrap + push
```

Run this on **every** run, including one that found nothing new — the mirror may be several runs behind. The script is a no-op when content is unchanged, so it is always safe to call.

`site/artifact.html` is a **fragment** — it starts at `<title>` because the Artifact host supplies `<!doctype>`, `<html>`, `<head>` and the viewport meta. `publish_pages.py` adds that wrapper; copying the file across verbatim would render in quirks mode with no viewport tag and break mobile layout. **Never `cp` it directly.**

### Credentials

The script finds credentials in this order, and never prints a token value:

1. **Git clone credentials** — when the working directory is a clone of `sdm1130/ai-it-research-tracker`. **This is the path scheduled cloud runs take:** the routine declares the repo as a git source, so the sandbox clones it with push credentials already attached. **No token is required or configured** — do not add one. It commits `index.html` plus `data/`, `site/`, `rubric.md` and `AGENT_PROMPT.md`, then pushes to `main`.
2. **`GH_TOKEN` / `GITHUB_TOKEN`** — a fine-grained PAT (`Contents: Read and write` on that one repo). Only needed if you are running somewhere that is neither a clone nor `gh`-authenticated.
3. **The `gh` CLI** — used by local runs on Steve's machine, which is not a clone.

### Act on the exit code — do not ignore it

| Code | Meaning | What you must do |
|---|---|---|
| **0** | Published, or already up to date | Nothing. Note it in the run report. |
| **3** | No credentials found | **Not an error.** Skip the mirror and state plainly in your §7 report that the GitHub Pages copy is now **stale** and needs a run with credentials to catch up. |
| **1** | Real failure — expired/invalid token, missing permission, network | **Report it loudly and prominently in §7.** A token expiry is the likeliest cause and it will otherwise fail silently every week while the public site quietly rots. Quote the script's error message verbatim so the fix is obvious. |

Never report the mirror as updated unless the script exited 0. `python3 site/publish_pages.py --check-auth` verifies credentials and permissions without changing anything.

## 6. Write the audit trail

If local files are reachable, append a dated entry to `data/findings_log/YYYY-MM-DD.md` covering: sources searched and how many yielded; findings passing intake; new vs updated vs archived opportunities; **red-team results (what was challenged, what survived, what was downgraded)**; score movements with before→after; coverage gaps still open; any source at `consecutiveEmptyRuns >= 6`. Update `data/opportunities.json`, `data/sources.json` tracking blocks, and `config.json` (`lastRunDate`, `lastRunStatus`).

**If local files are NOT reachable**, the published artifact is the only record — say so explicitly in your report so the human knows the local mirror has drifted and needs a sync.

## 7. Report back

End with a short plain-language summary: what's new, what changed score and why, what the red-team pass found, and the Artifact URL. If this is a scheduled/unattended run, this is what the user sees when they next check in — make it useful standalone, never a reference to "as discussed."

---

**Note for whoever wires up the recurring job:** bake the Artifact URL directly into the recurring prompt text (not just `config.json`) so a stateless cloud run has it without needing local file access.
