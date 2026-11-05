# Haven cloud-only foundation — current state

Requirement: basic AI plus private cloud storage, with no application install,
models, files or persistent app-managed storage on the owner’s laptop. Improving
intelligence is deferred. The browser is only a transient UI client.

## Implemented and verified

- Default production mode is HAVEN_CLOUD_ONLY=1. All data and processing live on
  the server; default data path is /workspace/haven-storage, outside the code tree.
- Login uses a bearer token kept only in page memory. No cookies or browser storage
  APIs are used in this mode. Reload requires login; server files/history remain.
- Downloads are disabled in the API and UI. File references remain in server-side
  chat with excerpts. Uploads and a Create cloud note dialog can save information
  to the server; cloud notes are created in RAM and do not need a local disk file.
- Existing private storage, quotas, Trash/restore/purge, backup/restore, recovery,
  source answers and basic local intent model remain available.
- 19 backend tests passed. Ten cloud-only browser checks passed, including empty
  localStorage/sessionStorage/IndexedDB/Cache API/service-worker storage and no
  cookies/external HTTP requests. Thirteen legacy-mode browser regression checks
  also passed separately. Test workspaces use synthetic data and are removed.

The app cannot guarantee literal zero browser/OS disk writes: browser-managed
cache, password-manager state, swap or crash reports are outside its control.
The verified scope is no persistent application-managed laptop data or AI install.

## Deployment gate — 5 November 2026

Haven is installed on the owner's free PythonAnywhere account. The traditional
Python 3.13 WSGI website is enabled, with HTTPS enforcement and no public static
directory mappings. The provider's startup log confirms the WSGI application is
ready and its worker started; its error log was empty at the last check.
**External HTTPS/login verification remains pending**, so do not report all public
behavior tested. Exact domain, console and private checksums are recorded in ignored
.private-hosting/deployment-state.json.

Completed on the provider:

- Secure API binding is ready, destination-bound to www.pythonanywhere.com.
- Minimal runtime source/archive and WSGI configuration were uploaded and read back.
- Pinned dependencies installed in ~/haven-venv, reusing system packages where valid.
- Synthetic WSGI setup/login/upload/sourced-answer/download-blocking checks passed
  on the home filesystem, including file/chat persistence after reopening.
- Owner password was initialized through the hidden console prompt after explicit
  owner authorization. No password value belongs in source, logs or status records.
- Measured home file allocation: 43,172,629 bytes (about 41.2 MiB). This is a file-size
  estimate, not the provider's authoritative quota meter. File payload quota: 64 MiB.
- Private data: ~/haven-data; source: ~/haven; no laptop install/download occurred.
- WSGI file is fail-closed if owner initialization is missing. No billing or paid
  service endpoints were used. Provider reports free-site expiry on 5 December 2026.

Remaining immediate gate: the running workspace permits the provider management
domain but not the new application domain. A real HTTPS CONNECT probe returned a
403 tunnel denial. An additive network draft allowing the application domain was
saved, preserving all existing hosts and the token's management-only destination.
It requires the owner to review/save/publish through environment settings. No
network bypass or publication was performed by the assistant.

After that change applies, verify /api/session reports setup_required=false and
cloud_only=true, unauthenticated files return 401, assets use no-store, HTTP redirects
to HTTPS, and real login/notes/chat work. Preserve owner data and do not rerun setup
or create another site/console. See deploy/pythonanywhere-operation.md.

Local setup checks: four preflight tests, four scoped-provider tests and six
bootstrap safety tests passed. The provider smoke is distinct from the earlier
local WSGI/browser suites. Public-route restart behavior, independent backup/recovery
and automated monthly renewal remain unverified. This is a limited free pilot,
not a promise of permanently available, maintenance-free storage.

Templates in deploy/ prepare systemd, configuration and HTTPS proxy behavior. They
are not installed/activated or production-tested. Start.sh is for the remote server,
not the owner’s laptop. No laptop download or installation is being requested.

## Intelligence

The built-in assistant uses local intent classification and document retrieval,
not a general-purpose generative model. No external AI/storage API is needed.
Optional loopback-only Ollama support is retained for later, with no downloaded
or verified generative model. Do not add intelligence features before hosting and
storage foundations are usable.

Earlier business and application work remains intact. The owner created the hosting
account; the assistant installed/configured Haven. No outreach or new paid service
was enabled during this work.

## GitHub source handoff

The owner requested using GitHub. The selected existing repository is
araadhay99-sketch/iie-big-data. Haven source, tests and deployment documents were
pushed to main and verified at initial source commit
816019f85bb6206d29967ed9e57f621dd07a4761. Application data, credentials, environments,
test artifacts and earlier business records were excluded. GitHub stores the code;
it does not run the AI backend or supply the app's private persistent file volume.

Additional implementation: wsgi.py and requirements-hosting.txt provide optional
traditional-host compatibility. One additional WSGI integration test passed.
Runtime code is now installed on the provider; owner credentials were entered only
through the authorized hidden console input and are stored as a password hash.
Private account reports, application data and credentials are excluded from GitHub.
External HTTPS/login and restart checks remain pending the network update above.
