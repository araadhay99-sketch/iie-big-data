# Haven — verified live free pilot

Updated 6 November 2026 (India). The app URL and account details are in ignored
.private-hosting/deployment-state.json. Source, tests and public docs are in GitHub;
credentials, app data, environments, artifacts and earlier business records are not.

## Delivered and verified

- Basic single-owner cloud storage and a server-side document relevance/intent
  assistant. It retrieves UTF-8 TXT, Markdown and CSV passages with sources; it is
  not a general generative model. Intelligence upgrades remain deferred.
- Real HTTPS page/assets return 200 with no-store and no cookies. HTTP redirects
  to HTTPS. Session reports setup_required=false and cloud_only=true. Anonymous
  file/message/status endpoints return 401. Seven anonymous route checks passed.
- 28 live authenticated checkpoints passed: login, owner-reclaim prevention,
  indexed notes, sourced answers, downloads blocked, Trash/restore/purge, and
  owner/files/conversation persisting across a confirmed provider restart.
- Only our temporary test files were removed. Getting started.md and a labelled
  demonstration conversation remain as a useful example. Owner data was preserved.
- Traditional Python 3.13 WSGI site enabled; source ~/haven, virtualenv ~/haven-venv,
  private data ~/haven-data, no public static mappings to private directories.
- No new paid plan, subscription or service was enabled; new spending was zero.

## Startup fix and test limits

The real host imports WSGI before forking workers. Starting the asyncio thread
there left children waiting on a thread that did not survive fork. wsgi.py now
initializes store/model/loop/thread on first request inside the worker, with PID
checks and cleanup. app.py releases the store if model initialization fails.
All 39 automated tests passed, including a bounded real-fork regression. Earlier
local browser suites passed 10 cloud-only and 13 legacy checks. A small help-text
correction also removed an inaccurate download promise in cloud-only mode.

Live Chromium UI automation was blocked by this workspace browser's missing proxy
CA trust before page load. No TLS bypass was used. Live browser screenshots/full
UI checks remain unverified, separate from successful TLS-verified HTTP/API tests.
The safe browser result is in ignored artifacts/. No UI assets changed in the fix.

## Storage, availability and continuity

- File payload quota 64 MiB, max upload 25 MiB, max 200 files; Trash counts toward
  quota. Database/index/backup overhead is separate. Initial measured account file
  allocation was about 41.2 MiB; this is not the provider's authoritative quota meter.
- Free host advertises 512 MiB private disk, one worker, 100 daily console CPU seconds.
  The provider reports site expiry on 5 December 2026. Renewal is required; no
  automated renewal, scheduled maintenance or independent backup is configured.
- Backups/restores remain offline procedures in backup.py. Provider restart
  persistence passed; whole-provider disaster recovery is not verified. The app
  does not encrypt stored file content. This is a limited free pilot, not an SLA.
- App processing/files/chat stay on the server. No laptop app/model installation,
  downloads or persistent app-managed browser storage. Browser/OS cache, swap and
  password managers are outside its control; literal zero disk writes is not assured.
- Hosting serves requests independently of this chat. Changes/maintenance require
  an active authorized session. No recurring agent operation has been configured.
- Read deploy/pythonanywhere-operation.md and private state before changes. The
  network addition is applied; do not save/publish it again. Do not reinitialize
  owner credentials, duplicate sites/consoles or delete owner data. Spend nothing
  without approval. The earlier income/business project remains separate and paused.
