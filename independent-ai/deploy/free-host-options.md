# Zero-new-spending hosting check — 4 November 2026

Update, 5 November 2026: the owner created the free PythonAnywhere account and
provided a token through secure settings. Authenticated CPU/version/console/webapp
reads and private source upload/read-back work. Dependencies installed and synthetic
WSGI/home-filesystem checks passed; owner initialization is complete. Home file
allocation measured about 41.2 MiB. The traditional Python 3.13 site is enabled,
HTTPS is required, and the provider reports a ready worker with an empty error log.
Update, 6 November: the network addition is applied and live HTTPS/login, note
retrieval, file operations and provider-restart persistence checks passed. No plan
was upgraded or paid service selected. The original review below records the
earlier proposal; current evidence and browser-test limits are in STATUS.md.

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

Registration, secure operator access and hidden owner-password initialization are
complete. The network addition and actual application-route tests are also complete.
No further owner setup is needed to launch this pilot. Free-site periodic renewal
is still required and not automated. See deploy/account-access.md.

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

Haven is a verified live free pilot on the owner's PythonAnywhere account.
Installation, real HTTPS/login, file operations, sourced answers and provider-restart
persistence checks passed. Hosting runs outside this managed workspace. Independent
disaster recovery and automatic monthly renewal remain absent; the free-site expiry
reported by the provider is 5 December 2026.
