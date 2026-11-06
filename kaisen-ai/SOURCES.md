# Official evidence — checked 6 November 2026

Public evidence was read through the available agent-reach/Jina web reader. Some
reader responses may be cached. Pinned revisions/digests are concrete observations,
not proof of the newest available release or of this model's task performance.

## Model

- [Official model card](https://huggingface.co/Qwen/Qwen3-8B-GGUF): 8.2B parameters,
  thinking/non-thinking modes, 32,768 native context tokens; up to 131,072 with YaRN
  caveats. The Q4 file's metadata differs on context size; planning uses the more
  conservative card figure and a smaller actual pilot context.
- [Pinned publisher LFS pointer](https://huggingface.co/Qwen/Qwen3-8B-GGUF/raw/7c41481f57cb95916b40956ab2f0b139b296d974/Qwen3-8B-Q4_K_M.gguf):
  5,027,783,488 bytes; SHA-256
  d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785.
- [Pinned license](https://huggingface.co/Qwen/Qwen3-8B-GGUF/raw/7c41481f57cb95916b40956ab2f0b139b296d974/LICENSE): Apache-2.0.
- [Pinned usage card](https://huggingface.co/Qwen/Qwen3-8B-GGUF/raw/7c41481f57cb95916b40956ab2f0b139b296d974/README.md): included chat template/--jinja,
  thinking sampling temperature 0.6 / top_p 0.95, caution against greedy decoding and
  retaining hidden reasoning in historical messages. Reduced context/output can
  reduce complex reasoning performance. No performance benchmark was run here.

The weights have not been downloaded. An actual downloaded-file checksum and
inference still need verification. Runtime availability alone is not a working AI.

## Runtime

- [Official CPU release](https://github.com/ggml-org/llama.cpp/releases/tag/b12175),
  a nightly/prerelease, commit 9a1d03c7ca2ca279feca8afd29d40c8e0fff9b6d.
- [Official asset metadata](https://api.github.com/repos/ggml-org/llama.cpp/releases/assets/717719273):
  llama-b12175-bin-ubuntu-x64.tar.gz, 23,047,234 bytes, SHA-256
  0296899717946797a68c47ad0339ff20d3f868ea0ebcb7532e365c8575b78849.

This runtime archive was downloaded into the cloud workspace, checked against that
size/digest, safely extracted, and tested with --version/--help. Model inference
was not run. The runtime is not a daemon or permanent hosting service.

## One petabyte of object storage

[Official Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/)
advertises Standard USD 0.015/GB-month, Infrequent Access USD 0.01/GB-month,
10 GB-month Standard free allowance, plus operations. IA also charges
USD 0.01/GB retrieved and has a 30-day minimum.

For an illustrative full month and decimal 1 PB = 1,000,000 GB:

| Class | Storage-only monthly USD |
|---|---:|
| Standard | 15,000 (14,999.85 if all 10 free GB-month are available) |
| Infrequent Access | 10,000 before retrieval/requests |

These are advertised list-price calculations, not a quote or purchased capacity.
They exclude compute, requests, backups, taxes, FX and negotiated rates. A full PB
read from IA would add approximately USD 10,000 at the observed retrieval price.
No zero-cost 1 PB option was established. Archive storage does not supply model RAM.
