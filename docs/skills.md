# Hermes Skills

EVA ships a project-bundled Hermes skill for safe EVA operation:

```text
adapters/hermes/skills/eva/SKILL.md
```

That file is the canonical skill source. It is committed as normal repository content so users can inspect the complete skill text before installing or copying it into a Hermes profile. The docs link to the canonical `SKILL.md` instead of duplicating the full skill body, because duplicating it in multiple documents creates drift.

## What the EVA skill does

The `eva` skill teaches a Hermes agent how to operate, test, and review EVA safely. It covers:

- clean checkout and Python setup;
- repository readiness gates;
- dry-run-first `eva-loop --no-write --json` checks;
- explicit `--profiles-dir` and `--vault` paths;
- keeping source runtime/profile directories read-only;
- writing generated output only to an EVA vault;
- source-mutation guards for real profile scans;
- generated artifact review before sharing;
- degraded, empty, noisy, and unsafe result classification; and
- concise tester/operator reports.

It does not authorize EVA or Hermes to auto-apply memory, skill, config, source-code, profile, credential, scheduler, or delivery-destination changes.

## Skill installation doctrine

Project-bundled skills are source artifacts. They are not live deployment state and are not automatically copied into a user's Hermes home by installing the Python package. This keeps package installation side-effect free and lets users inspect the full skill before enabling it.

Use one of these patterns:

1. **Use directly from the repo** when a Hermes profile supports loading a skill by path or has the repo configured as a skill source.
2. **Copy into a Hermes skills directory** when the profile should own a local installed copy.
3. **Attach the repo skill to a dedicated EVA profile** when operating EVA repeatedly from Hermes.

Always keep the canonical source in the repo at `adapters/hermes/skills/eva/SKILL.md`. If you copy it elsewhere, treat that copy as installed runtime state and refresh it when the repo skill changes.

## Install into a local Hermes skill directory

From the repository root:

```bash
mkdir -p "$HOME/.hermes/skills/eva"
cp adapters/hermes/skills/eva/SKILL.md "$HOME/.hermes/skills/eva/SKILL.md"
```

For a named profile with its own skill directory:

```bash
PROFILE_NAME=eva
HERMES_PROFILE_HOME="$HOME/.hermes/profiles/$PROFILE_NAME"
mkdir -p "$HERMES_PROFILE_HOME/skills/eva"
cp adapters/hermes/skills/eva/SKILL.md "$HERMES_PROFILE_HOME/skills/eva/SKILL.md"
```

If your Hermes installation uses a shared canonical skill tree or profile symlinks, install to that canonical skill tree instead of creating a second physical copy.

## Verify the skill file

Validate the committed skill frontmatter and body with the Python standard library:

```bash
python - <<'PY'
from pathlib import Path
import re

path = Path('adapters/hermes/skills/eva/SKILL.md')
content = path.read_text(encoding='utf-8')
assert content.startswith('---')
match = re.search(r'\n---\s*\n', content[3:])
assert match, 'frontmatter close missing'
frontmatter = content[3:match.start()+3]
assert re.search(r'^name:\s*eva\s*$', frontmatter, re.M)
description = re.search(r'^description:\s*(.+)$', frontmatter, re.M)
assert description and description.group(1).startswith('Use when')
assert len(description.group(1)) <= 1024
assert len(content) <= 100_000
assert content[match.end()+3:].strip()
print('PASS eva skill validation')
PY
```

Then run the repository readiness gate:

```bash
python -m ruff check .
python -m pytest -q
python -m compileall -q src tests
python scripts/public_readiness_check.py
git diff --check
```

## Use during an EVA test

Start a Hermes session with the skill loaded, then run the workflow in the skill:

```bash
hermes --skills eva
```

If the skill is not installed in Hermes yet, inspect and copy the canonical source first:

```bash
less adapters/hermes/skills/eva/SKILL.md
mkdir -p "$HOME/.hermes/skills/eva"
cp adapters/hermes/skills/eva/SKILL.md "$HOME/.hermes/skills/eva/SKILL.md"
hermes --skills eva
```

Within Hermes, the skill's core operating rule is:

```text
verify checkout → dry-run first → explicit paths → vault-only writes → artifact review → report evidence, limits, next steps
```

## Maintenance rules

When changing the EVA skill:

1. Edit only `adapters/hermes/skills/eva/SKILL.md` as the canonical source.
2. Keep frontmatter `name: eva` and the file path in sync.
3. Update `docs/skills.md`, `docs/hermes-adapter.md`, `docs/testing-quickstart.md`, `adapters/hermes/README.md`, and `scripts/public_readiness_check.py` if the path or install doctrine changes.
4. Do not paste a second full copy of the skill into docs; link to the canonical file instead.
5. Run the skill validation snippet and repository readiness checks.
6. Clean generated build/test artifacts before committing.
