# Hosting-account access — 5 November 2026

PythonAnywhere API access is now authenticated using the owner's securely supplied
`PA_API_TOKEN` binding. The current runtime reports the binding ready and restricts
its destination to `www.pythonanywhere.com`. `PA_USERNAME` supplies the account name.
Never print the token, put it in chat, a repository or command-line argument, or
copy the provider's injected `API_TOKEN` out of its runtime.

Verified provider reads:

- 100 daily console CPU seconds; no existing traditional webapp or console.
- Current system image `innit`; Python 3.13, 3.12, 3.11, 3.10 and 3.9 available.
- No existing Haven deployment paths before staging.
- The minimal source ZIP and fail-closed WSGI template were uploaded under the
  private `~/haven-install/` directory and read back for exact-byte verification.

The advertised free plan has 512 MiB total private disk and one traditional webapp.
No plan upgrade, card, paid task, experimental ASGI service or charge was requested.
Actual installed footprint, home filesystem compatibility, public HTTPS and
restart/recovery still need provider-side checks.

## Console boundary

The [official API documentation](https://help.pythonanywhere.com/pages/API/#consoles)
states that API console creation does **not** start its process. Connecting to the
console in the owner's authenticated browser starts it. No browser-control tool
is available in this session. Prepare the script, upload it, verify it and create
the exact console before asking for that owner action. The owner enters their own
Haven password only into the console's hidden `getpass` prompt, never into chat.

The bootstrap installs pinned binary dependencies with no pip cache, runs synthetic
WSGI and filesystem checks, then initializes the password hash privately. Its
status file contains stages and measurements, never plaintext credentials.
The public WSGI entry point refuses to initialize an unclaimed workspace.

## Resume procedure

1. Read `STATUS.md` and ignored `.private-hosting/deployment-state.json`.
2. Recheck runtime readiness and the prepared console's private
   `~/haven-install/status.json`. Do not create duplicate consoles or repeat uploads.
3. If initialization is incomplete, diagnose its recorded safe stage. Ask only for
   the outstanding owner credential/browser action, with the prepared direct link.
4. Once ready, inspect actual dependency footprint and disk headroom. Preserve any
   newly existing site/configuration. Configure the single traditional WSGI site,
   force HTTPS, and serve no public mapping to source, data or installer directories.
5. Verify the real route, owner claimed state, authentication boundary and persistent
   filesystem/restart behavior before reporting a usable service. No configured
   automatic renewal or independent disaster recovery is currently verified.

The read-only preflight is `python3 deploy/pythonanywhere_preflight.py --report
.private-hosting/preflight.json`. Its synthetic tests are separate from the live
account checks. The scoped deployment client forbids billing/always-on operations,
other accounts' sites and direct owner-data uploads.
