# Security Policy

EVA scans operational records that may contain sensitive information. Treat source profile stores and generated vault artifacts as private by default.

## Reporting issues

For now, report security issues privately to the repository owner. Do not include secrets, private logs, live memory content, or credentials in public issues.

## Supported versions

EVA is pre-alpha. Security fixes target the main branch until versioned releases are established.

## Sensitive data policy

- Do not commit live profile data.
- Do not commit generated vault artifacts.
- Do not paste credentials into issues or examples.
- If a secret is accidentally committed, remove it from history as appropriate and rotate the credential.

## Scanner behavior

Scanners and readiness checks should detect possible sensitive patterns without printing secret values.
