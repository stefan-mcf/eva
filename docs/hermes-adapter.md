# Hermes Adapter

The Hermes adapter is EVA's first runtime integration. It teaches EVA where to find Hermes profile stores and how to run the evidence loop from a Hermes profile or scheduler.

## Adapter scope

The adapter covers:

- profile memory files;
- session SQLite stores;
- skill directories;
- profile configuration files;
- a template `SOUL.md` for an EVA profile;
- a template `PROFILE.md` capability spec;
- a template `settings.json` for the EVA vault; and
- a reusable EVA skill at `adapters/hermes/skills/eva/SKILL.md`.

The adapter does not include live local profile state, secrets, chat identifiers, or generated vault artifacts.

## Create a Hermes EVA profile

1. Create a dedicated Hermes profile for EVA.
2. Copy or adapt `adapters/hermes/SOUL.md` into that profile's instruction file.
3. Install or attach the EVA skill if a Hermes agent will operate EVA:

   ```bash
   mkdir -p "$HOME/.hermes/skills/eva"
   cp adapters/hermes/skills/eva/SKILL.md "$HOME/.hermes/skills/eva/SKILL.md"
   ```

   See [docs/skills.md](skills.md) for skill doctrine, profile-specific install paths, and maintenance rules.
4. Configure the profile with local tools needed to run `eva-loop` and read profile files.
5. Set explicit paths when the profile-local home differs from the normal shell home.
6. Schedule `eva-loop` with `--profiles-dir` and `--vault`.

Example command:

```bash
EVA_HERMES_PROFILES_DIR=/path/to/hermes/profiles \
EVA_VAULT_DIR=/path/to/eva-vault \
eva-loop --profiles-dir /path/to/hermes/profiles --vault /path/to/eva-vault
```

## Scheduling

A daily scan is a reasonable default for the current local-first release. Manual scans are useful before changing runtime configuration or publishing a release. Live tailing is outside the current adapter boundary and should not be enabled without preserving the same proposal-only safety boundary.

## Committed templates vs local runtime state

Committed:

- `adapters/hermes/SOUL.md`
- `adapters/hermes/PROFILE.md`
- `adapters/hermes/settings.template.json`
- `adapters/hermes/skills/eva/SKILL.md`
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

## Skill doctrine

The EVA skill is committed in full at `adapters/hermes/skills/eva/SKILL.md` so users can inspect it before enabling it. It is not live profile state and is not automatically copied into a user's Hermes home by Python package installation. See [docs/skills.md](skills.md) for install commands, copy-vs-canonical-source guidance, and maintenance rules.
