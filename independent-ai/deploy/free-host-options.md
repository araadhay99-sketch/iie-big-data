# Zero-new-spending hosting check — 4 November 2026

The owner confirmed that no hosting account exists outside this Codex workspace.
No account has been created, card provided, plan upgraded or service published.

## Conditional first candidate: PythonAnywhere Beginner

Official sources:

- [Pricing](https://www.pythonanywhere.com/pricing/): Beginner is advertised at
  $0/month, with one username.pythonanywhere.com web app, 512 MiB private file
  storage and free SSL support. Paid plans are separate; none was selected.
- [Current free features](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/):
  one web worker, two consoles, 100 console CPU-seconds and one-month web-app expiry.
  New accounts no longer include scheduled tasks or MySQL. SQLite uses file storage.
- [2026 free-account changes](https://blog.pythonanywhere.com/221/) and
  [expiry explanation](https://blog.pythonanywhere.com/129/): free sites need periodic
  renewal/confirmation; expiration stops running the site. It is not an unconditional
  always-on, maintenance-free promise. The older expiry article's three-month
  examples are superseded by the current one-month rule.
- [API](https://help.pythonanywhere.com/pages/API/) and
  [API-token setup](https://help.pythonanywhere.com/pages/GettingYourAPIToken/):
  token-based management, file and console operations are documented. Actual free
  account API permissions are not yet tested. Never request the token in chat.
- [ASGI hosting](https://help.pythonanywhere.com/pages/ASGICommandLine/): native
  FastAPI/ASGI deployment is experimental and long-term pricing is undecided.

To avoid relying on experimental ASGI pricing, Haven now has a traditional WSGI
adapter in wsgi.py using pinned a2wsgi. A local end-to-end WSGI test covers cloud
login, uploads, sourced answers and download blocking. This verifies application
compatibility, not an actual PythonAnywhere deployment or account eligibility.

### Limits to verify in the account before deployment

- Keep all code, dependencies, data and backups on the hosting server. A 512 MiB
  host limit includes more than user files: use an initial 64 MiB Haven payload
  quota, then measure installed dependencies and actual free disk before uploading.
- Confirm available Python/package versions and actual CPU/resource limits. No
  generative model will fit this proposed starter setup; intelligence is deferred.
- Confirm HTTPS, Host/Origin forwarding, SQLite/locking, restart behavior and API
  upload/command permissions with an authenticated account test.
- Complete owner-password initialization through an authenticated server console
  before opening public first-use setup. Do not expose an unclaimed owner workspace.
- Treat periodic free-account confirmation as a genuine remaining maintenance
  requirement. No supported renewal automation has been configured or verified.
- Do not upgrade, add billing, accept charges or promise permanent free hosting.

The next indispensable owner step, if this limited free pilot is acceptable, is to
create a Beginner account through the provider's secure signup page and report
only the username. Account consent/email verification cannot be completed by the
assistant as the owner. Secure operator access is a later step; no password or API
token belongs in chat. The assistant handles technical setup once supported access
exists; no laptop installation or file download is required from the owner.

## Alternatives not selected

- [Render Free](https://render.com/docs/free): free service filesystems are
  ephemeral; uploaded files and SQLite data are lost on restart/redeploy/sleep.
  Persistent disks require paid service; free Postgres expires after 30 days.
  It does not meet this app's durable-file requirement at the authorized spend.
- [Hugging Face Spaces storage](https://huggingface.co/docs/hub/spaces-storage):
  the default filesystem is ephemeral. Current bucket options deserve separate
  consideration, but object storage has not been verified as safe for Haven's
  SQLite/WAL/flock/fsync semantics. See free-host-huggingface.md. Do not mount the
  live database on an unverified bucket filesystem.

## Verdict

There is a plausible limited free-pilot path; no verified live service yet.
This workspace alone still lacks user-facing ingress and durable-host guarantees.
The remaining immediate blocker is owner hosting-account registration/consent,
followed by supported secure access and actual provider tests. Research, a WSGI
compatibility test and a prepared app do not substitute for those checks.
