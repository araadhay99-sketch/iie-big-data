# Haven — cloud AI and private server storage

The current requirement is **no app, model, chat-history or user-file storage on
Araadhay’s laptop**. Haven now defaults to cloud-only mode. The laptop is only a
browser client; all processing and persistent application data belong on a cloud
server. Improving intelligence is deferred.

## Actual status

The cloud-only application is installed on the owner's free PythonAnywhere account.
Its Python 3.13 WSGI site is enabled with HTTPS required. Provider-side synthetic
login/upload/answer/persistence checks passed; the worker reports ready and its
error log was empty. Owner initialization is complete and the file payload quota
is 64 MiB. **Live HTTPS/login/storage checks now pass**, including sourced answers,
Trash/restore/purge and data surviving a confirmed provider restart. A Getting
started note and labelled demonstration are saved in the cloud. See STATUS.md.

No paid subscription/storage was enabled. The provider reports site expiry on
5 December 2026; renewal automation and independent disaster recovery are not
configured. Do not install or download Haven onto the owner's laptop.

## What cloud-only mode does

- Stores file bytes, indexes, chat history, password hashes and sessions on the server.
- Keeps the browser’s authentication token only in JavaScript memory. No login
  cookies, localStorage, sessionStorage, IndexedDB, Cache API or service worker
  storage is created by the application.
- Requires a fresh sign-in after reload; files and conversation remain on the server.
- Disables both file-download API access and the corresponding browser controls.
- Sends no external AI/storage requests in the default mode. Assets are served by
  the same server, and responses use Cache-Control: no-store.
- Supports upload, RAM-only Create cloud note, Trash, restore, permanent deletion
  and server-side backups.

A browser necessarily uses temporary RAM, and browser/OS cache, swap, crash reports
or password-manager behavior cannot be guaranteed to write literally zero bytes.
The verified promise is no persistent laptop storage managed by this application,
no local AI/model install and no client file-download feature in cloud-only mode.

## Basic AI scope

The built-in assistant is a small locally trained intent classifier plus a document
relevance model. It quotes relevant passages from cloud-stored UTF-8 TXT, Markdown
and CSV files with source references. It handles basic help, identity, privacy and
storage questions. It does not browse or provide general-purpose generative chat.
No external model download or AI API key is needed to use this foundation.

The optional local-only Ollama adapter remains available for later work, but no
model has been downloaded or inference-tested. Its URL must be loopback; external
providers and redirects are rejected. Leave HAVEN_OLLAMA_MODEL unset for now.

## Server operation — never on the owner’s laptop

Tested on Linux/Python 3.12 and hosted Python 3.13. A hosting operator can install dependencies once and
run the service on the authorized remote server. Runtime use needs no external
AI or storage service. Keep these commands and any virtual environment on that
server, not the user’s laptop:

    sh start.sh

In the current prepared cloud environment, installed packages also allow:

    python3 run.py

This listens on loopback port 7860 by default. That endpoint is for internal server
validation; it is not a remote browser URL. The user needs an authorized HTTPS
route with the original Host/Origin preserved before they can use it remotely.
Only one server process may open the data directory.

## Persistent storage

Default cloud data path: /workspace/haven-storage. This is a path inside the current
cloud environment, **not proof of a durable hosting volume or backup service**.
For real hosting, mount a verified persistent server volume at HAVEN_DATA_DIR.
The deployment template uses /var/lib/haven. Keep data outside the code/static path.

Default quota is 512 MiB of stored file payload, 25 MiB/upload and 200 stored files.
Trash counts toward quota; Delete forever reclaims file payload. Old chat quotes
remain until history is cleared. History retains the last 200 messages. Database,
index, backup and filesystem overhead are outside the displayed payload quota.
Text indexing covers the first 64,000 characters of supported files; other file
types can be stored but are not indexed. Files retain their original bytes.

Server files and backup ZIPs are not encrypted by this app. Use a hosting volume
and backups with appropriate access controls/encryption. Passwords use salted
PBKDF2 hashes; all file/chat APIs require authentication. Content-changing requests
require matching browser origin, and streaming uploads have explicit size limits.

## Deployment preparation and remaining gates

Templates in deploy/ describe a single-process systemd service, server configuration
and a Caddy HTTPS reverse proxy. They are preparation artifacts, not applied or
verified production infrastructure. A deployment operator still needs:

1. Authorized hosting with a reachable HTTPS route and a persistent disk.
2. An agreed hostname, TLS setup and supported operator access.
3. Server-side dependency installation and service account/directory permissions.
4. Real public-route, restart, backup and recovery checks before readiness is claimed.

No owner technical labour is assumed beyond indispensable account verification
and approvals. The assistant should perform setup when actual hosting capabilities
are available. The templates do not by themselves provide accounts, DNS, TLS or
storage. No paid service may be provisioned without explicit cost approval.

A cloud server still depends on its host and network. Here “independent” means no
external AI/storage SaaS dependency; it cannot mean independence from physical
hardware or the provider operating the chosen cloud machine.

## Configuration

| Variable | Cloud default | Purpose |
|---|---|---|
| HAVEN_CLOUD_ONLY | 1 | Memory-only bearer sessions and downloads disabled |
| HAVEN_DATA_DIR | /workspace/haven-storage | Persistent path on the hosting server |
| HAVEN_QUOTA_MB | 512 | File payload quota, in MiB |
| HAVEN_BIND_HOST | 127.0.0.1 | Backend listens privately behind HTTPS ingress |
| HAVEN_PORT | 7860 | Internal listening port |
| HAVEN_ALLOWED_HOSTS | 127.0.0.1,localhost | Explicit accepted hostname(s); configure for actual ingress |
| HAVEN_OLLAMA_MODEL | unset | Optional future local model |
| HAVEN_OLLAMA_URL | http://127.0.0.1:11434 | Local-only inference service |

HAVEN_CLOUD_ONLY=0 is an explicit legacy compatibility mode that re-enables
cookie sessions and file downloads. It does **not** meet the current no-laptop-
storage requirement and is not the mode to deploy for the owner. In that mode
HAVEN_SECURE_COOKIES=1 is required for remote HTTPS cookies.

## Server backups

Stop the server before creating a backup; the workspace lock rejects a backup
while the server is running. Keep the archive on server/private backup storage:

    python3 backup.py backup /var/lib/haven /private/server-backups/haven.zip
    python3 backup.py restore /private/server-backups/haven.zip /var/lib/haven-restored

Backups verify file hashes and database integrity, reject unsafe archive paths,
and revoke old sessions. Existing destination folders are not overwritten.
Backup storage durability, scheduling and disaster recovery have not been deployed.

## Verification

Development tests run on the cloud server:

    python3 -m pip install -r requirements-dev.txt
    python3 -m unittest discover -s tests -v
    node tests/cloud-browser.cjs

The development-only browser driver is Playwright 1.56.1 with system Chromium.
It is not an application dependency. Synthetic test workspaces are deleted after
checks. The browser suite verifies no application-managed browser persistence,
server-side file/history survival across reload, no download controls and no
external HTTP requests. Legacy-mode regression tests are also retained separately.
Provider-side synthetic checks passed on its home filesystem. Seven anonymous
public route checks and 28 live authenticated checkpoints also passed, including
restart persistence. All 39 automated tests passed after the prefork startup fix.
Live Chromium UI automation was blocked before page load by its workspace proxy
CA trust; TLS verification was preserved. Local browser suites passed separately.

## Free-pilot hosting

The owner created a PythonAnywhere account and securely connected its management
API. Beginner is advertised at $0/month with one web app, HTTPS and 512 MiB total private
server storage. New free web apps have a one-month expiry/confirmation requirement;
this is not a promise of maintenance-free, permanently available hosting.

The optional wsgi.py adapter works with traditional Python WSGI hosting and has
passed a cloud-login/upload/answer test. requirements-hosting.txt contains the
extra dependency. Provider file read/write and account/version inspection work;
the private bootstrap installed dependencies, passed synthetic checks and secured
the owner before site configuration. Measured home allocation was about 41.2 MiB.
See deploy/account-access.md, deploy/pythonanywhere-operation.md and STATUS.md.
No owner laptop installation is needed. No paid plan has been selected, and
periodic renewal/recovery automation is not configured.
