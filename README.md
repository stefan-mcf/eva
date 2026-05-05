# EVA — Evidence & Verification Agent

> A proposal-only evidence layer for understanding and improving agent runtimes.

EVA observes durable records from an agent system, turns them into structured evidence, and drafts reviewable optimization proposals for an operator. It is framework-agnostic at the concept layer and Hermes-first at the adapter layer. EVA does not act as an autonomous fixer: it reads, summarizes, diagnoses, proposes, and leaves changes to a human or explicitly approved workflow.

## Status

- Project status: pre-alpha, functional v0.
- Runtime support: Hermes adapter first; additional adapters are future work.
- Runtime dependencies: Python standard library only.
- Development tools: pytest, Ruff, setuptools/build.
- Safety stance: read-mostly and proposal-only.

## Why EVA exists

Agent systems accumulate operational knowledge in memories, transcripts, configuration files, skills, logs, and repeated operator corrections. Those records are valuable, but they are usually scattered across runtime-specific storage. EVA provides a lightweight evidence layer that periodically mines durable state and answers questions such as:

- Which instructions or memories contradict each other?
- Which tools or workflows fail repeatedly?
- Which skills or profile files are stale, oversized, or duplicated?
- Which configuration choices drift across related profiles?
- Which optimization proposals are supported by repeat evidence rather than one-off noise?

## What EVA does

EVA currently provides a Hermes adapter that can:

- scan profile memory files for contradictions, stale references, duplicates, and topic distribution;
- scan session SQLite stores for correction language, repeated tool failures, and skill patch signals;
- scan skills for oversized files, staleness candidates, duplicate names, and patch-frequency hints;
- scan profile configs for model, delegation, and tooling drift;
- compile an operator profile from evidence;
- draft pending optimization proposals for manual approval;
- compile a concise operator brief; and
- run the full loop from a CLI command or scheduler.

## What EVA does not do

EVA does **not**:

- automatically edit memories, skills, configs, source code, or runtime profiles;
- send proposals as if they were approved changes;
- require a live daemon or tail logs in real time for v0;
- publish telemetry to an external service;
- require credentials for local checks; or
- treat a single observation as enough evidence for a durable rule.

## Architecture

EVA separates the core evidence pipeline from runtime-specific adapters:

```text
Evidence Sources
  → Scanners
  → Evidence Bundle
  → Operator Profile Compiler
  → Proposal Engine
  → Brief Compiler
  → Operator Review
```

Runtime flow for the Hermes adapter:

```text
Hermes profile stores
  → eva-loop
  → EVA Vault artifacts
  → scheduled or manual operator review
```

See [docs/architecture.md](docs/architecture.md) for the conceptual architecture, runtime/data-flow architecture, module map, data contracts, adapter boundary, and live-mode decision record.

## Quickstart

```bash
git clone https://github.com/stefan-mcf/eva.git
cd eva
python3 -m pip install -e .
```

Run a strict dry-run. This prints JSON and does not create or modify a vault:

```bash
eva-loop --no-write --json
```

Expected output shape:

```json
{
  "scanner": "combined",
  "memory": {"scanner": "memory", "summary": {}},
  "sessions": {"scanner": "sessions", "summary": {}},
  "skills": {"scanner": "skills", "summary": {}},
  "configs": {"scanner": "configs", "summary": {}},
  "operator_profile": {"generated_at": "..."},
  "proposal_summary": {"proposals": [], "written": []}
}
```

Run against explicit profile and vault paths:

```bash
eva-loop \
  --profiles-dir /path/to/hermes/profiles \
  --vault /path/to/eva-vault
```

The write-mode loop creates vault artifacts under the configured vault path. Use `--no-write` for audits, CI smoke tests, or examples where no files should be created.

## CLI overview

Installed console scripts:

- `eva-loop` — full scan/profile/proposal/brief loop.
- `eva-scan-memory` — memory-file scanner.
- `eva-scan-sessions` — session SQLite scanner.
- `eva-scan-skills` — skill scanner.
- `eva-scan-configs` — profile config scanner.
- `eva-compile-profile` — operator profile compiler.
- `eva-compile-brief` — brief compiler.
- `eva-propose-patches` — proposal generator.

See [docs/cli.md](docs/cli.md) for command inputs, outputs, read/write behavior, and examples.

## Configuration

EVA uses portable defaults based on the current user's home directory and can be configured by CLI flags or environment variables:

- `EVA_HERMES_PROFILES_DIR` — profile root for Hermes scans.
- `EVA_PROFILE_DIR` — EVA adapter profile root.
- `EVA_VAULT_DIR` — vault root for evidence, profiles, proposals, briefs, and health artifacts.

Runtime thresholds can be supplied with `context/settings.json` in the EVA vault. A template lives at [adapters/hermes/settings.template.json](adapters/hermes/settings.template.json). See [docs/configuration.md](docs/configuration.md).

## Safety

EVA's core invariant is proposal-only operation. It can write evidence and proposals to an EVA vault in write mode, but it never modifies the source profiles it scans. `--no-write` is a strict dry-run and is covered by tests and the release-readiness script.

See [docs/safety.md](docs/safety.md) for read/write boundaries, private-data handling, and publication checks.

## Hermes adapter

The Hermes adapter is the first runtime integration. The committed files in [adapters/hermes/](adapters/hermes/) are templates and examples, not live profile state. See [docs/hermes-adapter.md](docs/hermes-adapter.md) for setup guidance, scheduling notes, and adapter constraints.

## Examples

Synthetic examples are available under [examples/](examples/):

- [example-scan.json](examples/example-scan.json)
- [example-proposal.json](examples/example-proposal.json)
- [example-brief.md](examples/example-brief.md)

They are intentionally generic and contain no live runtime data.

## Development

```bash
python3 -m pip install -e .
python3 -m pip install pytest ruff build twine
python3 -m ruff check .
python3 -m pytest -q
python3 -m compileall -q src tests
python3 scripts/public_readiness_check.py
python3 -m build
python3 -m twine check dist/*
```

## Public release status

Before publishing a repository visibility change, run the release-readiness gate in [docs/release-readiness.md](docs/release-readiness.md), verify the exact commit SHA on GitHub, and confirm commit attribution maps to the intended account.

## License

MIT. See [LICENSE](LICENSE).
