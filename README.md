# EVA — Evidence & Verification Agent

> The agent that watches all the other agents.

EVA is a framework-agnostic evidence operator. It observes how your agent system operates — memory, skills, session corrections, tool failures, config drift — and surfaces structured optimization proposals. It does not auto-apply changes. It reports to you.

First adapter targets Hermes. Future adapters welcome.

## What EVA does

- **Preference accumulation** — learns how you like things done from corrections, memory entries, skill patches
- **Crack detection** — finds tool failures, stale skills, config drift, contradictory memory
- **Optimization proposals** — drafts structured fixes for operator approval

## Status

Pre-alpha. Private repo. Design in progress.
