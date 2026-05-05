# EVA Hermes Profile Template

This file is an example profile specification for running EVA as a Hermes profile. It is not a live profile record.

## Location

Create a local Hermes profile using the normal Hermes profile mechanism. Keep live profile files, credentials, scheduler IDs, and generated vault data outside this repository.

## Model guidance

EVA's loop is mostly scanning, summarization, and proposal drafting. A low-cost model is usually sufficient for scheduled scan briefs. Use a stronger review model if the profile is expected to adjudicate complex architecture recommendations.

## Required capabilities

- Terminal or process execution to run `eva-loop`.
- File read access to the profile stores being scanned.
- File write access to the configured EVA vault.
- Optional scheduling support for periodic scans.
- Optional messaging support for delivering briefs through an operator-approved channel.

## Usually unnecessary capabilities

- Browser access.
- External web search.
- Delegation.
- Direct access to unrelated production services.

## Example schedule

Run once per day or on demand:

```bash
EVA_HERMES_PROFILES_DIR=/path/to/hermes/profiles \
EVA_VAULT_DIR=/path/to/eva-vault \
eva-loop --profiles-dir /path/to/hermes/profiles --vault /path/to/eva-vault
```

## Vault

```text
eva-vault/
  context/
  evidence/
  proposals/
  briefs/
  health/
```

## Adding scanners

Each scanner should be a standalone Python module under `src/eva/scanners/`, produce JSON-compatible output, and preserve degraded-mode reporting when evidence is missing or unreadable.
