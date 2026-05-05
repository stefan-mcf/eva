# EVA Public-Facing Preparation Plan

> **For Hermes:** Use `subagent-driven-development` to implement this plan task-by-task. Keep EVA private until the final publication gate is explicitly approved by the operator.

**Goal:** Bring EVA from a functional private v0 into a pristine, professional, public-facing repository with comprehensive documentation, clear architecture, clean adapter boundaries, and repeatable release-readiness verification.

**Architecture:** EVA should present as a framework-agnostic evidence and verification layer with Hermes as the first adapter. The public architecture must separate core package surfaces from adapter/runtime-specific deployment notes, and it must show two professional views: (1) product/concept architecture and (2) runtime/data-flow architecture.

**Tech Stack:** Python 3.10+, standard-library runtime, pytest, Ruff, setuptools, GitHub, Markdown documentation, optional static SVG/HTML architecture diagrams.

**Execution Rule:** This plan is documentation/release-prep only. Do not make the GitHub repository public, create a release, publish a package, add external telemetry, or introduce live-mode daemon behavior unless the operator explicitly approves a later publication/deployment gate.

---

## Deep Analysis Summary

Current repo state after v0 implementation:

- Core package is functional and verified.
- Public package code is portable; defaults use `Path.home()` and environment variables.
- `--no-write` is strict and covered by tests.
- Live/private memory fixture data was removed.
- The repo is still private and should remain private until a final release gate.

Public-facing gaps found during audit:

1. **README is clean but too thin for a serious public repo.**
   - Missing architecture overview.
   - Missing quickstart with expected output.
   - Missing CLI reference for every entrypoint.
   - Missing explicit proposal-only guarantees and threat model.
   - Missing adapter/runtime boundaries.
   - Missing examples of `settings.json`, proposal JSON, and brief output.

2. **Architecture documentation needs professional structure.**
   - Current architecture exists across concept/implementation notes, but it is not normalized into a public architecture document.
   - Need two views:
     - Conceptual architecture: Evidence Sources → Scanners → Compilers → Proposal Engine → Operator Review.
     - Runtime architecture: Hermes profiles/state stores → EVA loop → vault artifacts → scheduled/manual delivery.
   - Need a clear live-mode decision record: EVA is a cold observer over durable logs by default; live tailing is optional future work, not part of v0.

3. **Adapter boundary docs need cleanup.**
   - `adapters/hermes/SOUL.md` and `PROFILE.md` still read as local/private deployment notes.
   - They mention operator-specific delivery, model choices, and Telegram home-channel phrasing.
   - They should be rewritten as public templates/examples with placeholders and an explicit note that local profile files are not committed.

4. **Concept documents contain historical/private phrasing and stale names.**
   - `concept/2026-05-05-eva-concept.md` still refers to early `optimizer` naming and operator-specific examples.
   - It can either be moved under `docs/history/` with a disclaimer or rewritten as a cleaned public design note.
   - `concept/2026-05-05-eva-implementation-plan.md` is useful as internal evidence but too operational for a pristine public front page.

5. **Repository hygiene is good but could be more explicit.**
   - No CI workflow currently exists.
   - No `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, or `LICENSE` file is present in tracked files.
   - `pyproject.toml` uses MIT metadata, but a public repo should have an actual license file.

6. **Architecture standard needs source-of-truth docs.**
   - Add a top-level `docs/architecture.md` and optionally `docs/diagrams/eva-architecture.html` or SVG.
   - Avoid relying on README alone for architecture. README should summarize and link to architecture docs.

7. **Release gate needs an executable checklist.**
   - The repo has tests and manual scans, but no single `scripts/public_readiness_check.py` or documented release checklist.
   - A professional public prep should provide repeatable local verification: lint, tests, compileall, dry-run, private-pattern scan, secret-pattern scan, package build check, and GitHub attribution check.

8. **Planning artifacts need their own visibility decision.**
   - This tranched plan is intentionally operator-facing and may contain local execution commands for the current private repo.
   - During implementation, decide whether `docs/plans/` remains private-only, is moved to `docs/history/internal/`, or is rewritten into a sanitized public roadmap before any visibility flip.

---

## Definition of Done

This plan is complete when:

- README is comprehensive, polished, and public-audience appropriate.
- Public docs explain EVA's purpose, architecture, safety model, CLI, adapter model, vault schema, and development workflow.
- Two professional architecture views exist and are linked from README.
- Adapter docs are generic templates/examples, not local deployment records.
- Historical/internal concept docs are either cleaned, moved, or clearly marked as historical/internal.
- A release-readiness checklist/script exists and passes locally, including lint, tests, compileall, strict dry-run, privacy scan, and package build checks.
- CI workflow exists for lint/tests on Python 3.10+.
- No committed file contains private live data, secrets, local absolute paths in public-facing examples, or unrelated artifacts.
- Final independent review returns PASS.
- Repo remains private until explicit publication approval.

---

## Tranche 1 — Documentation Information Architecture

**Objective:** Establish a professional docs structure so README stays readable while deeper material has stable homes.

**Files:**

- Create: `docs/architecture.md`
- Create: `docs/safety.md`
- Create: `docs/cli.md`
- Create: `docs/configuration.md`
- Create: `docs/hermes-adapter.md`
- Create: `docs/release-readiness.md`
- Create: `docs/history/README.md`
- Modify: `README.md`

**Tasks:**

1. Create `docs/` and `docs/history/` directories.
2. Define the docs map:
   - `README.md`: public landing page and quickstart.
   - `docs/architecture.md`: professional architecture source of truth.
   - `docs/safety.md`: proposal-only model, dry-run semantics, privacy model.
   - `docs/cli.md`: all commands and examples.
   - `docs/configuration.md`: env vars, settings, vault layout.
   - `docs/hermes-adapter.md`: Hermes-specific setup and constraints.
   - `docs/release-readiness.md`: publication checklist.
   - `docs/history/`: early concept notes retained with disclaimers.
3. Update README to link to all docs.
4. Add a docs status section noting EVA is pre-alpha and currently Hermes-first.

**Acceptance Criteria:**

- All new docs exist and are linked from README.
- README does not attempt to contain every detail.
- No doc link is broken.

**Verification:**

```bash
python3 - <<'PY'
from pathlib import Path
required = [
  'docs/architecture.md', 'docs/safety.md', 'docs/cli.md',
  'docs/configuration.md', 'docs/hermes-adapter.md',
  'docs/release-readiness.md', 'docs/history/README.md'
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, missing
print('docs skeleton ok')
PY
```

---

## Tranche 2 — Pristine README Rewrite

**Objective:** Turn `README.md` into a polished public landing page that explains what EVA is, why it exists, how to run it, and what safety guarantees it provides.

**Files:**

- Modify: `README.md`

**Required README structure:**

1. Title and concise tagline.
2. One-paragraph product explanation.
3. Status badge placeholders or simple status bullets.
4. Why EVA exists.
5. What EVA does.
6. What EVA does not do.
7. Architecture summary with link to `docs/architecture.md`.
8. Quickstart:
   - clone
   - install editable
   - run `eva-loop --no-write --json`
   - run with explicit profiles/vault paths
9. CLI overview with link to `docs/cli.md`.
10. Configuration overview with link to `docs/configuration.md`.
11. Safety/proposal-only model with link to `docs/safety.md`.
12. Hermes adapter note with link to `docs/hermes-adapter.md`.
13. Development commands.
14. Public release status and privacy warning.
15. License.

**Style rules:**

- Use professional, neutral language.
- Avoid local absolute paths.
- Avoid operator-specific names except package author metadata if intentionally kept.
- Avoid stale project names unless explaining generic examples.
- Avoid overclaiming live/real-time behavior.
- Be explicit that EVA mines durable logs periodically by default.

**Acceptance Criteria:**

- README is comprehensive but scannable.
- First-time reader can understand the project without reading concept docs.
- README contains no unrelated local deployment details.

**Verification:**

```bash
python3 - <<'PY'
from pathlib import Path
text = Path('README.md').read_text()
required = [
  'Quickstart', 'Architecture', 'Safety', 'Configuration',
  'Hermes adapter', 'Development', 'License'
]
missing = [s for s in required if s.lower() not in text.lower()]
assert not missing, missing
for forbidden in ['/Users/stefan', 'optimizer-vault', 'home channel']:
    assert forbidden not in text, forbidden
print('README public surface ok')
PY
```

---

## Tranche 3 — Professional Architecture Documentation

**Objective:** Document EVA's architecture to a professional standard with two canonical views and clear design decisions.

**Files:**

- Create/modify: `docs/architecture.md`
- Optional create: `docs/diagrams/eva-architecture.html`
- Optional create: `docs/diagrams/eva-runtime-flow.svg` or `.html`

**Required sections in `docs/architecture.md`:**

1. Architecture goals.
2. Non-goals.
3. Design principles:
   - proposal-only
   - read-mostly
   - evidence-backed
   - adapter-separated
   - portable by default
   - no live daemon in v0
4. Conceptual architecture:
   ```text
   Evidence Sources
     → Scanners
     → Evidence Bundle
     → Operator Profile Compiler
     → Proposal Engine
     → Brief Compiler
     → Operator Review
   ```
5. Runtime/data-flow architecture:
   ```text
   Hermes profile stores
     → eva.loop
     → eva-vault/{evidence,context,proposals,briefs,health}
     → scheduled/manual delivery
   ```
6. Module map:
   - `eva.common`
   - `eva.settings`
   - `eva.scanners.*`
   - `eva.compilers.*`
   - `eva.proposers.*`
   - `eva.loop`
7. Data contracts:
   - scan bundle schema overview
   - operator profile schema overview
   - proposal schema overview
   - vault layout
8. Adapter boundary:
   - core package expectations
   - Hermes adapter responsibilities
   - future adapters
9. Scheduling model:
   - daily/manual default
   - why no live node by default
   - future trigger layer design
10. Failure/degraded-mode behavior.
11. Security/privacy boundaries.
12. Future architecture extension points.

**Diagram requirements:**

- At least two diagrams or two diagram sections:
  - System/concept component diagram.
  - Runtime data-flow diagram.
- Must not include local/private paths or operator-specific names.
- Must use neutral labels such as `Operator`, `Agent Runtime`, `Profile Store`, `EVA Vault`.

**Acceptance Criteria:**

- Architecture can be read independently of README.
- Live-mode decision is explicitly documented.
- Architecture does not imply EVA auto-applies changes.

**Verification:**

```bash
python3 - <<'PY'
from pathlib import Path
text = Path('docs/architecture.md').read_text()
required = [
  'Conceptual architecture', 'Runtime', 'Data contracts',
  'Adapter boundary', 'proposal-only', 'no live daemon'
]
missing = [s for s in required if s.lower() not in text.lower()]
assert not missing, missing
print('architecture doc ok')
PY
```

---

## Tranche 4 — CLI, Configuration, and Safety Docs

**Objective:** Provide enough operational detail that external users can install, run, configure, and trust EVA safely.

**Files:**

- Create/modify: `docs/cli.md`
- Create/modify: `docs/configuration.md`
- Create/modify: `docs/safety.md`
- Modify: `adapters/hermes/settings.template.json` if examples need alignment

**CLI doc must cover:**

- `eva-loop`
- `eva-scan-memory`
- `eva-scan-sessions`
- `eva-scan-skills`
- `eva-scan-configs`
- `eva-compile-brief`
- `eva-compile-profile`
- `eva-propose-patches`

For each command include:

- Purpose.
- Inputs.
- Outputs.
- Read/write behavior.
- Example invocation.
- Expected output shape.

**Configuration doc must cover:**

- Environment variables:
  - `EVA_HERMES_PROFILES_DIR`
  - `EVA_PROFILE_DIR`
  - `EVA_VAULT_DIR`
- `context/settings.json` schema.
- Template settings.
- Portable defaults.
- Profile-local HOME caveat for adapter runtimes.
- Vault layout and retention guidance.

**Safety doc must cover:**

- Proposal-only invariant.
- `--no-write` invariant.
- What EVA reads.
- What EVA writes.
- What EVA never writes.
- Private-data handling.
- Secret-handling stance.
- Manual approval flow.
- Suggested pre-publication scans.

**Acceptance Criteria:**

- Docs are specific enough that a new user can run EVA without reading source.
- Safety docs make it obvious EVA is not a self-modifying agent.
- CLI docs do not overpromise exact schemas beyond current code.

**Verification:**

```bash
python3 - <<'PY'
from pathlib import Path
for path in ['docs/cli.md', 'docs/configuration.md', 'docs/safety.md']:
    text = Path(path).read_text()
    assert len(text) > 1000, f'{path} too thin'
print('cli/config/safety docs present')
PY
```

---

## Tranche 5 — Hermes Adapter Public Template Cleanup

**Objective:** Convert Hermes adapter docs from local operational notes into generic public templates with clear placeholders.

**Files:**

- Modify: `adapters/hermes/SOUL.md`
- Modify: `adapters/hermes/PROFILE.md`
- Create: `adapters/hermes/README.md`
- Modify: `docs/hermes-adapter.md`

**Tasks:**

1. Rewrite `SOUL.md` as a template profile instruction:
   - Use `Operator`, not a named person.
   - Use generic delivery language, not a specific home channel.
   - Keep proposal-only rules.
   - Keep degraded scan behavior.
2. Rewrite `PROFILE.md` as an example profile spec:
   - Use generic model guidance.
   - Avoid hardcoding one provider as the only valid option.
   - Explain tools needed by capability.
3. Add `adapters/hermes/README.md`:
   - How to create a Hermes EVA profile.
   - What files are templates vs local runtime state.
   - How to schedule a scan.
   - How to run with explicit `EVA_*` env vars.
4. Write `docs/hermes-adapter.md` as user-facing adapter docs.

**Acceptance Criteria:**

- Adapter docs are useful to someone not using the local private setup.
- No references to local chat/channel IDs or local identity.
- Adapter docs clearly separate committed templates from uncommitted local profile files.

**Verification:**

```bash
python3 - <<'PY'
from pathlib import Path
paths = ['adapters/hermes/SOUL.md', 'adapters/hermes/PROFILE.md', 'adapters/hermes/README.md', 'docs/hermes-adapter.md']
for p in paths:
    text = Path(p).read_text()
    for forbidden in ['/Users/stefan', 'home channel', 'Stefan']:
        assert forbidden not in text, f'{forbidden} in {p}'
print('hermes adapter docs generic')
PY
```

---

## Tranche 6 — Historical Concept Docs Cleanup

**Objective:** Preserve useful design history without making the public repo look messy, private, or stale.

**Files:**

- Move or modify: `concept/2026-05-05-eva-concept.md`
- Move or modify: `concept/2026-05-05-eva-implementation-plan.md`
- Create: `docs/history/README.md`
- Optional create: `docs/history/2026-05-05-eva-concept.md`
- Optional create: `docs/history/2026-05-05-eva-implementation-plan.md`

**Recommended approach:**

- Move `concept/` material into `docs/history/`.
- Add a disclaimer to each historical note:
  - It is retained for development history.
  - Current source of truth is README + `docs/architecture.md` + `docs/*`.
  - Some names/examples were early design sketches.
- Replace stale `optimizer` names with `EVA` unless the section is explicitly quoting historical context.
- Replace operator-specific wording with `operator`.
- Remove tables that render poorly on Telegram only if they are part of public docs; regular GitHub Markdown tables are fine.

**Acceptance Criteria:**

- Historical docs do not undermine the polished public narrative.
- No public-facing doc suggests the old `optimizer` name is current.
- No historical doc contains private local paths or live-data snippets.

**Verification:**

```bash
python3 - <<'PY'
from pathlib import Path
for p in Path('docs/history').glob('*.md'):
    text = p.read_text()
    assert 'Historical' in text or 'history' in text.lower(), p
print('history docs marked')
PY
```

---

## Tranche 7 — Repository Metadata, CI, and Contribution Surface

**Objective:** Add standard public repository affordances.

**Files:**

- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `.github/workflows/ci.yml`
- Modify: `pyproject.toml` if needed

**Tasks:**

1. Add MIT `LICENSE` matching `pyproject.toml`.
2. Add `CHANGELOG.md` with `Unreleased` and `0.1.0` sections.
3. Add `CONTRIBUTING.md`:
   - setup
   - tests/lint
   - docs standards
   - proposal-only invariant
4. Add `SECURITY.md`:
   - report process placeholder
   - no secrets in issues/logs
   - privacy-sensitive data policy
5. Add CI:
   - checkout
   - Python 3.10 and 3.11 or 3.10 only if minimizing scope
   - install editable
   - run Ruff
   - run pytest
   - run compileall
6. Confirm `pyproject.toml` metadata is sufficient.

**Acceptance Criteria:**

- GitHub renders repo as professionally maintained.
- CI runs locally equivalent checks.
- Contribution docs explicitly protect proposal-only behavior.

**Verification:**

```bash
python3 - <<'PY'
from pathlib import Path
required = ['LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md', '.github/workflows/ci.yml']
missing = [p for p in required if not Path(p).exists()]
assert not missing, missing
print('repo metadata ok')
PY
python3 -m ruff check .
python3 -m pytest -q
python3 -m compileall -q src tests
```

---

## Tranche 8 — Public Readiness Check Script

**Objective:** Make the release gate executable and repeatable.

**Files:**

- Create: `scripts/public_readiness_check.py`
- Modify: `docs/release-readiness.md`

**Script checks:**

1. No obvious secrets:
   - hardcoded `api_key`, `secret`, `password`, `token`, private key blocks.
2. No committed live/private data:
   - `state.db`, `MEMORY.md`, `USER.md`, `latest-brief.md`, generated vault JSON/JSONL, private fixtures.
3. No local absolute paths in package/docs except allowlisted historical notes if retained.
4. README required sections exist.
5. `--no-write` smoke test with temp profiles/vault does not create vault.
6. `ruff`, `pytest`, and `compileall` pass, or the script clearly delegates to shell commands documented in `docs/release-readiness.md`.
7. Optional GitHub checks when `gh` is authenticated:
   - repo is still private before publication gate.
   - author attribution maps correctly.
8. Package build check:
   - `python3 -m build` succeeds.
   - `python3 -m twine check dist/*` succeeds when `twine` is installed.

**Acceptance Criteria:**

- Running the script locally produces a concise PASS/FAIL report.
- Script does not require credentials for local checks.
- Script never reads or prints secret values.

**Verification:**

```bash
python3 scripts/public_readiness_check.py
```

Expected:

```text
PASS public readiness local checks
```

---

## Tranche 9 — Example Artifacts Without Private Data

**Objective:** Show users what EVA outputs look like without committing live/private profile data.

**Files:**

- Create: `examples/minimal-profiles/` or `tests/fixtures/minimal_profiles/`
- Create: `examples/example-scan.json`
- Create: `examples/example-brief.md`
- Create: `examples/example-proposal.json`
- Modify: `README.md`
- Modify: `docs/cli.md`

**Tasks:**

1. Build a tiny synthetic Hermes-like profile fixture:
   - memory file with generic synthetic entries.
   - SQLite `state.db` generated during tests or created by script; avoid committing binary DB if possible.
   - skill file with generic frontmatter.
   - config file with generic model names.
2. Add script or test helper to generate example scan artifacts.
3. Commit generated examples only if synthetic and stable.
4. Link examples from README and CLI docs.

**Acceptance Criteria:**

- No example contains real local memory, real session text, real tool output, or real credentials.
- Examples are useful enough to understand output shapes.

**Verification:**

```bash
python3 scripts/public_readiness_check.py
python3 -m pytest -q
```

---

## Tranche 10 — Final Review, Commit, Push, and Publication Gate

**Objective:** Complete public-facing preparation while keeping publication gated.

**Files:**

- All docs and scripts from prior tranches.

**Tasks:**

1. Run full local verification:
   ```bash
   python3 -m ruff check .
   python3 -m pytest -q
   python3 -m compileall -q src tests
   python3 scripts/public_readiness_check.py
   git diff --check
   ```
2. Run package smoke:
   ```bash
   python3 -m pip install -e .
   eva-loop --no-write --json
   ```
3. Run package build check:
   ```bash
   python3 -m build
   python3 -m twine check dist/*  # if twine is installed
   ```
4. Run independent reviewer with explicit public-readiness checklist.
5. Decide how to handle `docs/plans/` before publication:
   - keep private-only and remove before public visibility,
   - move to sanitized history docs, or
   - rewrite into a public roadmap with local/operator references removed.
6. Fix any blockers.
7. Commit with verified attribution.
8. Push to private `main`.
9. Verify local and remote SHA match.
10. Verify repository remains private.
11. Stop. Do not make public until explicit operator approval.

**Acceptance Criteria:**

- Independent reviewer returns PASS.
- Remote `main` equals local `HEAD`.
- Repo visibility remains private.
- Final report includes exact checks and SHA.

**Verification:**

```bash
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(HOME=/Users/stefan gh api repos/stefan-mcf/eva/git/ref/heads/main --jq '.object.sha')
test "$LOCAL_SHA" = "$REMOTE_SHA"
HOME=/Users/stefan gh repo view stefan-mcf/eva --json isPrivate,visibility,nameWithOwner
```

---

## Notes for Implementers

- Do not modify local Hermes runtime profile files under `~/.hermes/profiles/eva` as part of this public-docs plan unless a task explicitly says local smoke verification requires it.
- Do not add live scan output to the repo.
- Do not introduce a live node/daemon. Document it as a future option only.
- Preserve the core promise: EVA observes, structures, diagnoses, and proposes. It does not auto-apply.
- Keep Hermes as an adapter, not the conceptual identity of the whole project.
- If unsure whether a phrase is too local/private, replace it with neutral operator/runtime language.
