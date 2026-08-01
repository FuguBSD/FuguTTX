# Inference and Quantization

The TTX agent must operate on OpenBSD with 16 GB RAM or less, on the CPU only.

## Runtime

The runtime is the `misc/llama.cpp` port (`pkg_add llama.cpp`), CPU only. The port is maintained: imported in January 2025, it follows the upstream releases. It builds on twelve architectures: aarch64, alpha, amd64, arm, hppa, i386, mips64, mips64el, powerpc, powerpc64, riscv64, and sparc64. Dependencies: `devel/libggml`, `net/curl`, `cmake`, `ninja`. Upstream has the MIT license, with `PERMIT_PACKAGE = Yes`.

## Format and quantization levels

The distribution format is GGUF. Each release has three quantization levels:

| Level | Purpose | Validation |
|---|---|---|
| **Q4_K_M** | Canonical release | Full evaluation suite |
| **Q5_K_M** | Machines with more memory | Smoke validation only |
| **Q3_K_M** | The smallest machines | Smoke validation only |

## Memory fit in 16 GB

- 4B at Q4_K_M: approximately 2.5–3 GB of weights.
- 8B at Q4_K_M: approximately 4.5–6 GB of weights.
- KV cache: approximately 0.5–2 GB at 4K–8K context.
- Runtime overhead: approximately 0.5–1 GB.

Both sizes fit with a large margin. A 13B-class model fits in memory, but it is too slow on the CPU.

## Performance

CPU llama.cpp is limited by memory bandwidth. Consumer hardware gives approximately 10–15 tokens/s for a 7B-class model. **No OpenBSD-specific tokens/s benchmark exists in public.** FuguTTX measures this first-hand with `llama-bench` on target hardware. FuguTTX publishes the results in Phase 2 ([roadmap](roadmap.md)).

## Quantization procedure

`ttx-quant` wraps `convert_hf_to_gguf.py` and `llama-quantize` from llama.cpp. Conversion is CPU-bound. It runs on the operator machine. No GPU is necessary.

## Development loop

Local iteration uses llama.cpp with Metal on Apple Silicon. The artifact that ships is the GGUF file validated on OpenBSD CPU. The same runtime serves development and production. What is validated is what ships.

## Release integrity

Each released GGUF file ships with a SHA256 manifest, signed with `signify(1)`. This matches how OpenBSD distributes sets and packages. See [licensing and release](licensing.md).
