# Inference and Quantization

The TTX agent must operate on OpenBSD with 16 GB RAM or less, on the CPU only.

<a id="inf-runtime"></a>

## Runtime

The runtime is the `misc/llama.cpp` port (`pkg_add llama.cpp`), CPU only.
The port is maintained: imported in January 2025, it follows the upstream releases.
It builds on twelve architectures: aarch64, alpha, amd64, arm, hppa, i386, mips64,
mips64el, powerpc, powerpc64, riscv64, and sparc64. Dependencies: `devel/libggml`,
`net/curl`, `cmake`, `ninja`. Upstream has the MIT license, with `PERMIT_PACKAGE = Yes`.

`llama-server` serves the agent with three settings that the harness requires: the
JSON-schema/grammar constraint on tool calls, prompt caching for a byte-stable prefix,
and context shift off.
The [harness](harness.md) states the reasons.

`devel/libggml` sets `-DGGML_VULKAN=on` for amd64 and aarch64. The aarch64 package
therefore installs a Vulkan back end, `libggml-vulkan.so`. On Apple Silicon that back
end loads, the Vulkan loader enumerates no device, and inference runs on the CPU. The
runtime prints no error.
An operator must not read a successful start as evidence of GPU use.
The reason is that OpenBSD has no kernel driver for the Apple GPU. See
[OpenBSD and the Apple GPU](../docs/research/openbsd-apple-silicon-gpu.md).

<a id="inf-format"></a>

## Format and quantization levels

The distribution format is GGUF. Each release has three quantization levels:

| Level | Purpose | Validation |
| --- | --- | --- |
| **Q4_K_M** | Canonical release | Full evaluation suite |
| **Q5_K_M** | Machines with more memory | Smoke validation only |
| **Q3_K_M** | The smallest machines | Smoke validation only |

<a id="inf-memfit"></a>

## Memory fit in 16 GB

- 4B at Q4_K_M: approximately 2.5–3 GB of weights.
- 8B at Q4_K_M: approximately 4.5–6 GB of weights.
- KV cache: approximately 0.5–2 GB at 4K–8K context.
- Runtime overhead: approximately 0.5–1 GB.

Both sizes fit with a large margin.
A 13B-class model fits in memory, but it is too slow on the CPU.

<a id="inf-perf"></a>

## Performance

CPU llama.cpp is limited by memory bandwidth.
Consumer hardware gives approximately 10–15 tokens/s for a 7B-class model.
**No OpenBSD-specific tokens/s benchmark exists in public.** FuguTTX measures this
first-hand with `llama-bench` on target hardware.
FuguTTX publishes the results.

Token generation reads all weights for each token.
Memory bandwidth therefore sets a hard ceiling.
A STREAM measurement gives the Apple M1 CPU 59 GB/s and the M1 GPU 60 GB/s, which is
about 85 percent of the 67 GB/s specification peak
([arXiv 2502.05317](https://arxiv.org/html/2502.05317v1), 7 February 2025). A 2.5 GB
Q4_K_M file therefore has a ceiling of 23.6 tokens/s on an M1. The ceiling is the same
for the CPU and for the GPU, because the two engines share one memory system.
Do not use the 68.25 GB/s specification figure as a ceiling, because no engine reaches
it.

The machine sets the ceiling.
OpenBSD lists three Mac mini models: M1 (2020), M2 (2023), and M2 Pro (2023). The same
STREAM study measures the M2 CPU at 78 GB/s, which is 32 percent above the M1. The M2
Pro has a specification peak of 200 GB/s, and no measured figure exists for it.

| Chip | Measured CPU | Ceiling for a 2.5 GB Q4_K_M file |
| --- | --- | --- |
| M1 | 59 GB/s | 23.6 tokens/s |
| M2 | 78 GB/s | 31.2 tokens/s |
| M2 Pro | not measured | approximately 68 tokens/s, extrapolated |

A change of target machine therefore gains more than a GPU can, and it needs no new
code.

<a id="inf-latency"></a>

### Latency budget

Tokens/s alone does not bound the user experience.
An agentic step ingests tool output on each turn, and CPU prompt processing is the slow
axis. A generation ceiling can hold while a task still takes too long.
An end-to-end budget therefore governs:

- **The reference task** is one agentic scenario from the evaluation suite: “Block
  inbound SSH, except from 10.0.0.0/8, in pf.conf,” up to the confirmation prompt.
- **The budget:** the reference task must complete in **5 minutes or less** on the M1
  reference machine, at Q4_K_M, through the harness.
- The measurement covers full agent turns: prompt processing, generation, and tool time,
  per turn and per task.
  `llama-bench` numbers do not substitute for a full-turn measurement.
- The budget is a pre-registered release bar ([evaluation](evaluation.md)). The HTTP
  timeout of the harness derives from the same measurements ([harness](harness.md)).

The budget is a starting value.
Only a human changes it, with a recorded reason, before a measurement runs.

<a id="inf-arm64"></a>

### aarch64 build defect

The OpenBSD aarch64 package of `devel/libggml` is not tuned for the target CPU. The port
sets `-DGGML_NATIVE=OFF` for all architectures.
It sets `-DGGML_CPU_ALL_VARIANTS=on` for amd64 only.
It never sets `GGML_CPU_ARM_ARCH`, and it passes no `-mcpu` value and no `-march` value.
The aarch64 package is therefore built for baseline armv8-a.

Three effects follow.
`__ARM_FEATURE_DOTPROD` stays undefined, so each `ggml_vdotq_s32` expands to six NEON
instructions in place of one `SDOT`. ggml does no runtime ARM feature detection, so the
loss cannot be recovered at run time.
The aarch64 package installs one untuned `libggml-cpu.so`, and the amd64 package
installs fourteen tuned variants.

The OpenBSD kernel exports `HWCAP_ASIMDDP` on this hardware.
The defect is in the port, and not in the kernel.

FuguTTX must do this work:

1. Run `llama-bench` on the target machine with the package as it ships.
2. Rebuild `devel/libggml` with `-DGGML_CPU_ARM_ARCH=armv8.4-a+dotprod+fp16`.
3. Run `llama-bench` again, and record the difference.
4. Send both results to the port maintainer.

GPU work must not start without these results.

<a id="inf-quant"></a>

## Quantization procedure

`ttx-quant` wraps `convert_hf_to_gguf.py` and `llama-quantize` from llama.cpp.
Conversion is CPU-bound.
It runs on the operator machine.
No GPU is necessary.

<a id="inf-devloop"></a>

## Development loop

Local iteration uses llama.cpp with Metal on Apple Silicon.
The artifact that ships is the GGUF file validated on OpenBSD CPU. The same runtime
serves development and production.
What is validated is what ships.

<a id="inf-nogpu"></a>

## GPU inference is not available on the target

Decision [D2](decisions.md) keeps inference on the CPU. A research note gives the full
evidence: [OpenBSD and the Apple GPU](../docs/research/openbsd-apple-silicon-gpu.md), 1
August 2026. Four facts control the result.

- OpenBSD has no kernel driver for the Apple GPU. A Mac mini M1 prints
  `"gpu" at simplebus0 not configured` at boot.
  `apldrm(4)` does mode setting only, and it creates no render node.
- The one Apple GPU driver that exists anywhere is Rust code in a branch that Asahi
  Linux rebases. The OpenBSD kernel has no Rust, and mainline Linux has no `drm/asahi`.
- No OpenBSD developer shows public work on an Apple GPU driver.
- Token generation would gain nothing on an M1, because the CPU and the GPU measure the
  same memory bandwidth.
  On an M2 the gain would be about 17 percent.
  Prompt processing would gain more, but the cheaper gain on that axis is the aarch64
  build fix above.

OpenBSD does support GPU offload on amd64 with an AMD card, through the ggml Vulkan back
end. D2 is therefore “CPU only on the target hardware”.
D2 is not “OpenBSD has no GPU path”.

<a id="inf-integrity"></a>

## Release integrity

Each released GGUF file ships with a SHA256 manifest, signed with `signify(1)`. This
matches how OpenBSD distributes sets and packages.
See [licensing and release](licensing.md).
