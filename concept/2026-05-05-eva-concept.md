# EVA — Draft Concept Plan

**Date:** 2026-05-05

**Goal:** Build EVA — an evidence operator that watches how the agent system operates (memory, skills, session corrections, tool failures, config drift) and surfaces structured optimization proposals to the operator. Framework-agnostic concept; first adapter targets Hermes.

**Name:** EVA = Evidence & Verification Agent.

**Status:** Draft concept — not yet an implementation spec. This is the starting point for iteration.

---

## Summary

Both the HALO post (recursive agent optimization via trace → diagnose → patch → redeploy) and Graeme's research agent post (vault-based evidence accumulation that makes downstream agents smarter) describe the same pattern: an **evidence operator** that watches what happens, structures it, and feeds insight back into the system.

For Stefan's setup, EVA sits between these two:

- **Research layer** (inward-facing, not outward): watches *the agent system itself* rather than the outside world
- **Diagnostic layer**: finds cracks, contradictions, stale artifacts, repeated failures
- **Proposal layer**: drafts structured fixes for operator approval — does NOT auto-apply

This profile is not a research agent (Graeme's pattern) and not a harness self-improver (HALO). It's an **operator-support layer** that turns scattered corrections, memory entries, skill patches, and failure logs into structured, actionable intelligence about the agent system.

---

## What It Watches

### Layer 1 — Preference Accumulation

Parse the operator's corrections and habits into a structured profile:

| Source | What it extracts |
|--------|-----------------|
| Memory entries | Repeated themes, contradictions, orphaned entries |
| Skill patches | What the operator always corrects |
| Session corrections | "Actually, do it this way" patterns |
| Config changes | Preference drift across profiles |

**Output:** `operator-profile.json` + `operator-profile.md` — a compressed, structured view of "how Stefan likes things done" that any agent can load.

### Layer 2 — Crack Detection

Find what's breaking across the system:

| Signal | What it means |
|--------|--------------|
| Repeated tool failures | Broken tool, missing env var, bad config |
| Dropped Telegram handoffs | Route bridge bug, topic gating issue |
| Delegation timeouts | Model too slow for task, wrong model choice |
| Stale skills | Loaded often but always patched — needs rewrite |
| Contradictory memory entries | Two entries saying opposite things |
| Config drift | Profile X configured differently from Y for same task |

### Layer 3 — Optimization Proposals

Draft structured fixes for operator review:

| Type | Example |
|------|---------|
| Skill patch | "Here's the updated SKILL.md based on corrections from 6 sessions" |
| New skill | "You've successfully done this workflow 4 times. Should it become a skill?" |
| Memory cleanup | "These 3 entries contradict. Here's the merge proposal." |
| Model routing change | "Task X costs 12× more on GPT-5.5 than DeepSeek Flash. Same output quality observed." |
| Config alignment | "Profiles A and B disagree on delegation config. Here's the unified proposal." |

---

## Architecture

```text
~/.hermes/profiles/optimizer/
├── SOUL.md                          # Identity, boundaries, operating rules
├── config.yaml                      # Cheap model (DeepSeek Flash), local terminal, memory + session_search enabled
├── skills/
│   └── optimizer-loop/
│       ├── SKILL.md                 # Loop contract: modes, output discipline
│       └── scripts/
│           ├── scan_memory.py        # Read Hermes memory DB → contradictions, staleness, orphans
│           ├── scan_skills.py        # Skill health: last-modified vs last-loaded, patch frequency
│           ├── scan_sessions.py      # Session_search for recent corrections + failure patterns
│           ├── scan_configs.py       # Cross-profile config drift detection
│           ├── compile_profile.py    # Build operator-profile.json from accumulated evidence
│           ├── compile_brief.py      # Synthesize findings → operator brief
│           └── propose.py            # Draft structured proposals for review
├── workspace/
│   └── optimizer-vault/
│       ├── context/
│       │   ├── operator-profile.json
│       │   └── operator-profile.md
│       ├── evidence/
│       │   ├── corrections.jsonl     # Every "actually, do it this way" captured
│       │   ├── failures.jsonl        # Tool errors, dropped handoffs, timeouts
│       │   └── successes.jsonl       # Workflows that completed cleanly
│       ├── proposals/
│       │   ├── pending/              # Patches waiting for operator approval
│       │   └── applied/              # What was applied and when
│       ├── briefs/
│       │   └── optimizer-brief.md    # "Here's what I found this cycle"
│       └── health/
│           └── latest-health-check.md
├── scripts/                          # Profile-level helper scripts
└── cron/
    └── jobs.json                    # Daily scan + weekly deep audit
```

---

## The Loop

```
Every N hours (daily start, configurable):
  1. Scan memory DB → find contradictions, staleness, orphan entries
  2. Session_search for recent corrections and failure patterns
  3. Scan skills for health (last-modified vs usage frequency)
  4. Scan configs across profiles for drift
  5. Update operator-profile.json with accumulated preferences
  6. Generate optimizer-brief.md → surface findings to operator
  7. Draft proposals in proposals/pending/ for review
```

**Guardrails:**

- Never auto-apply changes — proposals only, operator approves
- Never touch secrets, auth, or production config
- Never promote a single-observation pattern into a rule
- Always flag degraded data ("memory scan incomplete — session_search unavailable")
- Always source-cite every finding ("memory entry ID X contradicts entry ID Y")

---

## Delivery Model

Findings surface to Stefan via Telegram (home channel):

- **Daily optimizer brief**: concise, structured — "What changed, what's breaking, what to review"
- **Proposals**: one at a time, with evidence, operator accepts/rejects/edits
- **Health alerts**: only when something is structurally wrong (e.g., memory DB unreachable)

The optimizer doesn't publish or broadcast. It's a private operator-support profile.

---

## Relationship to Existing System

| Existing component | How optimizer interacts |
|--------------------|------------------------|
| Memory DB | Read-only scan for contradictions/staleness |
| Skills (all profiles) | Read-only health check |
| Session transcripts | session_search for correction/failure patterns |
| Config files | Read-only cross-profile diff |
| Antaeus plans/docs | Scans for stale plans, orphaned concepts |
| Cron scheduler | Runs the optimizer loop on schedule |
| Telegram gateway | Delivers briefs and proposals to Stefan |

The optimizer is **downstream from everything** — it reads, analyzes, and proposes. It does not own execution of any other agent.

---

## Open Design Questions (to work through)

1. **What's the MVP scope?** Start with memory scan + operator brief only? Include skills scan in v0?
2. **How does operator-profile.json get consumed?** Loaded as a skill? Injected into system prompt? Both?
3. **Proposal approval flow.** How does Stefan approve/reject? Telegram inline buttons? Slash commands? Separate chat?
4. **Evidence thresholds.** How many repetitions before a pattern is "real"? 3? 5? Per-signal type?
5. **Model routing.** DeepSeek Flash for routine scans, something stronger for synthesis? Or all-Flash?

---
## Immediate Next Steps (v0)

1. ~~Settle repository/home location~~ → `stefan-mcf/eva` (private)
2. Create the EVA Hermes profile
3. Build `scan_memory.py` — the first scanner (stub written)
4. Build `compile_brief.py` — generate first operator brief from existing memory/skills
5. Manual run, review output with Stefan
6. Iterate on format before adding more scanners
