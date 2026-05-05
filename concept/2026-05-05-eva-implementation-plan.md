# EVA Implementation Plan

**Date:** 2026-05-05
**Repo:** `stefan-mcf/eva` (private) — https://github.com/stefan-mcf/eva
**Local:** repository checkout path (operator-specific)
**Status:** v0 scaffold built. Scanners and brief compiler working against Hermes-compatible profile data.

---

## Overview

EVA is the Evidence & Verification Agent — an operator-support layer that watches how an agent system operates and surfaces structured optimization proposals. Framework-agnostic design; first adapter targets Hermes.

This plan covers building EVA to a minimally useful state (daily briefs reaching the operator via Telegram) plus a clear path for deeper capabilities.

---

## Tranche 1: Core Scanning Pipeline ✅

**What:** Memory scanner that reads live Hermes profiles and produces structured findings.
**Status:** Done.

- [x] `src/eva/scanners/scan_memory.py` — parses markdown MEMORY.md / USER.md across profiles
- [x] Contradiction detection (keyword heuristics)
- [x] Orphan reference detection
- [x] Duplicate detection
- [x] Topic distribution
- [x] Directory iteration (no `glob` hangs)

**Debt to address later:**
- Self-match fix applied for same-entry contradictions; still noisy
- Staleness scanner disabled (markdown has no per-entry timestamps — need filesystem mtime comparison or manual dating)
- Orphan detection uses static keyword list — should be configurable or inference-driven
- No session scanning yet

---

## Tranche 2: Brief Compiler ✅

**What:** Takes scan JSON → human-readable markdown brief for Telegram.
**Status:** Done.

- [x] `src/eva/compilers/compile_brief.py`
- [x] Sections: findings (contradictions, orphans, duplicates), topic distribution, scanner health
- [x] Deduplication of findings
- [x] Telegram-compatible markdown output

**Debt:**
- No operator-profile.json generation yet
- No proposal drafting (`src/eva/proposers/` directory exists but empty)
- Brief format not yet tuned for Stefan's eye — needs feedback loop

---

## Tranche 3: Hermes Profile Creation

**What:** A real `eva` Hermes profile that runs the pipeline on schedule and delivers briefs via Telegram.
**Dependencies:** Tranche 1, Tranche 2.

### 3.1 Profile skeleton

```
~/.hermes/profiles/eva/
├── SOUL.md                        # Copy from adapters/hermes/SOUL.md
├── config.yaml                    # DeepSeek Flash, local terminal, memory+session_search+file
├── skills/
│   └── eva-loop/
│       ├── SKILL.md
│       └── scripts/
│           ├── run_scan.sh        # Orchestrates all scanners
│           └── deliver_brief.sh   # Pipes brief to final response
├── workspace/
│   └── eva-vault/                 # Full vault structure from concept doc
│       ├── context/
│       │   ├── operator-profile.json
│       │   └── operator-profile.md
│       ├── evidence/
│       │   ├── corrections.jsonl
│       │   ├── failures.jsonl
│       │   └── successes.jsonl
│       ├── proposals/
│       │   ├── pending/
│       │   └── applied/
│       ├── briefs/
│       └── health/
└── cron/
    └── jobs.json
```

### 3.2 Tasks

- [x] 3.2.1 Create profile with `hermes profile create eva`
- [x] 3.2.2 Configure `config.yaml` — model: DeepSeek Flash, provider: deepseek, tools: terminal+file+memory+session_search+cronjob, limited context
- [x] 3.2.3 Copy SOUL.md from `adapters/hermes/SOUL.md` into profile root
- [x] 3.2.4 Install EVA package as editable: `pip install -e .` from the repository checkout in the profile's venv
- [x] 3.2.5 Create `eva-loop` skill with SKILL.md + scripts
- [x] 3.2.6 Create vault directory structure
- [x] 3.2.7 Create cron job: `eva-daily-scan` — daily, runs the loop, delivers brief
- [x] 3.2.8 Smoke test: `hermes -p eva chat -q "Run a memory scan and deliver the brief"`
- [x] 3.2.9 Verify brief lands in Telegram home channel

---

## Tranche 4: Session Scanner

**What:** Scan session transcripts for correction patterns, repeated failures, and tool errors.
**Dependencies:** Tranche 3 (needs profile + cron in place to surface findings).

### 4.1 Scanner design

Read from `~/.hermes/profiles/*/sessions/` — SQLite `state.db` with `sessions` and `messages` tables.

Detect:
- Corrections: messages where the operator says "actually", "no, do it this way", "don't", "never", "remember this"
- Tool failures: tool results containing error/exception/traceback
- Repeated patterns: same tool failing ≥3 times across sessions
- Skill patches: `skill_manage(action='patch')` tool calls → skill improvement frequency

### 4.2 Tasks

- [x] 4.2.1 `src/eva/scanners/scan_sessions.py` — reads session SQLite, applies correction detection
- [x] 4.2.2 Correction extraction with session linking ("session ABC-123: Stefan corrected X")
- [x] 4.2.3 Tool failure aggregation ("terminal tool failed 12 times this week: pattern is SSH timeout")
- [x] 4.2.4 Integrate into `compile_brief.py` with separate section
- [x] 4.2.5 Add to eva-loop skill — run after memory scan

---

## Tranche 5: Skill Health Scanner

**What:** Check skill health across profiles — staleness, patch frequency, last-modified vs usage.
**Dependencies:** Tranche 3.

### 5.1 Tasks

- [x] 5.1.1 `src/eva/scanners/scan_skills.py`
- [x] 5.1.2 Parse SKILL.md frontmatter across all profiles
- [x] 5.1.3 Flag skills with high patch frequency (≥3 patches without restructure = needs rewrite)
- [x] 5.1.4 Flag skills not loaded in ≥30 days (stale)
- [x] 5.1.5 Flag oversized skills (antaeus-system at ~100KB is a known issue)
- [x] 5.1.6 Integrate into brief

---

## Tranche 6: Config Drift Scanner

**What:** Cross-profile config comparison to detect inconsistencies.
**Dependencies:** Tranche 3.

### 6.1 Tasks

- [x] 6.1.1 `src/eva/scanners/scan_configs.py`
- [x] 6.1.2 Parse `config.yaml` across all profiles
- [x] 6.1.3 Compare delegation config, model choices, max_turns, timeouts
- [x] 6.1.4 Flag profiles with same role but different config ("antaeus-terminal and antaeus-terminal-side diverge on X")
- [x] 6.1.5 Integrate into brief

---

## Tranche 7: Operator Profile Builder

**What:** Synthesize accumulated evidence into a structured operator profile that agents can load as context.
**Dependencies:** Tranche 1, 4, 5, 6 (needs evidence from all scanners).

### 7.1 Tasks

- [x] 7.1.1 `src/eva/compilers/compile_profile.py`
- [x] 7.1.2 Ingest corrections.jsonl, memory scan findings, session corrections
- [x] 7.1.3 Produce `operator-profile.json` — structured preferences: communication style, tool preferences, model routing rules, naming conventions
- [x] 7.1.4 Produce `operator-profile.md` — human-readable companion
- [x] 7.1.5 Test: load operator-profile.md as a skill in a session, verify agent behavior aligns

---

## Tranche 8: Proposal Engine

**What:** Draft structured optimization proposals for operator approval.
**Dependencies:** Tranche 1-7.

### 8.1 Tasks

- [x] 8.1.1 `src/eva/proposers/propose_patches.py`
- [x] 8.1.2 Template-driven proposals: "Based on 6 sessions of corrections, here's the updated SKILL.md for skill X"
- [x] 8.1.3 Memory merge proposals: "These 3 entries contradict. Proposed merge: ..."
- [x] 8.1.4 Config alignment proposals: "Profiles A and B diverge on delegation. Both should use DeepSeek Flash"
- [x] 8.1.5 Write proposals to `eva-vault/proposals/pending/`
- [x] 8.1.6 Approval flow integration — operator accepts/rejects via Telegram or CLI

---

## Tranche 9: Feedback Loop + Iteration

**What:** EVA gets better at its job by tracking which proposals the operator accepts/rejects.
**Dependencies:** Tranche 8.

- [x] 9.1 Track proposal outcomes in `proposals/applied/`
- [x] 9.2 Weight future proposals by acceptance history
- [x] 9.3 Tune contradiction threshold, orphan keyword list, staleness windows
- [x] 9.4 Brief format iteration based on operator feedback

---

## Dependency Graph

```
1 (Memory Scanner) ──┐
                      ├──► 3 (Profile) ──┬──► 4 (Session Scanner)
2 (Brief Compiler) ───┘                  ├──► 5 (Skill Health)
                                         ├──► 6 (Config Drift)
                                         │
                                         4+5+6 ──► 7 (Operator Profile)
                                                      │
                                                      7 ──► 8 (Proposals)
                                                               │
                                                               8 ──► 9 (Feedback Loop)
```

---

## Current State Summary

| Component | Status |
|-----------|--------|
| Repo | `stefan-mcf/eva` (private), pushed |
| Memory scanner | Working against live data |
| Brief compiler | Working, produces Telegram-ready output |
| Hermes profile | Created and smoke-tested |
| Vault directory | Created with context/evidence/proposals/briefs/health structure |
| Cron job | `eva-daily-scan` scheduled daily at 09:00 |
| Session scanner | Working against Hermes SQLite `state.db` files |
| Skill scanner | Working across profile-local skills |
| Config scanner | Working across profile `config.yaml` files |
| Operator profile | Generated to `context/operator-profile.json` and `.md` |
| Proposal engine | Generates pending proposals and records applied/rejected outcomes |
| Feedback loop | Acceptance-history scoring and tunable settings file in place |

---

## Completion Evidence

- Local verification: `python3 -m ruff check .` and `python3 -m pytest -q` pass.
- Full-loop verification: `python3 -m eva.loop` writes latest scan/brief, operator profile, and deduplicated pending proposals.
- Hermes profile smoke: `hermes --profile eva ... deliver_brief.sh` returned the expected EVA brief.
- Cron verification: `eva-daily-scan` is enabled and scheduled for daily Telegram delivery.

## Next Action

Public-release gate: keep the repo private until Stefan explicitly chooses to publish. Before flipping visibility, run one more secret scan, attribution check, and remote CI/status verification.
