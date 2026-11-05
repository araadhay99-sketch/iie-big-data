# PythonAnywhere operation — 5 November 2026

Current phase: **site enabled; external verification blocked by workspace policy**.
Read STATUS.md and ignored .private-hosting/deployment-state.json first. That file
contains account-specific URLs and measurements; never commit it or application
data. Do not repeat initialization, console creation or website creation.

## Installed configuration

- Traditional WSGI / Python 3.13, using ~/haven-venv and source ~/haven.
- Data ~/haven-data, private directory; 64 MiB file payload quota.
- Cloud-only mode enabled; Ollama unset; BLAS thread counts limited to one.
- Provider WSGI path: /var/www/<username>_pythonanywhere_com_wsgi.py.
- WSGI template uploaded and read back exactly; it refuses an unclaimed workspace.
- HTTPS enforced; no provider static-file mapping exposes source, installer or data.
- Provider native certificate metadata exists; actual TLS route not yet checked.
- Free-site expiry reported as 5 December 2026. No renewal automation is configured.

The provider create API required `python313`; configuration metadata returns
`3.13`. Live OPTIONS advertises the configuration representation, while the
[official create example](https://help.pythonanywhere.com/pages/API/#webapps)
uses `python310` for Python 3.10. One initial creation request with `3.13` returned
400 and created no site; the corrected format succeeded. Do not recreate the site.

## Next verification

The network draft adds the application hostname only, retaining existing custom
hosts and leaving PA_API_TOKEN scoped to www.pythonanywhere.com. Saving the draft
did not apply or publish it. After the owner reviews/saves/publishes it:

1. Inspect runtime readiness and the executor network snapshot before requests.
2. GET the actual HTTPS /api/session: expect authenticated=false,
   setup_required=false and cloud_only=true. Check page/assets and no-store headers.
3. Confirm /api/files and /api/messages reject anonymous access. Confirm HTTP
   redirects to HTTPS without submitting credentials over plaintext HTTP.
4. Exercise real authorized login, cloud note, sourced answer, Trash/restore/purge
   using clearly synthetic data only. Keep credentials/tokens in memory and out of
   shell arguments, files, screenshots, command output and committed records.
5. Check a provider reload/restart preserves server data. The app holds an exclusive
   process lock; overlapping workers may refuse startup. If necessary use a cold
   disable/enable cycle and inspect only this site's error/server logs. Do not
   delete server.lock or bypass process locking. Preserve all owner content.

Provider-side synthetic setup/login/upload/answer/download-blocking and reopened
file/history checks passed in a temporary home-filesystem workspace, which was
removed. Worker startup and an empty error log were independently verified. Those
results do not replace real public-route tests.

The owner reported difficulty with invisible console input and explicitly
authorized assistant entry. Initialization then completed through the hidden
prompt. Do not retain or repeat that credential; any future credential entry must
use an appropriate secure mechanism and valid owner authorization.

No independent backup service, scheduled tasks, maintenance agent or automatic
renewal has been provisioned. Server backups/restores remain an offline procedure
in backup.py. Provider persistence, application checks and disaster recovery are
separate claims. Do not describe this free pilot as maintenance-free or permanent.
