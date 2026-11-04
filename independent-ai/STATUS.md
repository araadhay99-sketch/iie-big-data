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

## Deployment blocker

Cloud-only code is ready for a real hosting deployment, but **not live for the
owner’s browser**. This managed workspace has no available public ingress, HTTPS
preview, port-forward/deployment tool or routed domain. The sidecar proxy supports
outbound requests only. A separate durable volume, independent backup service,
always-on lifecycle and external restart recovery have not been verified.

Files in /workspace are current cloud workspace files, not evidence of a permanent
storage service. Environment snapshots must not be presented as preserving running
processes. No production server, paid hosting or public endpoint was provisioned.

The owner confirmed there is no hosting account outside this workspace. No cloud
provider identity/account is currently bound. A bounded public-doc review found
PythonAnywhere Beginner as a conditional free-pilot candidate: one HTTPS web app,
512 MiB total private disk, one-month web-app expiry. See deploy/free-host-options.md.
The traditional WSGI adapter passed a real cloud-login/upload/answer compatibility
test, avoiding experimental ASGI pricing. This is not a provider deployment.

The next indispensable owner step is to create the free Beginner account through
PythonAnywhere’s secure signup and provide only its username. Do not request
passwords/API keys in chat or assume paid fees/billing consent. Actual free-account
API access, dependency footprint, owner initialization before public setup,
HTTPS/expiry behavior and persistent-data/recovery checks remain deployment gates.
Do not spend money or claim a free permanently available host without evidence.

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
araadhay99-sketch/iie-big-data. Only Haven source, tests and deployment documents
are prepared for its initial commit; application data, credentials, environments,
test artifacts and earlier business records are excluded. GitHub stores the code;
it does not run the AI backend or supply the app's private persistent file volume.

Additional implementation: wsgi.py and requirements-hosting.txt provide optional
traditional-host compatibility. One additional WSGI integration test passed.
No files were transferred to a provider or the owner’s laptop.
