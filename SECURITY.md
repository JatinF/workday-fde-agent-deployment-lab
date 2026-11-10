# Security

This lab stores no Workday client secret, access token, or private key. `.env.example` is empty on purpose. Do not commit a filled `.env`.

The scanner is `scripts/reject_private_keys.py`. It skips its own file and keeps the key-header text split so the scanner does not match itself.

The security checklist is [docs/checklists/security.md](docs/checklists/security.md). Production use is NO-GO until the gates in [docs/gates.md](docs/gates.md) are actually run.
