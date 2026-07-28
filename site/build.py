#!/usr/bin/env python3
"""Assemble site/artifact.html from template.html + the canonical data files.

The published page must be able to fully reconstitute the pipeline's state on its
own, because scheduled cloud runs cannot read this filesystem. So the rubric and
source allowlist are embedded VERBATIM (rubric fullText / sources fullSource), not
summarised — a lossy summary is what previously caused local rubric.md edits to
silently never reach the automation.

Usage:  python3 site/build.py
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / 'site' / 'template.html'
OUT = ROOT / 'site' / 'artifact.html'

rubric_md = (ROOT / 'rubric.md').read_text()
sources = json.loads((ROOT / 'data' / 'sources.json').read_text())
opps = json.loads((ROOT / 'data' / 'opportunities.json').read_text())

# Structured fields the renderer needs for filters, PLUS the verbatim rubric text
# so a stateless run can recover the complete human-authored rubric.
def tag_list(section_num):
    """Pull the '·'-separated tag vocabulary out of a numbered rubric.md section, so
    the published snapshot can never drift from the human-edited rubric."""
    m = re.search(rf'^## {section_num}\..*?\n(.*?)(?=\n## |\Z)', rubric_md, re.S | re.M)
    if not m:
        sys.exit(f'FATAL: rubric.md section {section_num} not found')
    for line in m.group(1).split('\n'):
        if '·' in line:
            return [t.strip() for t in line.split('·') if t.strip()]
    sys.exit(f'FATAL: no "·"-separated tag line in rubric.md section {section_num}')

role_tags = tag_list(6)
dim_tags = tag_list(7)
if len(role_tags) < 10 or len(dim_tags) < 5:
    sys.exit(f'FATAL: tag extraction looks wrong (roles={len(role_tags)}, dims={len(dim_tags)})')

rubric_snapshot = {
    "recencyWindowMonths": 12,
    "maturityLadder": ["Leading Edge/Experimental", "Emerging Practice", "Growing Adoption",
                       "Common/Mainstream", "Legacy/Declining"],
    "roleTags": role_tags,
    "dimensionTags": dim_tags,
    "companySizes": ["Large Enterprise", "Mid-Market", "SMB", "Cross-size / Unspecified"],
    "compositeFormula": "round_half_up((2 * evidenceStrength + corroborationBreadth) / 3), then apply the section 4e contradiction downgrade",
    "fullText": rubric_md,
}

sources_snapshot = {
    "tiers": {k: {"baseReliability": v["baseReliability"],
                  "institutions": [{"name": i["name"], "domains": i["domains"]} for i in v["institutions"]]}
              for k, v in sources["tiers"].items()},
    "fullSource": sources,
}

html = TEMPLATE.read_text()
for marker, payload in [
    ('__RUBRIC_SNAPSHOT__', rubric_snapshot),
    ('__SOURCES_SNAPSHOT__', sources_snapshot),
    ('__OPPORTUNITIES_SNAPSHOT__', opps),
]:
    blob = json.dumps(payload, indent=2, ensure_ascii=False)
    if '</script>' in blob:
        sys.exit(f'FATAL: {marker} payload contains </script> and would break the page')
    html = html.replace(marker, blob)

OUT.write_text(html)

# --- sanity checks ---
assert '__RUBRIC_SNAPSHOT__' not in html and '__SOURCES_SNAPSHOT__' not in html \
    and '__OPPORTUNITIES_SNAPSHOT__' not in html, 'unreplaced marker'
for sid in ('rubric-snapshot', 'sources-snapshot', 'opportunities-snapshot'):
    m = re.search(rf'<script type="application/json" id="{sid}">(.*?)</script>', html, re.S)
    assert m, f'missing {sid}'
    json.loads(m.group(1))

print(f'built {OUT}  ({OUT.stat().st_size/1024:.0f} KB)')
print(f'  roleTags       : {len(role_tags)}')
print(f'  dimensionTags  : {len(dim_tags)}')
print(f'  opportunities  : {len(opps["opportunities"])}')
print(f'  rubric fullText: {len(rubric_md)} chars embedded verbatim')
print(f'  sources        : {sum(len(t["institutions"]) for t in sources["tiers"].values())} institutions embedded verbatim')
