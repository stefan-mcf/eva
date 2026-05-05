"""EVA end-to-end loop orchestration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eva.common import (
    EVA_VAULT_DIR,
    HERMES_PROFILES_DIR,
    atomic_write_json,
    atomic_write_text,
    ensure_vault,
    utc_now,
)
from eva.compilers.compile_brief import compile_brief
from eva.compilers.compile_profile import compile_profile
from eva.proposers.propose_patches import generate_proposals, write_pending
from eva.scanners import scan_configs, scan_memory, scan_sessions, scan_skills


def run_all(
    vault: str | Path = EVA_VAULT_DIR,
    profiles_dir: str | Path = HERMES_PROFILES_DIR,
    days: int | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Run every EVA scanner and compiler.

    When ``write`` is false, this function is a strict dry-run: it does not create
    the vault, append evidence, write profiles, write briefs, or write proposals.
    """
    vault_path = ensure_vault(Path(vault)) if write else Path(vault).expanduser()
    profiles_dir = Path(profiles_dir).expanduser()

    memory = scan_memory.run_scan(str(profiles_dir), vault=vault_path)
    sessions = scan_sessions.run_scan(profiles_dir, days=days, vault=vault_path if write else None)
    skills = scan_skills.run_scan(profiles_dir, vault=vault_path)
    configs = scan_configs.run_scan(profiles_dir)
    bundle: dict[str, Any] = {
        "scanner": "combined",
        "timestamp": utc_now(),
        "memory": memory,
        "sessions": sessions,
        "skills": skills,
        "configs": configs,
    }
    profile = compile_profile(bundle, vault_path, write=write)
    proposals = generate_proposals(bundle, profile, vault_path)
    paths = write_pending(proposals, vault_path) if write else []
    bundle["operator_profile"] = profile
    bundle["proposal_summary"] = {"proposals": proposals, "written": [str(p) for p in paths]}
    brief = compile_brief(bundle)
    if write:
        latest = vault_path / "briefs" / "latest-scan.json"
        latest_brief = vault_path / "briefs" / "latest-brief.md"
        stamp = utc_now().replace(":", "").replace("+", "Z")
        atomic_write_json(latest, bundle)
        atomic_write_text(latest_brief, brief)
        atomic_write_json(vault_path / "briefs" / f"scan-{stamp}.json", bundle)
        atomic_write_text(vault_path / "briefs" / f"brief-{stamp}.md", brief)
    bundle["brief"] = brief
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run EVA scans, profile compilation, proposal drafting, and brief compilation"
    )
    parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    parser.add_argument("--profiles-dir", default=str(HERMES_PROFILES_DIR))
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--json", action="store_true", help="print combined JSON instead of brief markdown")
    parser.add_argument("--no-write", action="store_true", help="strict dry-run; do not create or modify files")
    args = parser.parse_args()
    bundle = run_all(args.vault, args.profiles_dir, args.days, write=not args.no_write)
    if args.json:
        printable = {k: v for k, v in bundle.items() if k != "brief"}
        print(json.dumps(printable, indent=2, sort_keys=True))
    else:
        print(bundle["brief"], end="")


if __name__ == "__main__":
    main()
