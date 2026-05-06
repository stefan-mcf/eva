# Scheduling and Notifications

EVA is a local CLI package. It runs, reads durable evidence, writes vault artifacts when write mode is enabled, prints output, and exits. It is not a long-running daemon in the current local-first release.

## Does a terminal need to stay open?

No, not if a scheduler runs EVA.

A terminal only needs to stay open for a manual foreground command such as:

```bash
eva-loop --profiles-dir /path/to/hermes/profiles --vault /path/to/eva-vault
```

For unattended operation, use one of these scheduler layers:

- Hermes cron, when EVA is operated from Hermes;
- OS cron;
- macOS launchd;
- Linux systemd timers;
- another local scheduler or wrapper script.

The scheduler owns process startup, logs, retry policy, and delivery. EVA owns the scan and vault artifacts.

## Notification ownership

EVA core does not send Telegram, Discord, email, SMS, Slack, or desktop notifications by itself. Instead, EVA emits notification-ready text at:

```text
eva-vault/health/latest-notification.txt
```

A scheduler, wrapper, or Hermes agent can read that file and deliver it to an operator-approved destination.

If delivery fails, the vault remains the source of truth. Inspect:

```text
eva-vault/briefs/latest-brief.md
eva-vault/plans/latest-plan.md
eva-vault/health/latest-notification.txt
```

## Manual foreground run

Use foreground runs for setup, debugging, or one-off audits:

```bash
eva-loop \
  --profiles-dir /path/to/hermes/profiles \
  --vault /path/to/eva-vault
```

This prints the brief to stdout and writes vault artifacts. Closing the terminal stops only the currently running foreground process; it does not affect already written artifacts.

## Hermes cron pattern

Hermes cron is the best fit when the operator already uses Hermes and wants the final message delivered back through a Hermes-supported channel.

Recommended cron prompt shape:

```text
Run EVA unattended using explicit paths. Execute eva-loop with the configured profiles directory and EVA vault. Read health/latest-notification.txt after the scan. Deliver a concise operator notification including status, finding counts, pending proposal count, plan path, brief path, and next recommended tranche. Do not apply fixes or mutate source profiles.
```

Important notes:

- Create the cron job from the Hermes profile/channel that should receive the response, or configure delivery explicitly in Hermes.
- Use explicit `--profiles-dir` and `--vault` paths.
- Do not store private chat IDs, scheduler IDs, or delivery destinations in the public EVA repository.
- The Hermes gateway or scheduler service must be running for platform delivery.

## OS cron pattern

A minimal cron entry can run EVA and keep logs without an interactive terminal:

```cron
0 9 * * * cd /path/to/eva && /path/to/python -m eva.loop --profiles-dir /path/to/hermes/profiles --vault /path/to/eva-vault > /path/to/eva-vault/health/latest-cron.log 2>&1
```

That entry does not send a chat message. Add a local notifier wrapper if delivery is needed.

## macOS launchd pattern

For macOS, create a user LaunchAgent that runs a wrapper script. The wrapper should:

1. activate the intended Python environment;
2. run `eva-loop` with explicit paths;
3. redirect stdout/stderr to vault-local logs;
4. optionally send `health/latest-notification.txt` through an approved notifier.

Keep LaunchAgent labels, local account paths, and delivery destinations out of public docs and committed templates.

## Linux systemd timer pattern

For Linux, pair a user service with a timer. The service should run a wrapper script with explicit paths and write logs under the selected vault. The timer controls schedule. A separate notifier can send `health/latest-notification.txt` after the service succeeds.

## Failure handling

If an unattended run fails:

1. inspect scheduler logs;
2. inspect vault logs if the wrapper writes them;
3. rerun `eva-loop --no-write --json` manually with the same paths;
4. check whether the failure is scan coverage, permissions, Python environment, or delivery only;
5. do not apply remediation from a degraded or partial scan until coverage is understood.

## Public-template boundary

Committed EVA docs may show placeholder paths such as `/path/to/eva-vault`. They must not include live credentials, chat IDs, scheduler IDs, local account-specific paths, or delivery destinations.
