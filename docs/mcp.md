# EVA MCP bridge

EVA exposes a small stdio MCP bridge for Hermes and other MCP clients. The bridge is the capability surface for bounded scans and remediation-plan compilation; it is not the full operator doctrine. For Hermes-side operating guidance, safety interpretation, scheduler/notification boundaries, memory-provider boundaries, and artifact-review rules, use the project-bundled EVA skill at `adapters/hermes/skills/eva/SKILL.md` and the install notes in `docs/skills.md`.

## Server command

```bash
uv run --project /path/to/eva --with mcp eva-mcp
```

Hermes registration:

```bash
hermes mcp add eva --command uv --args run --project /path/to/eva --with mcp eva-mcp
hermes mcp test eva
```

## Tools

### `eva_scan_health`

Runs one EVA scanner or the combined scan.

Parameters:

- `scan`: `all`, `memory`, `sessions`, `skills`, `configs`, or `memory_provider`.
- `profiles_dir`: optional Hermes profiles directory.
- `vault`: optional EVA vault path.
- `days`: optional session scan window.
- `write`: default `false`; strict dry-run/no-write unless explicitly true.
- `include_details`: default `false`; returns bounded summaries unless explicitly true.

### `eva_compile_remediation`

Runs the scan-to-remediation compiler and returns an operator-safe remediation plan summary plus notification summary.

Parameters:

- `profiles_dir`, `vault`, `days` as above.
- `write`: default `false`; no vault writes unless explicitly true.
- `include_bundle`: default `false`; keeps MCP results bounded.

## Safety boundary

The MCP bridge is read/proposal-first. It does not expose proposal application, config mutation, memory mutation, skill mutation, or profile changes.

## Verification

```bash
cd /path/to/eva
PYTHONPATH=src python3 -m py_compile src/eva/mcp_server.py
PYTHONPATH=src python3 -m pytest -q tests/test_mcp_server.py tests/test_eva_pipeline.py
```
