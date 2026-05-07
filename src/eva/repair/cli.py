"""CLI for EVA Repair."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from eva.common import EVA_VAULT_DIR, read_json
from eva.proposers.propose_patches import record_outcome
from eva.repair.applier import apply_repair_bundle
from eva.repair.closeout import (
    compile_closeout_report,
    render_closeout_markdown,
    write_closeout_report,
)
from eva.repair.io import list_proposals, load_repair_bundle, write_repair_bundle
from eva.repair.ledger import (
    compile_repair_ledger,
    render_repair_ledger_markdown,
    write_repair_ledger,
)
from eva.repair.planner import draft_repair_bundle
from eva.repair.verifier import verify_repair_outcome

PROPOSAL_STATES = ["pending", "approved", "deferred", "rejected", "applied", "superseded"]


def _print(data: Any, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
    elif isinstance(data, str):
        print(data)
    else:
        print(json.dumps(data, indent=2, sort_keys=True))


def _find_proposal(vault: Path, proposal_id: str) -> dict[str, Any]:
    exact_matches = []
    prefix_matches = []
    for proposal in list_proposals(vault, PROPOSAL_STATES):
        path = Path(str(proposal.get("_path", "")))
        proposal_id_value = str(proposal.get("id", ""))
        if proposal_id_value == proposal_id or path.stem == proposal_id:
            exact_matches.append(proposal)
        elif proposal_id_value.startswith(proposal_id) or path.stem.startswith(proposal_id):
            prefix_matches.append(proposal)
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise ValueError(f"ambiguous proposal id: {proposal_id}")
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        raise ValueError(f"ambiguous proposal id prefix: {proposal_id}")
    raise FileNotFoundError(f"proposal not found: {proposal_id}")


def _add_common_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true")


def _configure_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eva-repair",
        description="Draft, gate, apply safe EVA repair bundles, and close out outcomes",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    list_parser = sub.add_parser("list")
    list_parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    list_parser.add_argument("--state")
    _add_common_json(list_parser)

    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("proposal_id")
    inspect_parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    _add_common_json(inspect_parser)

    draft_parser = sub.add_parser("draft")
    draft_parser.add_argument("proposal_id")
    draft_parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    draft_parser.add_argument("--scan")
    draft_parser.add_argument("--write", action="store_true")
    _add_common_json(draft_parser)

    draft_all_parser = sub.add_parser("draft-all")
    draft_all_parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    draft_all_parser.add_argument("--scan")
    draft_all_parser.add_argument("--write", action="store_true")
    _add_common_json(draft_all_parser)

    ledger_parser = sub.add_parser("ledger")
    ledger_parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    ledger_parser.add_argument("--write", action="store_true")
    _add_common_json(ledger_parser)
    ledger_parser.add_argument("--markdown", action="store_true")

    for name in ("approve", "reject", "defer"):
        outcome_parser = sub.add_parser(name)
        outcome_parser.add_argument("proposal_id")
        outcome_parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
        outcome_parser.add_argument("--note", required=True)

    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("bundle_id")
    apply_parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    _add_common_json(apply_parser)
    apply_parser.add_argument("--force", action="store_true")
    apply_parser.add_argument("--no-require-approved", action="store_true")

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("bundle_or_outcome_id")
    verify_parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    _add_common_json(verify_parser)

    closeout_parser = sub.add_parser("closeout")
    closeout_parser.add_argument("--vault", default=str(EVA_VAULT_DIR))
    closeout_parser.add_argument("--before-scan")
    closeout_parser.add_argument("--after-scan")
    closeout_parser.add_argument("--write", action="store_true")
    _add_common_json(closeout_parser)
    closeout_parser.add_argument("--markdown", action="store_true")
    return parser


def _load_scan(args: argparse.Namespace) -> dict[str, Any] | None:
    scan_path = getattr(args, "scan", None)
    return read_json(Path(scan_path)) if scan_path else None


def _run_draft_all(args: argparse.Namespace, vault: Path, scan: dict[str, Any] | None) -> None:
    bundles = []
    paths = []
    for proposal in list_proposals(vault):
        bundle = draft_repair_bundle(proposal, scan, vault=vault)
        bundles.append(bundle)
        if args.write:
            paths.append(str(write_repair_bundle(bundle, vault)))
    if args.write:
        ledger = compile_repair_ledger(
            bundles,
            source_scan_timestamp=(scan or {}).get("timestamp"),
        )
        write_repair_ledger(ledger, vault)
    _print({"count": len(bundles), "written": paths}, args.json)


def _run_ledger(args: argparse.Namespace, vault: Path) -> None:
    bundles = []
    for draft_path in (vault / "repairs" / "drafts").glob("*.json"):
        bundles.append(read_json(draft_path))
    ledger = compile_repair_ledger(bundles)
    if args.write:
        write_repair_ledger(ledger, vault)
    rendered = render_repair_ledger_markdown(ledger) if args.markdown and not args.json else ledger
    _print(rendered, args.json)


def _run_verify(args: argparse.Namespace, vault: Path) -> None:
    found = None
    for state in ("applied", "failed"):
        for path in (vault / "repairs" / state).glob(f"*{args.bundle_or_outcome_id}*.json"):
            found = read_json(path)
            break
        if found:
            break
    if not found:
        raise FileNotFoundError(f"outcome not found: {args.bundle_or_outcome_id}")
    _print(verify_repair_outcome(found, vault=vault), args.json)


def main() -> None:
    parser = _configure_parser()
    args = parser.parse_args()
    vault = Path(getattr(args, "vault", EVA_VAULT_DIR)).expanduser()
    try:
        scan = _load_scan(args)
        if args.cmd == "list":
            _print(list_proposals(vault, [args.state] if args.state else None), args.json)
        elif args.cmd == "inspect":
            _print(_find_proposal(vault, args.proposal_id), args.json)
        elif args.cmd == "draft":
            bundle = draft_repair_bundle(_find_proposal(vault, args.proposal_id), scan, vault=vault)
            path = write_repair_bundle(bundle, vault) if args.write else None
            _print({"bundle": bundle, "path": str(path) if path else None}, args.json)
        elif args.cmd == "draft-all":
            _run_draft_all(args, vault, scan)
        elif args.cmd == "ledger":
            _run_ledger(args, vault)
        elif args.cmd in {"approve", "reject", "defer"}:
            state = {"approve": "approved", "reject": "rejected", "defer": "deferred"}[args.cmd]
            print(record_outcome(args.proposal_id, state, vault, args.note))
        elif args.cmd == "apply":
            _, bundle = load_repair_bundle(args.bundle_id, vault)
            outcome = apply_repair_bundle(
                bundle,
                vault=vault,
                require_approved=not args.no_require_approved,
                force=args.force,
            )
            _print(outcome, args.json)
            if outcome.get("status") not in {"applied", "blocked"}:
                sys.exit(1)
        elif args.cmd == "verify":
            _run_verify(args, vault)
        elif args.cmd == "closeout":
            before = read_json(Path(args.before_scan)) if args.before_scan else None
            after = read_json(Path(args.after_scan)) if args.after_scan else None
            report = compile_closeout_report(vault, before_scan=before, after_scan=after)
            if args.write:
                write_closeout_report(report, vault)
            rendered = render_closeout_markdown(report) if args.markdown and not args.json else report
            _print(rendered, args.json)
    except Exception as exc:
        print(f"eva-repair: error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
