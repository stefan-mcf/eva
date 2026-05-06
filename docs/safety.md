# EVA Safety Model

EVA is intentionally conservative. It helps an operator understand an agent runtime, but it does not become an agent that changes that runtime.

## Proposal-only invariant

EVA may produce evidence, summaries, briefs, remediation plans, notification summaries, and proposal files. A proposal or remediation plan is a recommendation for manual review. EVA does not apply proposals automatically, modify runtime configuration, edit memories, patch skills, or rewrite source repositories.

## `--no-write` invariant

`eva-loop --no-write` is a strict dry-run. It must not create a vault, write evidence files, write proposals, update operator profiles, create briefs, write remediation plans, or write notification summaries. This behavior is covered by tests and by `scripts/public_readiness_check.py`.

## What EVA reads

For the Hermes adapter, EVA may read:

- profile memory files;
- session SQLite databases;
- skill markdown and supporting files;
- profile configuration files; and
- existing EVA vault settings when a vault is explicitly provided.

Other adapters should document their equivalent evidence sources.

## What EVA writes

In write mode, EVA writes only under the configured EVA vault:

- evidence summaries;
- compiled operator profile JSON/Markdown;
- pending proposal JSON files;
- brief Markdown/JSON artifacts;
- remediation plan JSON/Markdown artifacts;
- scheduler-friendly notification summaries; and
- health/degraded-mode notes when implemented.

## What EVA never writes

EVA never writes directly to source runtime profile stores, memory files, skills, configs, credentials, external services, package registries, or repository visibility settings. Any workflow that applies a proposal must be a separate, explicit, operator-approved action.

## Private-data handling

Runtime records can contain sensitive operational details. Treat the EVA vault as private runtime state. Do not commit generated vault artifacts to a public repository. Public docs and examples should use synthetic data only.

## Secret-handling stance

EVA scanners should look for signs that secrets may be present without printing secret values. Release checks scan for obvious tokens, passwords, private key blocks, and live runtime artifacts. If a check finds a possible secret, remove the data and rotate the credential as appropriate before publication.

## Manual approval flow

1. EVA scans durable evidence.
2. EVA drafts a proposal with rationale and supporting evidence.
3. EVA compiles a checklisted remediation plan that groups findings into ordered tranches.
4. The operator reviews the proposal and plan.
5. A separate approved workflow applies, edits, rejects, or defers the proposal.
6. EVA can later observe the result as evidence.

## Pre-publication scans

Before making a repository public, run:

```bash
python3 -m ruff check .
python3 -m pytest -q
python3 -m compileall -q src tests
python3 scripts/public_readiness_check.py
git diff --check
```

Also verify GitHub attribution and exact remote SHA before changing visibility.

## Threat model

EVA's primary risks are accidental disclosure and accidental authority expansion. The design mitigates those risks by keeping examples synthetic, vault artifacts ignored, source stores read-only, and the proposal/application boundary explicit.
