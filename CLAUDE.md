# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A self-updating research tracker: "AI in Enterprise IT" — a living catalog of specific, named ways AI is reshaping roles, teams, and operating models inside enterprise IT organizations. This is not a conventional software project: there is no package manager, test suite, or lint step. It is an agent-run research pipeline whose output is a single published Artifact, kept in sync with local JSON data files.

"Running" this project means executing the research-update routine in `AGENT_PROMPT.md`, either manually or as a scheduled cloud run.

## Commands

```bash
python3 site/build.py           # regenerate site/artifact.html from template + data files
python3 site/publish_pages.py   # mirror it to GitHub Pages (--dry-run / --force available)
```

`build.py` is the only build step. It injects three JSON snapshots into `site/template.html` and writes `site/artifact.html`, then asserts every snapshot parses and that the rubric tag vocabularies extracted from `rubric.md` look sane (13 roles, 6 dimensions). It exits non-zero on a malformed payload, so a failed build never silently produces a broken page.

There are no tests. To verify page changes without a browser, extract the inline `<script>` and run it against a DOM stub (see `data/findings_log/2026-07-28.md` for the approach used) — `node --check` alone catches syntax errors but not render-path failures.

## Architecture: how state flows

The critical constraint that shapes everything: **scheduled cloud runs cannot read this filesystem.** They recover state by fetching the published artifact and reading its embedded snapshots. Therefore the published page must always be able to fully reconstitute the pipeline.

- **`rubric.md`** — human-edited source of truth for scoring and categorization. Published **verbatim** into the artifact as `rubric-snapshot.fullText`. This verbatim embedding is load-bearing: an earlier version published only a lossy summary, which dropped the conflict-of-interest adjustment, the tier scoring notes, and the dedup guidance, so cloud runs scored against a rubric the human never approved and local edits to this file silently never took effect. **Never replace `fullText` with a summary.**
- **`data/sources.json`** — the institution allowlist across five tiers, each with `baseReliability`, scoring `note`s, and a per-institution `tracking` block (`lastSearched`, `lastYield`, `consecutiveEmptyRuns`) that makes a silently-dead source visible. Published verbatim as `sources-snapshot.fullSource`.
- **`data/opportunities.json`** — the canonical catalog (schema v2). Mirrors `opportunities-snapshot` in the artifact.
- **`data/config.json`** — `artifactUrl` (must be reused on every publish, never regenerated, or the page forks), paths, and last-run metadata.
- **`data/findings_log/YYYY-MM-DD.md`** — one append-only audit entry per run.
- **`site/template.html`** — the page: CSS, markup, and the render script, with three `__*_SNAPSHOT__` markers.
- **`site/artifact.html`** — build output; also directly editable by cloud runs that only have the published HTML (they modify the snapshot blocks in place).

Because cloud runs can't write here, local `data/` **will** drift from the published catalog over time. Reconcile by syncing the published snapshot down before doing local work — this already happened once, silently, for three weeks.

## Two published surfaces

1. **The Artifact** (`config.json.artifactUrl`) — private, and the system of record that cloud runs recover state from.
2. **GitHub Pages** — `https://sdm1130.github.io/ai-it-research-tracker/`, public, served from `sdm1130/ai-it-research-tracker` `main:/index.html`.

`site/artifact.html` is a **fragment** (starts at `<title>`; the Artifact host supplies `<!doctype>`, `<html>`, `<head>`, viewport). `site/publish_pages.py` adds that wrapper for the Pages copy — never `cp` the file across, or the site renders in quirks mode with no viewport tag.

**The GitHub repo is now the pipeline's source of truth**, not just a publishing target. It contains `AGENT_PROMPT.md`, `rubric.md`, `data/`, and `site/` alongside the built `index.html`. The scheduled routine clones it and follows `AGENT_PROMPT.md` from there, so editing `rubric.md` changes automation behavior without touching the schedule. The routine's prompt used to carry the whole process inline, which is how it silently drifted a full major version behind.

This machine's `/Users/steve/Claude/ai_research` is **not** a clone, so it will drift from the repo whenever a cloud run commits. Reconcile by pulling the repo's `data/` and `rubric.md` before doing local work.

`publish_pages.py` picks credentials in order: **git clone credentials** (the cloud-run path — the sandbox clones with push access, so *no token is needed or configured*), then `GH_TOKEN`/`GITHUB_TOKEN`, then the local `gh` CLI. It never prints a token.

Exit codes are contractual and `AGENT_PROMPT.md` §5b depends on them: **0** published or unchanged, **3** no credentials (skip, report mirror stale — not an error), **1** real failure such as an expired token (report loudly). `--check-auth` verifies credentials without writing.

**`publish_pages.py` always pushes `HEAD:main`, whatever branch you are on — and that is correct.** Scheduled cloud runs are checked out on a generated `claude/…` branch because the routine declares the repo as a git source. That branch is not a restriction and not a push target. On 2026-08-10 a run misread `--check-auth`'s branch line as a prohibition, published with `--dry-run` (which pushes nothing), and reported success; the public site went stale for four days while the Artifact stayed current. Pushing to `main` **is** the job. Never substitute `--dry-run`, and never leave the work on a branch expecting someone to merge it.

Because a `--dry-run` also exits 0, exit codes alone cannot prove the mirror moved. `--verify` compares live `origin/main:index.html` against the page the checkout builds and exits non-zero on drift; §5b requires it as the last step of every run. The general failure it guards against: the pipeline used to verify *that a command ran*, never *that the world changed*.

Because the Pages repo is public, everything embedded in the page — including the verbatim rubric and source allowlist — is public.

## Scoring model (schema v2)

Evidence is scored on **two independent axes**, because the previous single score conflated proof quality with proof volume — letting a topic reach 5 by accumulating surveys, and letting four rows from one BLS release count as four corroborations.

- `evidenceStrength` (1–5) — best study design in the trail. Government statistical series and causal/quasi-experimental work on real data score 5; multi-firm surveys score 3; forecasts score 2.
- `corroborationBreadth` (1–5) — **independent institutions**, weighted by tier diversity.
- `evidenceScore` = `round_half_up((2 × evidenceStrength + corroborationBreadth) / 3)`, then the contradiction downgrade. Only strength ≥5 with breadth ≥4 reaches 5.

**The independence rule is the one most easily got wrong:** breadth counts distinct `institution` and `studyId` values, never `len(evidence)`. Multiple rows from one parent institution count once; rows sharing a `studyId` (same institution, same release, same dataset) count once. `breadthBasis` records the counts that produced the score.

Scores must be able to go **down**. `contradictingEvidence[]` feeds a downgrade, gated at contradicting-source reliability ≥3 so a no-methodology opinion piece cannot move a well-corroborated finding. `lastRedTeamedDate` distinguishes "survived a disconfirmation search" from "nobody looked."

Other derived fields: `newestEvidenceDate` and `stale` (evidence freshness, deliberately separate from `lastUpdated`, which changes on any edit), `companySize`, symmetric `relatedTo` edges, and `metrics[]` with `studyId` provenance.

## Conventions

- An "opportunity" is a specific, nameable organizational shift, not a theme. Check `relatedTo` neighbours before creating a near-duplicate (rubric §9).
- Evidence score and maturity are always **re-derived** from the full trail on merge, never hand-set. Maturity describes how *widespread* a shift is; evidence score describes how well *proven* — they are independent.
- Summaries are **rewritten from the full trail, never appended to**, with a hard 4-paragraph cap. One had reached seven paragraphs by accretion.
- Relationships between opportunities are structured edges, never prose ("see also…" in a summary is not acceptable).
- The 12-month recency window is a hard intake filter, and separately governs archiving (`status: "archived_aged_out"` → `archived[]`, never deleted).
- Every run must aim at least one search at an under-covered role. Coverage is lopsided (IT Leadership 17, Software Engineering 11, vs. Product Management 1) — close gaps with research, never with generous tagging.
- Charts encode magnitude (coverage counts, source reliability) and therefore use lightness-monotonic **sequential** ramps, not categorical hues. A categorical palette was tried and failed four of the six colour checks.
- **The page is single-theme light, by explicit request — do not add dark mode back.** There is no `prefers-color-scheme` block and no `[data-theme]` rule; `:root { color-scheme: light !important; }` is deliberate, because the Artifact host's runtime sets `documentElement.style.colorScheme` inline when its toggle is used, and author `!important` is the only thing that overrides an inline style. Drop the `!important` and the palette stays light while native scrollbars and form controls go dark.
- `favicon` (🏢) and page `<title>` stay stable across every republish.
