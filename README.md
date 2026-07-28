# AI in Enterprise IT — Research Tracker

Live site: **https://sdm1130.github.io/ai-it-research-tracker/**

A living catalog of how AI is reshaping roles, teams, and operating models inside
enterprise IT organizations. Sourced only from an allowlist of government, academic,
top-tier consulting, IT analyst and preprint institutions, restricted to material
published in the trailing 12 months.

Evidence is scored on two independent axes — **study design** and **independent
corroboration** (counted by institution, never by row) — and every finding scoring 4
or higher is actively searched for disconfirming evidence.

## Repository layout

| Path | What it is |
|---|---|
| `index.html` | The published page. GitHub Pages serves this. Build output — edit the template, not this. |
| `AGENT_PROMPT.md` | The complete research-run procedure. The scheduled routine reads this. |
| `rubric.md` | Scoring rubric — source of truth. Embedded verbatim into the published page. |
| `data/opportunities.json` | The catalog itself. |
| `data/sources.json` | Institution allowlist and per-source tracking. |
| `data/findings_log/` | One audit entry per run. |
| `site/template.html` | Page markup, CSS and render script. |
| `site/build.py` | Injects the data snapshots into the template. |
| `site/publish_pages.py` | Wraps the page as a standalone document and publishes it here. |

## Running a research update

```bash
python3 site/build.py          # regenerate the page from rubric.md + data/
python3 site/publish_pages.py  # wrap it and push to GitHub Pages
```

See `CLAUDE.md` for the architecture and the constraints that shape it.
