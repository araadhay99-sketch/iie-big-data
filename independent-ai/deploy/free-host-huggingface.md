# Hugging Face free-host feasibility

Checked 4 November 2026 using Agent Reach’s documented Jina Reader route. Read-only research; no account, token, bucket, Space, deployment or billing configuration created. This is a feasibility note, not a verified deployment.

## Decision

**Potential free hosting/storage route, but not a verified drop-in host for Haven.** The official free storage allowance is promising. The existing application needs filesystem and database guarantees that this bounded review did not establish for Storage Bucket mounts. Do not mount a bucket and assume that SQLite WAL, `fcntl.flock`, atomic replacement and `fsync` are safe.

## Evidence

| Official source | Observed fact | Consequence |
| --- | --- | --- |
| [Storage limits](https://huggingface.co/docs/hub/storage-limits#storage-plans) | Free users and organizations receive **100GB private storage**. The page explicitly says limits apply to models, datasets, buckets and other Hub storage types. | A documented private-storage free tier exists; this does not prove the owner has an account, available quota, or an enabled bucket. |
| [Storage limits](https://huggingface.co/docs/hub/storage-limits#private-storage-pay-as-you-go) | Additional pay-as-you-go storage is described for paid plans. | Stay on the free account/tier; do not enable paid plans, paid hardware, add-ons or billing. Account-specific enforcement and over-quota behavior have not been checked. |
| [Storage Buckets](https://huggingface.co/docs/hub/storage-buckets) | Buckets are **S3-like object storage**, powered by Xet, mutable and non-versioned. Public or private visibility can be chosen at creation. | A private bucket is the relevant candidate for personal files. Public community storage is inappropriate for private Haven data. |
| [Storage Buckets](https://huggingface.co/docs/hub/storage-buckets#deleting-files) | Deletions are immediate and permanent; there is no recovery through bucket version history. | A bucket alone is not a backup/version-history system. |
| [Storage Buckets](https://huggingface.co/docs/hub/storage-buckets#tracking-changes) | Mounts/filesystem layers may follow change events; events are retained for about 15 minutes and clients must re-list after longer gaps. | The existence of a filesystem interface or change stream does not establish a POSIX disk contract or database correctness. |

## Remaining launch gates

1. Confirm the exact free Space configuration against the [Spaces overview](https://huggingface.co/docs/hub/spaces-overview), its HTTPS URL, sleep/restart behavior and whether source visibility meets the owner’s requirements. Free hosting must not be presented as always-on infrastructure.
2. Keep personal data and secrets out of the Space source repository. Private bucket visibility does not authenticate a separately public application; Haven’s own authentication must protect every data route. A host’s public-code visibility and an app’s private data are separate concerns.
3. Obtain an owner-authorized Hugging Face account and narrowly scoped access through a supported secure connection. No account or credential is currently available here. Do not paste tokens into source, public files, chat logs or browser storage.
4. **Filesystem blocker:** the three reviewed documents do not establish mount support/correctness for `flock`, SQLite WAL shared-memory/locking, crash-safe `fsync`, or atomic rename/replace. They do not establish that a mounted bucket is an appropriate live SQLite database disk.
5. A possible redesign would use cloud-local SQLite and explicitly persisted, verified snapshots in private object storage, with a documented single-writer and crash-recovery protocol. That is additional engineering and testing, not an existing guarantee; it must account for a Space stopping between a write and a snapshot. No such implementation has been made or validated in this audit.

## Bounded conclusion

Hugging Face is a credible candidate for a small, sleeping, free cloud application with private object storage. The 100GB free private-storage allowance is documented. Secure browser access, authentication, compatible durable writes, recovery, free-tier account configuration and a working end-to-end deployment remain unverified. **Do not promise that the present Haven implementation is deployable safely and durably on bucket mounts.**

Sources were retrieved via `https://r.jina.ai/https://huggingface.co/...`; the linked upstream pages are authoritative. Advertised entitlements are not evidence of a configured account or tested service.
