# EVA CLI Reference

Install the package in editable mode to expose console scripts:

```bash
python3 -m pip install -e .
```

All commands are local filesystem commands. They do not require network access or credentials for ordinary use.

## `eva-loop`

Purpose: run the full loop: scan memory, sessions, skills, configs; compile an operator profile; generate pending proposals; compile a brief; compile a checklisted remediation plan; and compile a scheduler-friendly notification summary.

Inputs:

- `--profiles-dir PATH` — profile root to scan.
- `--vault PATH` — EVA vault path.
- `--days N` — optional session scan window.
- `--json` — print JSON bundle instead of brief markdown.
- `--no-write` — strict dry-run.

Outputs:

- stdout: brief markdown or JSON bundle.
- write mode: vault artifacts under `context/`, `proposals/`, `briefs/`, `plans/`, and `health/`.

Read/write behavior: reads profile stores and optional settings. Writes only to the vault unless `--no-write` is set.

Example:

```bash
eva-loop --profiles-dir /path/to/profiles --vault /path/to/eva-vault
```

Expected output shape: a human brief with scanner summaries, or a JSON object with top-level keys `memory`, `sessions`, `skills`, `configs`, `operator_profile`, `proposal_summary`, and `remediation_plan`.

## `eva-scan-memory`

Purpose: scan profile memory-like files for contradictions, duplicates, stale references, and topic distribution.

Inputs: a profile root path argument.

Outputs: JSON scanner result on stdout. In library use, evidence may be passed to the loop bundle.

Read/write behavior: reads profile files; does not modify source profiles.

Example:

```bash
eva-scan-memory /path/to/profiles
```

## `eva-scan-sessions`

Purpose: inspect durable session SQLite stores for correction language, repeated failures, and skill patch signals.

Inputs: a profile root path and optional scanner parameters exposed by the module.

Outputs: JSON scanner result on stdout.

Read/write behavior: reads SQLite session stores; loop write mode may persist derived evidence to the vault.

Example:

```bash
eva-scan-sessions /path/to/profiles
```

## `eva-scan-skills`

Purpose: inventory skills and identify oversized, stale, duplicate, or frequently patched skills.

Inputs: a profile root path.

Outputs: JSON scanner result on stdout.

Read/write behavior: reads skill files; does not patch skills.

Example:

```bash
eva-scan-skills /path/to/profiles
```

## `eva-scan-configs`

Purpose: scan profile configuration files for drift across related profile groups.

Inputs: a profile root path.

Outputs: JSON scanner result on stdout.

Read/write behavior: reads configuration files; does not edit them.

Example:

```bash
eva-scan-configs /path/to/profiles
```

## `eva-compile-profile`

Purpose: compile an operator profile from a scan bundle.

Inputs: a scan bundle JSON file or module-specific input supported by the current implementation.

Outputs: JSON and/or Markdown operator profile data.

Read/write behavior: when used through `eva-loop`, writes only to the configured vault context directory in write mode.

Example through the loop:

```bash
eva-loop --profiles-dir /path/to/profiles --vault /path/to/eva-vault
```

## `eva-compile-brief`

Purpose: compile a concise human-readable brief from a scan bundle.

Inputs: path to a scan JSON file.

Outputs: Markdown brief on stdout.

Read/write behavior: reads the scan file and writes nothing by itself.

Example:

```bash
eva-compile-brief /path/to/eva-vault/briefs/latest-scan.json
```

## `eva-compile-plan`

Purpose: compile a checklisted remediation plan from an existing combined scan JSON without rerunning scanners.

Inputs:

- scan bundle JSON path.
- optional `--vault PATH` for artifact references and write mode.
- `--json` to print plan JSON.
- `--markdown` to print plan Markdown; this is the default.
- `--write` to write `plans/latest-plan.*` artifacts under `--vault`.

Outputs: remediation plan JSON or Markdown on stdout. With `--write`, writes plan artifacts only under the selected vault.

Read/write behavior: reads the scan file. Writes only to `--vault` when `--write` is supplied. `--write` requires `--vault`.

Examples:

```bash
eva-compile-plan /path/to/eva-vault/briefs/latest-scan.json --markdown
eva-compile-plan /path/to/eva-vault/briefs/latest-scan.json --json
eva-compile-plan /path/to/eva-vault/briefs/latest-scan.json --vault /path/to/eva-vault --write
```

## `eva-propose-patches`

Purpose: generate proposal records from evidence and a compiled profile.

Inputs: bundle/profile data as supported by the module or through `eva-loop`.

Outputs: proposal dictionaries or pending proposal JSON files when called by the loop in write mode.

Read/write behavior: proposal files are written only under the EVA vault proposal directory when write mode is active.

Example through the loop:

```bash
eva-loop --profiles-dir /path/to/profiles --vault /path/to/eva-vault
```

## `eva-repair`

Purpose: draft, inspect, ledger, safely apply, verify, and close out EVA repair bundles generated from proposal records. `eva-repair` does not grant approval for live memory, skill, profile config, scheduler, credential, delivery, or public-repo mutation.

Inputs:

- `--vault PATH` — EVA vault containing proposals and repair artifacts.
- `draft PROPOSAL_ID` — draft one repair bundle.
- `draft-all` — draft all pending proposal bundles and optionally write a ledger.
- `list` / `inspect` — review proposal state.
- `approve`, `reject`, `defer` — record operator proposal outcomes with `--note`.
- `apply BUNDLE_ID` — apply only policy-allowed EVA-owned generated-artifact actions.
- `verify OUTCOME_ID` — verify an apply outcome.
- `ledger` / `closeout` — render operator inbox and closeout artifacts.

Outputs: JSON or Markdown on stdout. With `--write`, writes only under `repairs/` and `review-packets/` in the selected vault, except proposal outcome commands which move proposal JSON between proposal state directories.

Read/write behavior: drafting, ledgers, review packets, and closeout reports are vault-local. Auto-apply is restricted to deterministic EVA-owned generated artifacts and review packets. Human-gated target classes remain blocked until a separate approved workflow handles them.

Examples:

```bash
eva-repair list --vault /path/to/eva-vault --json
eva-repair draft-all --vault /path/to/eva-vault --write --json
eva-repair ledger --vault /path/to/eva-vault --write --markdown
eva-repair closeout --vault /path/to/eva-vault --write --markdown
```

## Recommended dry-run smoke

```bash
tmp=$(mktemp -d)
mkdir -p "$tmp/profiles"
eva-loop --profiles-dir "$tmp/profiles" --vault "$tmp/vault" --no-write --json
 test ! -e "$tmp/vault"
```
