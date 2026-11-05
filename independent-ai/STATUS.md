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

Cloud-only code is ready for a real hosting deployment, but **not live for the
owner’s browser**. This managed workspace has no available public ingress, HTTPS
preview, port-forward/deployment tool or routed domain. The sidecar proxy supports
outbound requests only. A separate durable volume, independent backup service,
always-on lifecycle and external restart recovery have not been verified.

Files in /workspace are current cloud workspace files, not evidence of a permanent
storage service. Environment snapshots must not be presented as preserving running
processes. No production server, paid hosting or public endpoint was provisioned.

The owner created a free PythonAnywhere account and supplied its API token through
secure environment settings. The published runtime reports the destination-bound
credential and username ready. Real authenticated API calls verified a 100-second
daily console CPU allowance, Python 3.13 availability and no existing traditional
webapps/consoles. No Haven paths existed before staging. A 32,173-byte source ZIP
and fail-closed WSGI template were uploaded privately and read back byte-for-byte.
No website has been created or enabled; no billing/upgrade endpoint was used.

PythonAnywhere Beginner is advertised with one HTTPS web app, 512 MiB total private
disk and one-month web-app expiry. See deploy/free-host-options.md. The traditional
WSGI adapter passed a local cloud-login/upload/answer compatibility test, avoiding
experimental ASGI pricing. This does not establish provider compatibility yet.

The next indispensable owner action is to open the prepared private setup console
and choose a Haven password through hidden input. The provider's official API can
create that console but its process starts only when connected in a browser. No
browser-control tool is available. Console details and exact staging checksums
belong in ignored .private-hosting/deployment-state.json; do not duplicate consoles.
The private bootstrap was uploaded and read back exactly, and one Python 3.13
console was created with its fixed script/checksum arguments. Installation has
not started through these tools, and no owner password has been entered.

Setup validation: four preflight tests, three scoped-provider tests and six
bootstrap safety tests passed. A separate real synthetic WSGI smoke passed locally
for setup/login/upload/source retrieval/download blocking and file/chat persistence
after reopening. These checks do not claim installation on PythonAnywhere.

The bootstrap must install pinned binary dependencies, measure home usage, run
synthetic WSGI/filesystem/restart checks and initialize the password hash privately.
Only then configure the public WSGI site. Initial file payload quota is 64 MiB,
leaving room within advertised disk limits for dependencies and database overhead.
Actual footprint, owner setup, HTTPS, restart behavior and recovery remain gates.
No automatic monthly renewal or independent backup infrastructure is configured.
Do not spend money or promise a permanently available free host.

Templates in deploy/ prepare systemd, configuration and HTTPS proxy behavior. They
are not installed/activated or production-tested. Start.sh is for the remote server,
not the owner’s laptop. No laptop download or installation is being requested.

## Intelligence

The built-in assistant uses local intent classification and document retrieval,
not a general-purpose generative model. No external AI/storage API is needed.
Optional loopback-only Ollama support is retained for later, with no downloaded
or verified generative model. Do not add intelligence features before hosting and
storage foundations are usable.

Earlier business and application work remains intact. No production application
deployment, hosting-account creation, message sending or new paid service occurred.

## GitHub source handoff

The owner requested using GitHub. The selected existing repository is
araadhay99-sketch/iie-big-data. Haven source, tests and deployment documents were
pushed to main and verified at initial source commit
816019f85bb6206d29967ed9e57f621dd07a4761. Application data, credentials, environments,
test artifacts and earlier business records were excluded. GitHub stores the code;
it does not run the AI backend or supply the app's private persistent file volume.

Additional implementation: wsgi.py and requirements-hosting.txt provide optional
traditional-host compatibility. One additional WSGI integration test passed.
Only source/configuration preparation files have been staged at the hosting
provider; no owner files or passwords were transferred. No laptop installation or
download occurred. GitHub source publication is complete; live hosting remains
pending dependency/owner initialization, HTTPS and persistent-storage checks.
