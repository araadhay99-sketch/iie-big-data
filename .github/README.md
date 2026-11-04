# Haven — private cloud AI and storage

A basic, single-owner AI workspace with server-side file storage. Intelligence is
deliberately limited for now: a local document-relevance model and intent classifier.

The default cloud-only mode keeps processing, files, indexes and chat history on
the server. The browser uses an in-memory login token; it creates no application
cookies or browser databases, and file downloads are disabled. You can create
cloud notes without first saving a file on a laptop.

## Current status

The application and hosting-compatibility code are implemented and tested. **This
repository contains the source; it is not a running cloud service.** GitHub Pages
cannot run this Python backend, and this repository is not a private upload bucket.
No production URL, paid hosting or permanent storage service has been provisioned.

## Included

- Private password setup/login and memory-only browser sessions.
- Upload, server-side notes, sourced file answers, Trash/restore/permanent deletion.
- Storage quotas, backup/restore, restart and interrupted-write recovery.
- A responsive browser interface with local assets and no external AI/storage API.
- ASGI and optional WSGI hosting entry points; deployment configuration examples.

The cloud-only application has passed 19 backend tests and 10 browser checks. An
additional WSGI compatibility test passed. These are local/cloud-workspace checks,
not proof of a public host's availability, durable storage or full security certification.

See [server documentation](../independent-ai/README.md),
[current deployment status](../independent-ai/STATUS.md), and
[free-host research](../independent-ai/deploy/free-host-options.md).

No application installation or model download is intended on the owner's laptop.
The hosting server needs its dependencies installed once. A browser still uses RAM
and may manage its own cache; the application does not promise zero OS-level writes.
