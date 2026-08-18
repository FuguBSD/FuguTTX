# Draft plan: Apple GPU support for OpenBSD on the Mac mini

**Date: 1 August 2026. Status: draft, research only.
This document is not part of the specification.
It commits FuguTTX to nothing.
It describes what the work would look like, and what it would cost.**

The companion research note gives the evidence for the current state:
[OpenBSD and the Apple GPU](openbsd-apple-silicon-gpu.md).
That note recommends that nobody starts this work.
This document exists so that the recommendation is an informed one.
A reader must be able to see the shape of the work before a reader rejects it.

## 1. Scope

Three machines are in scope.
OpenBSD lists these three Mac mini models, and no others.

| Machine | SoC | GPU | GPU cores | Memory bandwidth |
| --- | --- | --- | --- | --- |
| Mac mini (M1, 2020) | t8103 | AGX G13G | 8 | 68.25 GB/s |
| Mac mini (M2, 2023) | t8112 | AGX G14G | 10 | 100 GB/s |
| Mac mini (M2 Pro, 2023) | t6020 | AGX G14S | 16 or 19 | 200 GB/s |

The GPU generation names come from the Asahi driver source and from the device-tree
binding patch that adds the `agx-g14s`, `agx-g14c`, and `agx-g14d` compatibles.
The mapping of `g14s` to the M2 Pro is an inference from the order of that patch.
Confirm it before any work starts.

**In scope:** compute on the GPU, for llama.cpp.

**Not in scope:** accelerated X or Wayland, OpenGL, video decode, the Neural Engine, M3
and later machines, and any machine that is not a Mac mini.

The distinction matters, because it removes work.
A desktop needs a display pipeline, a window-system integration, and OpenGL. `apldrm(4)`
already drives the display.
An inference workload needs only this: submit a compute job, and read the result back.

## 2. What “support” must mean

Three end states can satisfy the goal.
They differ by a large factor in cost and in risk.

| Option | What it is | Code cost | Risk |
| --- | --- | --- | --- |
| **A. Full Vulkan** | A kernel driver with the Linux `asahi_drm.h` UAPI, plus Mesa Honeykrisp built in xenocara. | Highest | Lowest. The user space is written, conformant, and tested. |
| **B. Compute-only Vulkan** | The same, but the kernel implements only the ioctls that compute queues need. Graphics queues stay absent. | High | Medium. Mesa expects a full device. A partial device can fail in ways nobody upstream has seen. |
| **C. Bespoke compute driver** | A small kernel driver with its own ioctl interface, plus a new ggml back end that talks to it directly. No Mesa, no Vulkan. | Lowest | Highest. No conformance suite, no upstream, no second user. Every shader must be written and validated by FuguTTX. |

Option C looks attractive, because the goal is narrow.
It is a trap. The value of Honeykrisp is not the code.
The value is that thousands of Vulkan CTS tests and one llama.cpp back end already
exercise it. Option C throws that away and replaces it with work that only FuguTTX can
validate.

**This plan assumes option A.** Option B is a fallback that a reader can consider after
gate G3.

## 3. What OpenBSD already has

The starting position is better than the current state suggests.

| Asset | State | Why it matters |
| --- | --- | --- |
| `rtkit.c` | 999 lines of C in `sys/arch/arm64/dev` | The AGX firmware coprocessor speaks RTKit. The Asahi documentation states that “firmware communication uses the RTKit framework common to other ASCs”. OpenBSD has this in C already. |
| `apldcp(4)` and `apldrm(4)` | In the tree since January 2024 | These prove the whole model. Kettenis ported an RTKit-based Apple coprocessor driver from the Asahi tree into OpenBSD, in C. The AGX is the same class of problem. |
| `apldart(4)` | In the tree | The Apple IOMMU. The GPU needs address translation for its buffers. |
| arm64 pmap | In the tree | The UAT “is essentially the ARM64 MMU, and uses identical page tables”. The page-table format is not new work. |
| DRM shim | Linux 6.18.22 | `drm_gpuvm.c`, `drm_exec.c`, `drm_gem.c`, `drm_prime.c`, and the GPU scheduler are present in C. |
| Mesa `asahi` and Honeykrisp | Vendored in xenocara at Mesa 25.0.7 | The user-space driver source is already in the tree. No import is necessary. |
| `vulkan-loader`, `shaderc`, ggml Vulkan | In ports; `libggml-vulkan.so` ships on aarch64 | The whole stack above the driver is packaged and works on OpenBSD amd64 with AMD cards. |

The one missing layer is the kernel driver.
Everything above it and everything below it exists.

## 4. The gaps

| Gap | Size | Notes |
| --- | --- | --- |
| No AGX kernel driver | **20,860 lines of Rust**, 45 files, measured 1 August 2026 | The only implementation anywhere. It lives in the `asahi-wip` branch, which rebases. |
| No Rust in the OpenBSD kernel | Policy is unwritten; `src` contains none | This forces a rewrite in C. See section 5. |
| `drm_gem_shmem_helper.c` | Absent | The Asahi GEM layer depends on it. |
| `drm_syncobj` fd paths | Present but stubbed | `drm_syncobj_get_fd()` and `drm_syncobj_fd_to_handle()` return `-ENOSYS`. |
| dma-buf sync-file ioctls | Absent | Mesa needs `DMA_BUF_IOCTL_IMPORT_SYNC_FILE` and `DMA_BUF_IOCTL_EXPORT_SYNC_FILE`. |
| Mesa targets the unstable UAPI | Mesa 25.0.7 includes `unstable_asahi_drm.h` | It refuses to run unless the unstable version matches. Mesa main uses the stable `asahi_drm.h`. A xenocara Mesa bump is necessary. |
| No xenocara build rules for Apple Vulkan | `lib/mesa/mk` has no `libvulkan_asahi` | The source is vendored, but nothing builds it. |
| Firmware ABI follows macOS | Not versioned by Asahi, tracked by hand | The Asahi rule is that the ABI is “whatever macOS does”. Each macOS firmware release can break it. |
| GPU init is moving into m1n1 | Asahi did this in the Linux 7.1 cycle | m1n1 1.6.0 needs Rust for its stage 2 build. The OpenBSD port is at 1.5.2. |

## 5. Strategy

Four strategies exist.
Three of them fail for stated reasons.

| Strategy | Verdict |
| --- | --- |
| **S1. Allow Rust in the OpenBSD kernel, then port `drm/asahi`** | Rejected. It needs a project-wide policy change that no OpenBSD developer has proposed. It also makes base depend on a package toolchain, which conflicts with the rule that base builds base. The gain is small, because the Rust driver depends on Rust DRM abstractions that were still landing in Linux 7.1. |
| **S2. Rewrite `drm/asahi` in C, keep the Linux UAPI** | **Recommended.** It matches how OpenBSD already handles Apple graphics. It keeps Mesa usable without a fork. It is 21,000 lines of new C, written against a moving source. |
| **S3. Bespoke compute-only driver with a private UAPI** | Fallback only. It is the smallest kernel change and the largest total risk. Section 2 gives the reason. |
| **S4. Wait for mainline Linux, then take it in a DRM sync** | Rejected. Mainline has no `drm/asahi`. Only the UAPI header is in mainline, since Linux 6.16. The only driver posting is an RFC from 7 March 2023, which patchwork still shows as “New”. OpenBSD also does not need mainline, because it imported the Apple DCP code straight from the Asahi tree. |

## 6. The work, by gate

Each gate has an exit criterion that a machine or a person can check.
A gate that fails ends the effort.
That is the point of the structure.

### G0 — Feasibility, no code

- **Scope:** confirm the SoC-to-GPU mapping for all three machines.
  Survey the firmware ABI versions that the three machines ship.
  Decide between strategy S2 and strategy S3. Find out whether any OpenBSD developer
  will review and commit the result.
- **Exit:** a written decision, and a named reviewer.
- **Stop rule:** no named reviewer means stop.
  Unreviewed kernel code does not enter OpenBSD.

### G1 — Kernel plumbing

- **Scope:** add `drm_gem_shmem_helper.c`. Implement the `drm_syncobj` fd export and
  import paths. Add the two dma-buf sync-file ioctls.
- **Exit:** `inteldrm` and `amdgpu` still work on amd64. The new helpers compile and
  pass their own tests.
- **Note:** this gate has value on its own.
  It helps every DRM driver, and it does not depend on the Apple GPU.

### G2 — Bring-up on the M1

- **Scope:** claim the `gpu` node.
  Set up the UAT page tables.
  Boot the AGX firmware over RTKit.
  Build and send the initialization data structure.
- **Exit:** `dmesg` stops printing `"gpu" at simplebus0 not configured`. The firmware
  answers on the channel.
- **Size:** this is `mmu.rs` (1,654 lines), `initdata.rs` (1,021), `fw/initdata.rs`
  (1,352), `gpu.rs` (1,642), and `channel.rs` (631). Call it 6,000 lines of the hardest
  code in the driver.

### G3 — One compute job

- **Scope:** the work queue, the event and completion path, and the compute queue.
  Submit one trivial compute job and read the result.
- **Exit:** a null compute kernel completes, and the driver reads back the correct
  value.
- **Decision point:** this is where a reader must choose between option A and option B.

### G4 — Memory and recovery

- **Scope:** GPU virtual memory through `drm_gpuvm`, buffer objects, page-fault
  handling, job timeouts, and firmware recovery.
- **Exit:** an injected fault and an injected timeout both recover, with no kernel panic
  and no leak.
- **Warning:** this gate is where a driver becomes safe to give to users.
  A GPU driver that cannot recover from a bad job is a denial-of-service tool.

### G5 — User space

- **Scope:** match the stable `asahi_drm.h` UAPI. Bump Mesa in xenocara past 25.0.7. Add
  the `libvulkan_asahi` build rules and the ICD JSON file.
- **Exit:** `vulkaninfo` on a Mac mini M1 enumerates the GPU.

### G6 — Correctness and compute

- **Scope:** run the Vulkan CTS compute subset.
  Then run `llama-bench` with the ggml Vulkan back end.
- **Exit:** the CTS compute subset passes.
  `llama-bench` reports a GPU device.
  Generated text matches the CPU output within tolerance.
- **Warning:** llama.cpp issue 16188 reported garbage output from Honeykrisp on an M2
  Pro in September 2025. Wrong output is worse than no output, because the harness gives
  system-administration advice.

### G7 — The M2 and the M2 Pro

- **Scope:** add the two further SoC descriptions.
- **Exit:** G3 and G6 pass on all three machines.
- **Size:** small, and this is the best news in the plan.
  The per-SoC files in the Asahi driver are `t8103.rs` at 92 lines, `t8112.rs` at 105
  lines, and `t602x.rs` at 179 lines.
  `hw/mod.rs` holds the 657 shared lines.
  Support for three machines costs little more than support for one.

### G8 — The OpenBSD security model

- **Scope:** review the `drm` pledge promise against the new ioctls.
  Set the device-node permissions.
  Check W^X against the Mesa shader compiler.
  Add an unveil path list for the harness.
- **Exit:** the `ttx` harness runs a GPU inference under pledge and unveil, with no
  promise wider than the CPU path needs.

### G9 — Upstream

- **Scope:** send the driver to tech@. Commit to maintenance across macOS firmware
  releases.
- **Exit:** the driver is committed, or an OpenBSD developer declines it with a reason.
- **Warning:** a driver that lives outside the tree is dead within two DRM syncs.

## 7. Cost

The estimate below is a judgement, and not a measurement.
The basis is stated so that a reader can disagree with it.

| Gate | Estimate | Basis |
| --- | --- | --- |
| G0 | 2 to 4 weeks | Reading and correspondence. |
| G1 | 1 to 2 months | Well-understood porting work against a known upstream. |
| G2 | 4 to 8 months | Firmware bring-up with no documentation. The Asahi work took longer, but it also had to reverse-engineer the hardware. |
| G3 | 2 to 4 months |  |
| G4 | 3 to 6 months | Recovery paths take most of the time in every GPU driver. |
| G5 | 1 to 2 months | Mesa build integration in xenocara, plus a Mesa version bump. |
| G6 | 2 to 4 months | Conformance debugging has no floor. |
| G7 | 1 month | Three small SoC description files. |
| G8 | 2 to 4 weeks |  |
| G9 | Continuous | Maintenance never ends. |

**Total: about 15 to 30 person-months, and then maintenance forever.**

Two facts make the range wide.
The rewrite target moves, because the source branch rebases.
The firmware ABI moves, because it follows macOS.

One person cannot carry the maintenance.
Asahi Linux showed this.
Its GPU work slowed sharply after its maintainers stepped away in 2025.

## 8. Risks

| Risk | Effect | Mitigation |
| --- | --- | --- |
| No OpenBSD developer accepts the code | The work is wasted | G0 stops the effort before any code exists |
| The firmware ABI changes with a macOS release | The driver breaks on updated machines | Pin the firmware version, and test against several |
| The Rust source rebases under the rewrite | Constant re-synchronization | Snapshot one commit, and treat it as frozen |
| The driver produces wrong results, and not crashes | The agent gives wrong advice with confidence | G6 gates on output equality, and not only on speed |
| The gain does not justify the cost | 15 to 30 person-months for little speed | Section 9 |

## 9. Why this plan should not start

The plan is achievable.
It is not worth it, and the arithmetic is not close.

Token generation is bandwidth-bound.
On the M1 the CPU and the GPU measure 59 GB/s and 60 GB/s. The GPU therefore adds
nothing on the axis that an interactive agent uses most.
On the M2 the gain would be about 17 percent.
Prompt processing would gain more, and that gain is real.
It is also available by two cheaper routes.

Ranked by cost, these actions all come before the GPU:

1. Measure the CPU path with `llama-bench`. Nobody has done this on OpenBSD arm64. Cost:
   one afternoon.
2. Rebuild `devel/libggml` with `-DGGML_CPU_ARM_ARCH=armv8.4-a+dotprod+fp16`. The
   aarch64 package ships with no dot-product instructions today.
   Cost: one line, and a port test.
3. Move the target machine to a Mac mini M2 or M2 Pro.
   The M2 Pro has about three times the memory bandwidth of the M1. Cost: one machine,
   and no engineering.
4. Add a BLAS or Arm KleidiAI path for prompt processing on aarch64. Cost: port work,
   and no kernel work.
5. Everything in this document.
   Cost: 15 to 30 person-months.

Action 3 alone beats the whole of this plan on token generation.

## 10. When to reconsider

Any one of these would change the arithmetic.
None of them is under the control of FuguTTX.

- An OpenBSD developer states a plan to write the driver.
  Then FuguTTX helps and tests, and does not lead.
- A C implementation of an AGX driver appears in any project.
  The rewrite is the bulk of the cost, and somebody else would have paid it.
- Asahi lands `drm/asahi` in mainline Linux, and OpenBSD gains kernel Rust.
  Both must happen. Neither is close.
- The model grows past what the CPU can serve, and prompt processing becomes the limit.
  Measure first. Action 1 in section 9 is the test.

## 11. Open questions

- Does the Mac mini M2 Pro use `agx-g14s`? The inference comes from the order of a
  device-tree patch, and not from a statement.
- Which firmware versions do the three Mac minis ship, and how far apart are their ABIs?
- Would OpenBSD accept `drm_gem_shmem_helper.c` and the `drm_syncobj` fd paths on their
  own merits, separately from any Apple work?
  G1 has value even if the rest never happens.
- Does Honeykrisp work correctly on a G14S today?
  llama.cpp issue 16188 says that it did not in September 2025.

## 12. Sources

- OpenBSD arm64 platform page (the three Mac mini models), read 1 Aug 2026 —
  https://www.openbsd.org/arm64.html
- `AsahiLinux/linux` `drivers/gpu/drm/asahi` on `asahi-wip`, line counts measured 1 Aug
  2026 — https://github.com/AsahiLinux/linux/tree/asahi-wip/drivers/gpu/drm/asahi
- Asahi Linux, Apple GPU (AGX) hardware documentation (UAT, RTKit, channels), read 1 Aug
  2026 — https://asahilinux.org/docs/hw/soc/agx/
- Asahi Linux, glossary (RTKit on AGX, ANE, AOP, DCP, AVE, PMP), read 1 Aug 2026 —
  https://asahilinux.org/docs/project/glossary/
- Asahi Linux, Progress Report: Linux 7.1 (GPU init moves into m1n1), 30 Jun 2026 —
  https://asahilinux.org/2026/06/progress-report-7-1/
- patchwork.kernel.org, dri-devel, “[RFC,00/18] Rust DRM subsystem abstractions (&
  preview AGX driver)”, Asahi Lina, 7 Mar 2023, state “New” —
  https://patchwork.kernel.org/project/dri-devel/list/?q=agx&state=*&archive=both
- patchwork.kernel.org, “[12/37] dt-bindings: gpu: apple,agx: Add agx-{g14s,g14c,g14d}
  compatibles”, in the series “arm64: Add initial device trees for Apple M2
  Pro/Max/Ultra devices”, Janne Grunau, 28 Aug 2025 — same listing
- OpenBSD `sys/arch/arm64/dev/rtkit.c`, 999 lines, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/dev/rtkit.c
- OpenBSD `sys/dev/pci/drm/drm_syncobj.c` (stubbed fd paths), read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/dev/pci/drm/drm_syncobj.c
- `apldrm(4)` manual page, 23 Jan 2024 — https://man.openbsd.org/apldrm.4
- llama.cpp issue 16188, garbage output from Honeykrisp on an M2 Pro, 23 Sep 2025 —
  https://github.com/ggml-org/llama.cpp/issues/16188
- The companion research note, with the full evidence base —
  [OpenBSD and the Apple GPU](openbsd-apple-silicon-gpu.md)
