# Hermes Adapter Templates

These files are public templates for running EVA against Hermes profile stores. They are not live deployment files.

## Files

- `SOUL.md` — template instructions for an EVA Hermes profile.
- `PROFILE.md` — example profile capability spec.
- `settings.template.json` — generic vault settings template.
- `skills/eva/SKILL.md` — project-bundled Hermes skill for repeatable dry-run-first EVA operation and testing; see `../../docs/skills.md` for install doctrine.

## Basic setup

1. Install EVA:

   ```bash
   python3 -m pip install -e .
   ```

2. Create a local EVA vault outside this repository.
3. Create a Hermes profile using `SOUL.md` as a starting point.
4. Run with explicit paths:

   ```bash
   eva-loop --profiles-dir /path/to/hermes/profiles --vault /path/to/eva-vault
   ```

5. If a Hermes agent will operate EVA, install or attach `skills/eva/SKILL.md` after inspecting it:

   ```bash
   mkdir -p "$HOME/.hermes/skills/eva"
   cp adapters/hermes/skills/eva/SKILL.md "$HOME/.hermes/skills/eva/SKILL.md"
   ```

6. Schedule the command only after confirming `eva-loop --no-write --json` behaves as expected.

## Do not commit

- Local profile configs.
- Credentials.
- Generated vault artifacts.
- Scheduler IDs.
- Delivery destinations.
- Live operator memory or session data.
