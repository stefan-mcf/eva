# EVA Configuration

EVA is configured with CLI flags, environment variables, and optional JSON settings in the EVA vault.

## Environment variables

- `EVA_HERMES_PROFILES_DIR`: Hermes profile root. Default: `~/.hermes/profiles`.
- `EVA_PROFILE_DIR`: EVA adapter profile root. Default: `$EVA_HERMES_PROFILES_DIR/eva`.
- `EVA_VAULT_DIR`: EVA vault root. Default: `$EVA_PROFILE_DIR/workspace/eva-vault`.

CLI flags such as `--profiles-dir` and `--vault` are preferred in scripts because they make the target paths explicit.

## `context/settings.json`

Runtime thresholds can be supplied by creating `context/settings.json` inside the EVA vault. The file is merged over built-in defaults.

Example:

```json
{
  "memory": {
    "duplicate_similarity_threshold": 0.9
  },
  "skills": {
    "oversized_bytes": 80000,
    "stale_days": 45
  },
  "sessions": {
    "window_days": 30,
    "repeated_failure_threshold": 3
  },
  "operator": {
    "name": "Operator"
  }
}
```

A fuller template is available at `adapters/hermes/settings.template.json`.

## Portable defaults

Defaults are home-relative and are resolved at runtime. This keeps the package usable across machines, CI, and temporary test environments. Public documentation should prefer placeholders such as `/path/to/profiles` rather than local absolute paths.

## Profile-local HOME caveat

Some adapter runtimes launch tools with a profile-local home directory. In those cases, explicit environment variables or CLI flags are safer than assuming the process home is the operator's normal shell home.

Example:

```bash
EVA_HERMES_PROFILES_DIR=/path/to/profiles \
EVA_VAULT_DIR=/path/to/eva-vault \
eva-loop --json
```

## Vault layout

```text
eva-vault/
  context/
    settings.json
    operator-profile.json
    operator-profile.md
  evidence/
    corrections.jsonl
    failures.jsonl
    successes.jsonl
  proposals/
    pending/
    applied/
    rejected/
  briefs/
    latest-scan.json
    latest-brief.md
  health/
```

## Retention guidance

The vault may contain sensitive derived evidence. Store it outside the public repository, back it up according to local policy, and prune old generated briefs or scan JSON files when they are no longer useful. Keep pending proposal records until they are accepted, rejected, or superseded.

## Template settings

The Hermes adapter template is safe to commit because it contains thresholds and generic labels only. Do not commit live vault settings if they contain operator-specific details.
