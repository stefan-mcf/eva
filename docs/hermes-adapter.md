# Hermes Adapter

The Hermes adapter is EVA's first runtime integration. It teaches EVA where to find Hermes profile stores and how to run the evidence loop from a Hermes profile or scheduler.

## Adapter scope

The adapter covers:

- profile memory files;
- session SQLite stores;
- skill directories;
- profile configuration files;
- a template `SOUL.md` for an EVA profile;
- a template `PROFILE.md` capability spec; and
- a template `settings.json` for the EVA vault.

The adapter does not include live local profile state, secrets, chat identifiers, or generated vault artifacts.

## Create a Hermes EVA profile

1. Create a dedicated Hermes profile for EVA.
2. Copy or adapt `adapters/hermes/SOUL.md` into that profile's instruction file.
3. Configure the profile with local tools needed to run `eva-loop` and read profile files.
4. Set explicit paths when the profile-local home differs from the normal shell home.
5. Schedule `eva-loop` with `--profiles-dir` and `--vault`.

Example command:

```bash
EVA_HERMES_PROFILES_DIR=/path/to/hermes/profiles \
EVA_VAULT_DIR=/path/to/eva-vault \
eva-loop --profiles-dir /path/to/hermes/profiles --vault /path/to/eva-vault
```

## Scheduling

A daily scan is a reasonable default for v0. Manual scans are useful before changing runtime configuration or publishing a release. Live tailing is future work and should not be enabled without preserving the same proposal-only safety boundary.

## Committed templates vs local runtime state

Committed:

- `adapters/hermes/SOUL.md`
- `adapters/hermes/PROFILE.md`
- `adapters/hermes/settings.template.json`
- `adapters/hermes/README.md`

Not committed:

- live profile config files;
- credentials;
- generated vault artifacts;
- local scheduler IDs;
- delivery destinations; and
- private operator data.

## Degraded scans

If a profile store, database, or settings file cannot be read, EVA should report degraded coverage rather than claiming a fresh complete scan. Degraded scans are still useful when they clearly identify what was missing.

## Adapter boundary

Hermes is an adapter, not EVA's entire identity. The core project should remain understandable to users of other agent runtimes.
