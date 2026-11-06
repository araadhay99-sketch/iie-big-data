# PythonAnywhere operation — 6 November 2026

Current phase: **verified live free pilot**. Read STATUS.md and ignored
.private-hosting/deployment-state.json first. The private record has actual URLs,
checksums and safe verification results. Do not commit it or owner data, reinitialize
credentials, create duplicate consoles/sites, or clear existing owner history.

## Installed configuration

- Traditional WSGI, Python 3.13, source ~/haven, virtualenv ~/haven-venv.
- Private data ~/haven-data; 64 MiB file payload quota; cloud-only mode enabled.
- No Ollama model/external AI API. BLAS thread counts limited to one.
- Provider entry point /var/www/<username>_pythonanywhere_com_wsgi.py checks an
  existing owner password record before exposing the app. No public static mapping
  exposes source, installer or data. HTTPS is enforced; HTTP redirects verified.
- Runtime entry point must initialize inside the worker's first request, not in
  the prefork master. Threads do not survive fork; opening Store in the master also
  shares its flock. Keep the lazy initialization/PID guards in wsgi.py.

The create API required python313, while configuration returns 3.13. The official
API create example uses python310 for Python 3.10:
https://help.pythonanywhere.com/pages/API/#webapps . Do not recreate the live site.

## Verification evidence

- 39 automated tests passed, including bounded POSIX fork, initialization failure
  cleanup and cloud-only integration. A final 19-test app regression also passed
  after the small built-in help-text correction.
- Seven anonymous public endpoints: real page/assets/session succeed; protected
  file/message/status routes deny access. Responses use no-store and no cookies.
- 28 live authenticated checkpoints: password login, ownership protection, indexed
  cloud notes, sourced answer, downloads disabled, Trash/restore/purge and cleanup.
- Provider startup records confirmed a newer server instance after requested
  restart. Owner login, cloud guide note and conversation persisted. Provider logs
  can update asynchronously and PIDs can be reused; use full startup timestamps/
  generation evidence, not PID alone. API reload acknowledgement alone is not proof.
- A Getting started.md guide and explicitly labelled demonstration remain. Only
  generated temporary test files were purged; no existing owner data was deleted.
- Earlier local browser suites passed ten cloud-only and thirteen legacy checks.
  Live Chromium UI automation did not load the page: its workspace browser lacks
  trust for the platform HTTPS proxy CA. No bypass/shared-profile mutation was used.
  Do not claim live browser screenshots or browser UI checks passed.

## Future changes and maintenance

Inspect runtime network/credential readiness before operations. The application
network addition is already published; do not reapply/publish it again. PA_API_TOKEN
remains destination-bound only to www.pythonanywhere.com. Never print or copy it.
Keep any login credentials and bearer sessions out of commands, files and logs.

Read provider state before updates and preserve source/data. Upload only intended
runtime files, read back hashes, then reload. Test affected real routes. Avoid
concurrent workers using the data directory. If overlapping reload causes a flock
conflict, use the provider's cold disable/enable cycle; never delete server.lock or
bypass locking. Scope log reads to this site's known paths and avoid raw log dumps.

The free-site expiry is 5 December 2026. Periodic renewal, scheduled maintenance
and independent backups are not automated. File payload quota is separate from
512 MiB advertised total account disk and database/index/backup overhead. Initial
home allocation measured about 41.2 MiB, not an authoritative quota reading.

Server backups/restores remain offline operations in backup.py. Restart persistence
is verified; entire-provider loss/recovery is not. No paid upgrade, billing mandate,
scheduler or independent backup service was enabled. Hosting serves normal requests
without an active chat; changes and maintenance need an authorized active session.
