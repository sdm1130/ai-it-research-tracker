#!/usr/bin/env python3
"""Publish a standalone copy of the artifact to GitHub Pages.

  https://sdm1130.github.io/ai-it-research-tracker/  (repo: sdm1130/ai-it-research-tracker)

`site/artifact.html` is a FRAGMENT — it starts at <title> because the Artifact host
supplies <!doctype>, <html>, <head> and the viewport meta itself. Copying it to Pages
verbatim would render in quirks mode with no viewport tag, which breaks mobile layout.
So this script wraps it in the standalone document head the Pages copy needs.

AUTH — two paths, tried in this order:
  1. A token in GH_TOKEN or GITHUB_TOKEN -> talks to the GitHub REST API directly.
     This is the path scheduled cloud runs use; they cannot reach this machine's
     keyring. Required permission on a fine-grained PAT is exactly:
         Repository access : Only select repositories -> sdm1130/ai-it-research-tracker
         Contents          : Read and write
         Metadata          : Read-only  (GitHub adds this automatically)
     Nothing else. `main` has no branch protection or rulesets, and Pages is
     build_type=legacy on main:/ so it rebuilds automatically on push — no Pages
     write and no Actions permission needed.
  2. The `gh` CLI, using whatever credentials it already has. Local runs use this.

The token value is never printed, and never needs to pass through a chat transcript —
set it in the environment of whatever runs this.

EXIT CODES (AGENT_PROMPT.md section 5b depends on these):
  0  published, or already up to date
  3  no credentials available — caller should SKIP and report the mirror as stale
  1  a real failure (bad/expired token, missing permission, network, bad input)

Usage:
    python3 site/publish_pages.py              # publish if content changed
    python3 site/publish_pages.py --dry-run    # write ./_pages_preview.html, push nothing
    python3 site/publish_pages.py --force      # publish even if unchanged
    python3 site/publish_pages.py --check-auth # verify credentials/permissions, change nothing
"""
import base64, datetime, hashlib, json, os, pathlib, shutil, subprocess, sys, urllib.error, urllib.request

REPO = "sdm1130/ai-it-research-tracker"
TARGET = "index.html"
BRANCH = "main"
API = "https://api.github.com"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "site" / "artifact.html"

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="description" content="A living catalog of how AI is reshaping enterprise IT roles, team structures, and operating models — scored for study design and independent corroboration.">
"""
TAIL = "\n</body>\n</html>\n"

NO_CREDS = 3


# ---------------------------------------------------------------- auth plumbing
def in_target_clone():
    """True when ROOT is a git work tree whose origin is REPO.

    This is the path scheduled cloud runs take: the routine declares the repo as a
    git source, so the sandbox clones it with push credentials already attached and
    no token is needed at all. Preferred over the API precisely because there is then
    no secret to store, rotate, or have silently expire."""
    if not shutil.which("git"):
        return False
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"],
                       capture_output=True, text=True)
    if r.returncode != 0 or r.stdout.strip() != "true":
        return False
    r = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    return r.returncode == 0 and REPO.lower() in r.stdout.strip().lower()


def resolve_auth():
    """Return ('git'|'token'|'gh', value) | (None, None). Never logs the token."""
    if in_target_clone():
        return "git", None
    for var in ("GH_TOKEN", "GITHUB_TOKEN"):
        tok = os.environ.get(var, "").strip()
        if tok:
            return "token", tok
    if shutil.which("gh"):
        r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if r.returncode == 0:
            return "gh", None
    return None, None


def git(*args, check=True):
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"FATAL: git {' '.join(args)}\n{r.stderr.strip() or r.stdout.strip()}")
    return r


def git_publish(page, force):
    """Write index.html, commit the run's output, push to main."""
    target = ROOT / TARGET
    if target.exists() and target.read_text() == page and not force:
        # page unchanged, but the run may still have updated data files
        if not git("status", "--porcelain").stdout.strip():
            print("unchanged — nothing to publish (use --force to push anyway)")
            return
    target.write_text(page)

    # Stage only what a research run legitimately produces.
    for p in (TARGET, "data", "site", "rubric.md", "AGENT_PROMPT.md", "CLAUDE.md"):
        if (ROOT / p).exists():
            git("add", "--", p, check=False)
    if not git("diff", "--cached", "--name-only").stdout.strip():
        print("unchanged — nothing staged to publish")
        return

    today = datetime.date.today().isoformat()
    git("-c", "user.email=sdm1130@users.noreply.github.com", "-c", "user.name=sdm1130",
        "commit", "-m", f"Weekly update: {today}")
    r = git("push", "origin", "HEAD:" + BRANCH, check=False)
    if r.returncode != 0:
        sys.exit("FATAL: git push failed — the public mirror did NOT update.\n"
                 f"  {r.stderr.strip()}\n"
                 "  If this says authentication failed, the sandbox lost its repo credentials.")
    files = git("show", "--stat", "--oneline", "HEAD").stdout.strip().splitlines()
    print(f"published {len(page)/1024:.0f} KB to https://sdm1130.github.io/ai-it-research-tracker/")
    print(f"  auth   : git (repo clone credentials — no token involved)")
    print(f"  commit : Weekly update: {today}")
    print(f"  files  : {len(files)-1} changed")
    print("  note   : GitHub Pages takes ~1 min to rebuild.")


def _fail_http(e, path):
    body = ""
    try:
        body = json.loads(e.read().decode()).get("message", "")
    except Exception:
        pass
    if e.code == 401:
        sys.exit("FATAL: GitHub rejected the credentials (401).\n"
                 "  The token is invalid or has EXPIRED. Create a new fine-grained PAT with\n"
                 "  Contents: Read and write on " + REPO + " and update the environment.")
    if e.code == 403:
        sys.exit(f"FATAL: GitHub returned 403 for {path}.\n"
                 f"  {body}\n"
                 "  Most likely the token lacks 'Contents: Read and write', or you hit a rate limit.")
    if e.code == 404:
        sys.exit(f"FATAL: GitHub returned 404 for {path}.\n"
                 "  For a FINE-GRAINED token this usually means the token is not scoped to\n"
                 f"  {REPO} at all (GitHub returns 404, not 403, for repos a token cannot see).\n"
                 "  Check 'Repository access -> Only select repositories' includes it.")
    if e.code == 409:
        sys.exit("FATAL: 409 conflict — the file changed on GitHub since this run read it.\n"
                 "  Re-run to pick up the newer version.")
    sys.exit(f"FATAL: GitHub API {e.code} for {path}\n  {body}")


def api(mode, tok, method, path, payload=None, allow_404=False):
    """One call against the GitHub REST API, via token or the gh CLI."""
    if mode == "token":
        req = urllib.request.Request(
            API + path, method=method,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Authorization": f"Bearer {tok}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "Content-Type": "application/json",
                     "User-Agent": "ai-it-research-tracker-publisher"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode()
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            if e.code == 404 and allow_404:
                return None
            _fail_http(e, path)
        except urllib.error.URLError as e:
            sys.exit(f"FATAL: could not reach api.github.com ({e.reason})")
    else:
        args = ["gh", "api", "--method", method, path[1:] if path.startswith("/") else path]
        tmp = None
        if payload is not None:
            tmp = ROOT / ".pages_payload.json"
            tmp.write_text(json.dumps(payload))
            args += ["--input", str(tmp)]
        try:
            r = subprocess.run(args, capture_output=True, text=True)
        finally:
            if tmp:
                tmp.unlink(missing_ok=True)
        if r.returncode != 0:
            if "404" in r.stderr and allow_404:
                return None
            sys.exit(f"FATAL: gh api {method} {path} failed\n  {r.stderr.strip()}")
        return json.loads(r.stdout) if r.stdout.strip() else {}


# ---------------------------------------------------------------- page assembly
def build_page() -> str:
    frag = ARTIFACT.read_text()
    low = frag.lstrip().lower()
    if low.startswith("<!doctype") or low.startswith("<html"):
        sys.exit("FATAL: artifact.html already looks like a full document; wrapper would nest <html>.")
    if "<title" not in frag[:400].lower():
        sys.exit("FATAL: artifact.html does not start with its <title>; refusing to guess the wrapper.")
    page = HEAD + frag + TAIL
    for marker in ('id="opportunities-snapshot"', 'id="rubric-snapshot"', 'id="sources-snapshot"'):
        if marker not in page:
            sys.exit(f"FATAL: wrapped page is missing {marker}")
    if "__RUBRIC_SNAPSHOT__" in page or "__OPPORTUNITIES_SNAPSHOT__" in page:
        sys.exit("FATAL: unbuilt template markers present — run `python3 site/build.py` first.")
    return page


# ---------------------------------------------------------------- entry point
def main():
    dry = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    check_only = "--check-auth" in sys.argv

    if not ARTIFACT.exists():
        sys.exit(f"FATAL: {ARTIFACT} not found — run `python3 site/build.py` first.")

    if dry:
        page = build_page()
        out = ROOT / "_pages_preview.html"
        out.write_text(page)
        print(f"dry run — wrote {out} ({len(page)/1024:.0f} KB), pushed nothing")
        return

    mode, tok = resolve_auth()
    if mode is None:
        print("NO CREDENTIALS — skipping the GitHub Pages mirror.")
        print("  Set GH_TOKEN (fine-grained PAT, Contents: Read and write on " + REPO + "),")
        print("  or authenticate the gh CLI, then re-run.")
        print("  The Pages copy is now STALE relative to the Artifact — say so in the run report.")
        sys.exit(NO_CREDS)

    if mode == "git":
        if check_only:
            url = git("remote", "get-url", "origin").stdout.strip()
            br = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            print(f"auth mode      : git (clone credentials, no token)\n"
                  f"remote         : {url}\nbranch         : {br}\ncredentials look good.")
            return
        git_publish(build_page(), force)
        return

    if check_only:
        who = api(mode, tok, "GET", "/user", allow_404=True)
        meta = api(mode, tok, "GET", f"/repos/{REPO}/contents/{TARGET}?ref={BRANCH}", allow_404=True)
        print(f"auth mode      : {mode}")
        if who and who.get("login"):
            print(f"authenticated  : {who['login']}")
        print(f"repo read      : {'OK' if meta else 'FAILED — cannot read ' + TARGET}")
        if not meta:
            sys.exit(1)
        # Probe write access without changing anything: re-PUT identical content is
        # still a write, so instead check the permissions block the API reports.
        repo = api(mode, tok, "GET", f"/repos/{REPO}", allow_404=True) or {}
        perms = repo.get("permissions") or {}
        if perms:
            print(f"push permission: {'OK' if perms.get('push') else 'MISSING — token cannot write Contents'}")
            if not perms.get("push"):
                sys.exit(1)
        else:
            print("push permission: (not reported by this token type; a real publish will confirm)")
        print("credentials look good.")
        return

    page = build_page()
    meta = api(mode, tok, "GET", f"/repos/{REPO}/contents/{TARGET}?ref={BRANCH}", allow_404=True)
    sha = None
    if meta:
        sha = meta["sha"]
        remote = base64.b64decode(meta["content"]).decode("utf-8", "replace")
        if remote == page and not force:
            print("unchanged — nothing to publish (use --force to push anyway)")
            return

    today = datetime.date.today().isoformat()
    payload = {"message": f"Weekly update: {today}",
               "content": base64.b64encode(page.encode()).decode(),
               "branch": BRANCH}
    if sha:
        payload["sha"] = sha

    api(mode, tok, "PUT", f"/repos/{REPO}/contents/{TARGET}", payload)

    print(f"published {len(page)/1024:.0f} KB to https://sdm1130.github.io/ai-it-research-tracker/")
    print(f"  auth   : {mode}")
    print(f"  commit : Weekly update: {today}")
    print(f"  sha256 : {hashlib.sha256(page.encode()).hexdigest()[:12]}")
    print("  note   : GitHub Pages takes ~1 min to rebuild.")


if __name__ == "__main__":
    main()
