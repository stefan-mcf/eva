# Release Readiness

This checklist is the publication gate for EVA. Run it before making the repository public or tagging a release.

## Local verification

Install the development extras first so local readiness checks can run the same package/build tooling documented for CI and release review:

```bash
python3 -m pip install -e '.[dev]'
python3 -m ruff check .
python3 -m pytest -q
python3 -m compileall -q src tests
python3 scripts/public_readiness_check.py
git diff --check
```

## Package smoke

```bash
python3 -m pip install -e .
eva-loop --no-write --json
```

The dry-run command must not create a vault.

## Package build

```bash
python3 -m pip install build twine
rm -rf dist build *.egg-info src/*.egg-info
python3 -m build
python3 -m twine check dist/*
```

## Dependency license inventory

EVA currently has no runtime dependencies, so the runtime dependency-license inventory is empty. If runtime dependencies are added later, install a license inventory tool and record the result before tagging a release:

```bash
python3 -m pip install pip-licenses
python3 -m piplicenses --format=markdown --with-urls
```

## Privacy and public-surface checks

- No generated vault artifacts are committed.
- No live memory files, session databases, profile configs, credentials, or local scheduler IDs are committed.
- Public examples are synthetic.
- Public docs use generic operator/runtime language.
- Local absolute paths are absent from public-facing files.
- Historical docs are clearly marked.

## GitHub checks

Before publishing:

```bash
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(gh api repos/OWNER/REPO/git/ref/heads/main --jq .object.sha)
test "$LOCAL_SHA" = "$REMOTE_SHA"
gh api repos/OWNER/REPO/commits/main --jq '{sha:.sha, authorLogin:(.author.login // null), committerLogin:(.committer.login // null)}'
gh api repos/OWNER/REPO/contributors --jq '.[] | {login, contributions}'
```

After making the repository public, verify visibility and CI against the exact pushed SHA, not merely a recent green run.

## Expected readiness script output

```text
PASS public readiness local checks
```

Any failure should be treated as a release blocker until fixed or explicitly documented as a false positive.
