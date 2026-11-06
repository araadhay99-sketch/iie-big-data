# Kaisen — personal science AI prototype

This is a restarted project for computers, maths, physics, chemistry and biology,
under a **20,000,000,000-byte project budget**. It is computational groundwork and
a prepared local-model pipeline. **The language-model weights are not installed,
model reasoning has not been tested, and no 1 PB cloud has been provisioned.**

The objective is accurate, useful answers supported by calculations and sources.
There is no claim of complete knowledge, unlimited work, superhuman reliability or
performance exceeding Codex. Those claims cannot follow from code or disk capacity.

## What works now

- Deterministic tools: bounded symbolic maths, three SI physics formulas, neutral
  reaction balancing, DNA/RNA statistics/standard-code translation, and Python AST
  inspection. Each reports assumptions and rejects unsupported inputs. Code is not
  executed by the inspection tool; this is not a general computer-control agent.
- Streamed UTF-8 text ingestion, SHA-256 provenance and SQLite full-text retrieval.
  Invalid input/quota exhaustion rolls back the current ingestion without deleting
  previous sources. Managed writers share a project lock and conservative quotas.
- A pinned CPU inference runtime is actually installed in this cloud workspace:
  llama.cpp build b12175, 58 MB extracted. Publisher checksum, --version and --help
  passed. This verifies the runtime executable, **not language-model inference**.
- A local-model adapter can request allowlisted computation tools and cite selected
  passages. Its tests use simulated backend responses; no real model benchmark ran.
- 45 software tests passed. A separate synthetic 32 MiB text file indexed in 1,025
  chunks; a final passage was found with about 0.53 MB peak Python heap. The measured
  process peak RSS was about 17.2 MB. This is not a petabyte-scale test.

## Model and resource decision

Experimental first candidate: official **Qwen3-8B Q4_K_M**, 5,027,783,488 bytes,
Apache-2.0, pinned revision/checksum in kaisen/model-manifest.json. Metadata was verified
against publisher sources on 6 November 2026. It is a documented starting candidate,
not a claim to be the newest or strongest possible model.

The current development workspace has a 32 GiB RAM limit and roughly four CPU cores.
It could support a bounded trial, but is temporary and has no configured public
inference ingress. CPU speed and answer quality are unmeasured. The existing free
PythonAnywhere site has 512 MiB of account disk and cannot hold this 5.03 GB model.
A persistent personal model service needs a suitable separately authorized host.

The prepared server uses loopback only, one slot, four threads, an 8,192-token
context and at most 2,048 generated tokens. Long reasoning may hit those budgets;
incomplete output is not reported as a complete answer. Context can only be changed
after resource/quality tests. Archive size does not increase a model's context.

## Operator commands — cloud/server only

No laptop installation is requested. The assistant should run these commands in
an authorized cloud execution environment, not turn them into owner technical work.

```sh
python -m kaisen status
python -m unittest discover -s tests -v
python -m kaisen tool math '{"operation":"differentiate","expression":"x**3+2*x"}'
python -m kaisen tool chemistry '{"operation":"balance","reaction":"Fe + O2 -> Fe2O3"}'
python -m kaisen tool biology '{"operation":"translate","sequence":"ATGGCTTAA","kind":"DNA"}'
python -m kaisen ingest /authorized/cloud/path/notes.txt
python -m kaisen search 'question about the notes'
```

The pinned runtime is already installed in this workspace. scripts/install_runtime.py
exists for a fresh environment; it preserves an existing installation rather than
silently replacing it. Model installation is a separate, currently blocked step:

```sh
python -m kaisen download-model
python -m kaisen serve
python -m kaisen chat 'A question supported by the notes or calculation tools'
```

Download uses TLS, a revision-pinned publisher URL, exact size and SHA-256, temporary
files, and atomic publication. It never substitutes arbitrary weights. Serve refuses
missing/corrupted weights. No model server is started automatically on import.

## Storage and operational limits

The 20 GB cap covers project files, weights, installed runtime and managed indexes.
Shared preinstalled system libraries are outside that accounting. The cooperative
write protocol cannot prevent an owner or unrelated process manually writing extra
files; it is not a kernel/filesystem quota. Index/journal headroom is conservative.
The default index budget is 1 GB including reserved overhead, not a 1 PB index.
Input documents are streamed; originals are not copied wholesale into the project.
Only UTF-8 text is supported currently, not arbitrary PDFs, images, archives or video.

One decimal PB is 1,000,000 GB, fifty thousand times the project disk cap. If it is
external object storage, it requires a separate account, capacity and money. If it
means RAM, neither this machine nor the 20 GB disk budget supplies it. The model's
context is finite and selected passages must fit it; it cannot read an entire PB
into one reasoning turn.

At observed Cloudflare R2 list pricing, 1 PB Standard storage alone is about
USD 15,000/month before request costs, taxes, compute and backups. No such account,
spending, billing mandate or capacity is authorized/configured. See SOURCES.md.

The ₹0 spending boundary remains in force. Existing Haven stays available while
this separate prototype is developed. No paid service or autonomous ongoing
operation has been configured. See STATUS.md for exact remaining blockers.
