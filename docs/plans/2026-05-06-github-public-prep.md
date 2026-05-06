# EVA GitHub Public Release Preparation Plan

> For Hermes: this is an audit-first, finding-traceable public-release/readiness plan for `stefan-mcf/eva`. The repository is already PUBLIC. Do not change repository visibility. Do not publish package releases. Commit/push only after operator approval or an explicit execution request.

**Goal:** Bring the already-public EVA repository into a polished, discoverable, exact-SHA-verified public GitHub state.
**Architecture/Product stance:** EVA is a proposal-only evidence and verification layer for agent runtime observability, currently Hermes-first and framework-agnostic in design.
**Tech Stack:** Python 3.10+, standard-library runtime, setuptools package metadata, pytest, Ruff, GitHub Actions CI.
**Execution Rule:** Visibility is already public; treat future publication work as polish and safety hardening. Do not publish packages/releases or broaden integrations without a separate gate.

---

## Audit Evidence Summary

Current repo state:
- Path: local EVA checkout
- Branch: `main`
- Local state at audit time: `main...origin/main [ahead 1]`
- Local HEAD: `7f5cda8 fix: harden EVA evidence remediation scanners`
- Remote: `https://github.com/stefan-mcf/eva.git`
- GitHub repo: `stefan-mcf/eva`
- Visibility: `PUBLIC`
- Default branch: `main`
- Description: `EVA: Evidence and Verification Agent - agent system observability`
- GitHub topics at audit start: `[]`
- Tracked files: 46
- Top-level public surface includes: README, LICENSE, CHANGELOG, CONTRIBUTING, SECURITY, `.github/workflows/ci.yml`, docs, examples, adapters, source, tests.
- Approximate repository composition from fallback line scan: Python 17 files / 2589 lines; Markdown 19 files / 1468 lines; JSON 3 files / 209 lines; TOML 1 file / 52 lines; YAML 2 files / 38 lines.

Verification run during audit:
- `PYTHONPATH=src python3 scripts/public_readiness_check.py`: PASS, with package build check skipped locally because `build` module was not installed in the active environment.
- `PYTHONPATH=src python3 -m pytest -q`: PASS, 19 tests.
- `PYTHONPATH=src python3 -m ruff check .`: PASS.
- `PYTHONPATH=src python3 -m compileall -q src tests`: PASS.
- Privacy grep found only documented/public examples, ignore rules, scanner code patterns, and safety documentation; no live secrets were printed or identified.
- Large object scan: no tracked blobs over 1 MiB.
- Binary tracked-file scan: no tracked binary/image/archive/SQLite/PDF/Zip files.
- Risk inventory: ignored cache files were present only from local verification; tracked risk-like hit was `examples/minimal-profiles/example-profile/memory.md`, an intentional synthetic example.
- `.gitattributes`: missing.
- Dependency license inventory: `pip-licenses` unavailable locally; runtime dependencies are empty in `pyproject.toml`.

Audit findings:

- **F-01: GitHub repository topics are missing**
  - Severity: medium
  - Evidence: `gh repo view stefan-mcf/eva --json repositoryTopics` returned `repositoryTopics: null`; direct topics API returned `{"names":[]}`.
  - Public-release impact: The public repo is less discoverable and does not communicate its domain (`agent-observability`, `verification`, `python`, etc.) through GitHub metadata.
  - Required remediation: Add concise, accurate GitHub topics and verify through the topics API.
  - Plan mapping: Tranche 1

- **F-02: Local public-readiness commit is not pushed to the public remote**
  - Severity: high
  - Evidence: `git status --short --branch` showed `main...origin/main [ahead 1]`; local HEAD `7f5cda8`, remote `origin/main` still at `1b8032d` at audit start.
  - Public-release impact: GitHub visitors do not yet see the latest scanner hardening and verification improvements, so the public surface lags behind the validated local state.
  - Required remediation: Push the validated local commit after final review, then verify remote `main` equals local `HEAD` and CI/check-runs pass for that exact SHA.
  - Plan mapping: Tranche 2

- **F-03: `.gitattributes` is missing**
  - Severity: polish
  - Evidence: `test -f .gitattributes || echo 'missing .gitattributes'` printed `missing .gitattributes`; `git ls-files --eol` showed LF-normalized working files but no declared attributes.
  - Public-release impact: Cross-platform line-ending behavior is currently implicit rather than documented/enforced.
  - Required remediation: Add a small `.gitattributes` file with text normalization and LF rules for Python, Markdown, YAML, JSON, TOML, and shell-like files.
  - Plan mapping: Tranche 3

- **F-04: Package build readiness is CI-covered but not locally available in the active environment**
  - Severity: polish
  - Evidence: `scripts/public_readiness_check.py` printed `SKIP package build check: build module not installed`; CI installs `build` and README documents `python3 -m build` / `twine check`.
  - Public-release impact: Local public-readiness output can look incomplete for contributors who have not installed dev extras.
  - Required remediation: Either document `python3 -m pip install -e '.[dev]'` as the preferred dev setup before readiness checks or make the readiness script message point to the dev extra.
  - Plan mapping: Tranche 3

- **F-05: Dependency-license inventory tooling was unavailable during audit**
  - Severity: polish
  - Evidence: `pip-licenses unavailable`; `pyproject.toml` currently declares `dependencies = []`.
  - Public-release impact: Low risk now because runtime dependencies are empty, but future dependencies need an explicit inventory path.
  - Required remediation: Document that dependency-license inventory is not required while runtime dependencies are empty, and add the command to release-readiness docs for future dependencies.
  - Plan mapping: Tranche 3

- **F-06: Synthetic example memory file can trigger generic artifact-risk scanners**
  - Severity: polish
  - Evidence: risk inventory flagged tracked `examples/minimal-profiles/example-profile/memory.md` because of the word `memory`; README says examples are synthetic and generic.
  - Public-release impact: Not a blocker, but future auditors may confuse it with live runtime memory unless the example is clearly named/documented.
  - Required remediation: Keep it only if docs continue to identify it as synthetic, or rename to `example-memory.md` and update references if recurring scanner noise appears.
  - Plan mapping: Tranche 4

---

## Definition of Done

This plan is complete when:
- GitHub topics are accurate and verified through GitHub API.
- Local `main` and remote `origin/main` match at the exact validated SHA.
- CI succeeds for that exact pushed SHA.
- `.gitattributes` and local dev/readiness docs are polished or explicitly deferred.
- Privacy/artifact scans pass with no live runtime state, secrets, generated vault artifacts, or private paths in tracked files.
- Any remaining findings are documented as accepted polish items.

---

## Tranche 1 — Repository Metadata and GitHub Topics

**Findings addressed:** F-01

**Objective:** Make the already-public GitHub repository discoverable and accurately classified.

**Files / external surfaces:**
- External GitHub metadata: repository topics for `stefan-mcf/eva`.

**Tasks:**
1. Add topics such as:
   - `agent-observability`
   - `ai-agents`
   - `verification`
   - `evidence`
   - `operator-tools`
   - `hermes-agent`
   - `python`
   - `cli`
2. Verify with the topics API.
3. Confirm the repo description still matches the README positioning.

**Acceptance Criteria:**
- GitHub topics API returns the approved topic list.
- Description remains accurate and not overclaimed.

**Verification:**
```bash
gh api repos/stefan-mcf/eva/topics \
  -H 'Accept: application/vnd.github+json'
gh repo view stefan-mcf/eva \
  --json nameWithOwner,description,repositoryTopics,visibility,url
```

---

## Tranche 2 — Push Validated Local Remediation Commit and Verify Exact SHA

**Findings addressed:** F-02

**Objective:** Bring the public remote up to the validated local state.

**Files / external surfaces:**
- Remote branch: `origin/main`
- Existing local commit: `7f5cda8 fix: harden EVA evidence remediation scanners`

**Tasks:**
1. Re-run local gates.
2. Push `main` to origin.
3. Verify local `HEAD` equals GitHub `refs/heads/main`.
4. Poll/check CI for the pushed SHA.
5. Verify attribution maps to `stefan-mcf` and noreply email.

**Acceptance Criteria:**
- `git status --short --branch` shows no ahead/behind after push.
- GitHub API remote SHA equals local `git rev-parse HEAD`.
- CI check-runs for the exact SHA complete successfully or are explicitly absent and accepted.
- Commit author/committer attribution maps to `stefan-mcf`.

**Verification:**
```bash
PYTHONPATH=src python3 scripts/public_readiness_check.py
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 -m ruff check .
PYTHONPATH=src python3 -m compileall -q src tests
git diff --check
git push origin main
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(gh api repos/stefan-mcf/eva/git/ref/heads/main --jq '.object.sha')
test "$LOCAL_SHA" = "$REMOTE_SHA"
gh api repos/stefan-mcf/eva/commits/$LOCAL_SHA \
  --jq '{sha:.sha, authorLogin:(.author.login // null), committerLogin:(.committer.login // null), authorEmail:.commit.author.email, committerEmail:.commit.committer.email}'
gh run list --repo stefan-mcf/eva --limit 20 \
  --json databaseId,status,conclusion,headSha,workflowName,url \
  --jq '.[] | select(.headSha=="'"$LOCAL_SHA"'")'
```

---

## Tranche 3 — Clone Hygiene Polish

**Findings addressed:** F-03, F-04, F-05

**Objective:** Remove small public-readiness polish gaps that affect contributors and auditors.

**Files:**
- Create: `.gitattributes`
- Modify: `README.md` or `docs/release-readiness.md`
- Optional modify: `scripts/public_readiness_check.py`

**Tasks:**
1. Add `.gitattributes` with `* text=auto` and LF rules for common text/source files.
2. Update development docs to prefer `python3 -m pip install -e '.[dev]'` before readiness checks.
3. If desired, improve the readiness script skip message to say how to install `build`.
4. Add a release-readiness note: dependency-license inventory is currently trivial because runtime dependencies are empty; run a license inventory when dependencies are added.

**Acceptance Criteria:**
- `.gitattributes` exists and `git ls-files --eol` remains clean.
- Development/readiness docs tell contributors how to install dev tooling.
- Readiness script output is clear when optional build tooling is absent.

**Verification:**
```bash
test -f .gitattributes
git ls-files --eol | sed -n '1,120p'
PYTHONPATH=src python3 scripts/public_readiness_check.py
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 -m ruff check .
```

---

## Tranche 4 — Synthetic Example Artifact Clarity

**Findings addressed:** F-06

**Objective:** Prevent future scanners/reviewers from confusing committed synthetic examples with live runtime data.

**Files:**
- Review/possibly rename: `examples/minimal-profiles/example-profile/memory.md`
- Modify if renamed: README and docs/example references.

**Tasks:**
1. Keep `memory.md` if it intentionally models a generic adapter input and docs remain clear.
2. If recurring scanner noise matters, rename to `example-memory.md` and update example docs/tests accordingly.
3. Ensure examples continue to be synthetic and no live profile/vault data appears.

**Acceptance Criteria:**
- Public docs explicitly identify examples as synthetic.
- Risk inventory has no ambiguous live-runtime hits, or the synthetic hit is documented as accepted.

**Verification:**
```bash
git grep -n -I 'synthetic\|generic\|live runtime' -- README.md docs examples
python3 scripts/public_readiness_check.py
```

---

## Final Tranche — Independent Review, Commit, Push, and Publication Gate

**Findings addressed:** all

**Objective:** Close the audit with exact-SHA proof and no hidden public-surface regressions.

**Tasks:**
1. Run the full verification bundle.
2. Inspect `git status --short --branch` and staged diff.
3. Commit only intended source/docs/metadata changes.
4. Push to `origin/main` only after operator approval.
5. Verify exact local/remote SHA, CI, topics, visibility, attribution, and contributors.
6. Stop; do not create package releases or visibility changes.

**Verification:**
```bash
PYTHONPATH=src python3 scripts/public_readiness_check.py
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 -m ruff check .
PYTHONPATH=src python3 -m compileall -q src tests
git diff --check
git status --short --branch
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(gh api repos/stefan-mcf/eva/git/ref/heads/main --jq '.object.sha')
test "$LOCAL_SHA" = "$REMOTE_SHA"
gh repo view stefan-mcf/eva --json nameWithOwner,isPrivate,visibility,url,repositoryTopics
gh api repos/stefan-mcf/eva/contributors \
  --jq '.[] | {login,contributions,html_url}'
```

Stop condition: public visibility is already enabled, but package release, PyPI publication, release tags, or further visibility/metadata changes require explicit operator approval.
