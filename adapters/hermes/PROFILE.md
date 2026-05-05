# EVA Hermes Profile

Profile location: `~/.hermes/profiles/eva/`

## Configuration

- **Model:** DeepSeek Flash (`deepseek-v4-flash`) — cheap, fast, good enough for scanning
- **Provider:** DeepSeek
- **Tools:** terminal, file, skills, memory, session_search, cronjob, messaging (Telegram)
- **Max turns:** 50
- **Delegation:** disabled
- **Browser/Web:** disabled (EVA doesn't browse)

## Cron Job

`eva-daily-scan` — runs daily at 9am AEST.

Pinned to DeepSeek Flash. Terminal + file tools only (no web, no delegation). Full prompt is self-contained — no skill dependency needed.

## Vault

```
workspace/eva-vault/
  context/          # Operator profile (future)
  evidence/         # corrections.jsonl, failures.jsonl, successes.jsonl
  proposals/        # pending/ + applied/
  briefs/           # One brief per scan
  health/           # Scanner health reports
```

## Skill

`eva-loop` — local profile skill at `skills/eva-loop/SKILL.md`.

Modes: SCAN (run scanners), BRIEF (compile output), FULL (scan + brief).

## Adding Scanners

Each scanner is a standalone Python module in the EVA repo (`src/eva/scanners/`). To add a new scanner:

1. Write the scanner — it takes no args, outputs JSON to stdout
2. Add it to the cron job prompt in the RUN step
3. Add a section in `compile_brief.py` for the new scanner's output shape
