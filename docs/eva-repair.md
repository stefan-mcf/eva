# EVA Repair

EVA Repair is the approval-gated repair layer for EVA-generated evidence and proposals.

## Pipeline stages

```text
scan -> propose -> plan -> repair draft -> operator ledger -> safe apply -> verify -> closeout
```

- `eva-repair draft` and `eva-repair draft-all` convert proposal JSON into repair bundle JSON.
- `eva-repair ledger` renders a single operator-visible repair ledger/inbox.
- `eva-repair apply` applies only safe, deterministic EVA-owned artifact actions.
- `eva-repair closeout` records repair outcomes, concise run-report artifacts,
  and unresolved human-gated work.

## Safety doctrine

EVA-Repair is human-gated, machine-executable.

Allowed without approval:

- draft repair bundles;
- write repair ledgers;
- write review packets under the EVA vault;
- record proposal state transitions requested by the operator;
- verify generated artifacts;
- write closeout reports under the EVA vault.

Auto-apply is restricted to these target classes:

- `eva_generated_artifact`
- `eva_review_packet`
- `eva_proposal_state`

Always human-gated target classes:

- `hermes_skill`
- `hermes_memory`
- `hermes_profile_config`
- `operator_profile`
- `scheduler`
- `credential`
- `delivery_destination`
- `public_repo`
- `unknown`

EVA-Repair must not silently edit durable memory, live Hermes skills, profile configs, credentials, scheduler state, delivery targets, or public repositories.

## Proposal lifecycle

Proposal files are stored by lifecycle state:

```text
proposals/pending/
proposals/approved/
proposals/deferred/
proposals/rejected/
proposals/applied/
proposals/superseded/
```

Valid states are:

- `pending`
- `approved`
- `deferred`
- `rejected`
- `applied`
- `superseded`

Use `eva-repair approve`, `eva-repair reject`, or `eva-repair defer` to move proposal files with operator notes.

## Repair artifacts

Repair files are stored under:

```text
repairs/drafts/
repairs/approved/
repairs/applied/
repairs/failed/
repairs/ledger/
review-packets/
```

Every repair bundle records:

- source scan timestamp;
- source proposal id/kind;
- risk;
- target class;
- human gate requirement;
- auto-apply eligibility;
- planned actions;
- rollback notes;
- verification notes.

## CLI examples

Use a temporary vault first:

```bash
eva-repair list --vault /tmp/eva-vault --json
eva-repair draft-all --vault /tmp/eva-vault --write --json
eva-repair ledger --vault /tmp/eva-vault --write --markdown
eva-repair closeout --vault /tmp/eva-vault --write --markdown
```

Inspect and approve a proposal:

```bash
eva-repair inspect <proposal-id> --vault /tmp/eva-vault --json
eva-repair approve <proposal-id> --vault /tmp/eva-vault --note 'approved for generated review packet only'
```

Apply a safe EVA-owned generated-artifact repair:

```bash
eva-repair apply <repair-bundle-id> --vault /tmp/eva-vault --json
```

Do not apply live memory/skill/config/profile repair bundles without explicit operator approval.

## Validation and closeout

Remediation plans include validator output for:

- scan completeness;
- proposal actionability;
- suppressed proposal kinds that still have active findings;
- evidence classes with missing proposal kinds.

Closeout should include:

- drafted/applied/blocked repair counts;
- unresolved human-gated bundle counts;
- before/after scan timestamps when supplied;
- paths to generated ledgers/outcomes/review packets;
- `latest-run-report.{json,md}` for concise operator-facing reporting; and
- `latest-residual-plan.{json,md}` for post-repair human-gated next actions.

## Suppression doctrine

Do not broadly suppress active remediation proposal classes while findings are still accumulating. If a proposal is reviewed and found to be a false positive, record a rejected/no-op outcome with evidence notes instead of hiding the class.
