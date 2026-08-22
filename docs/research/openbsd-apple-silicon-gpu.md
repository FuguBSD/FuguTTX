# Can FuguTTX run GPU inference on a Mac mini M1 under OpenBSD?

**Date: 1 August 2026. Status: research report. This report changes no code.**

A companion document describes what the work would look like, if anybody did it:
[Draft plan: Apple GPU support for OpenBSD on the Mac mini](apple-gpu-openbsd-draft-plan.md).
That plan is a draft, and it is not part of the specification.

## 1. Verdict

No. The first necessary condition is many years away.

OpenBSD boots and runs on a Mac mini M1 (2020). OpenBSD has no driver for the
Apple GPU. The kernel sees the GPU node and leaves it unclaimed. The display
driver `apldrm(4)` does mode setting only. It declares no `DRIVER_RENDER` flag,
so it creates no render node. A compute client has no device to open.

The only Apple GPU kernel driver that exists anywhere is the Asahi Linux driver.
That driver is 24 Rust source files in a branch that Asahi rebases. The OpenBSD
kernel contains no Rust. Mainline Linux contains no `drivers/gpu/drm/asahi` on 1
August 2026.

An earlier version of this report named a different blocker. It said that
OpenBSD takes DRM drivers only from mainline Linux. The evidence refutes that
statement. Mark Kettenis imported `apldcp(4)` and `apldrm(4)` on 22
January 2024. He took that code from the Asahi Linux tree, not from mainline
Linux. Jonathan Gray has carried the out-of-tree subtree by hand through each
mainline sync since. OpenBSD can take out-of-tree DRM code, and it has done this
for Apple graphics already. Section 5 gives the corrected list of blockers.

The software above the driver is ready. `devel/libggml` builds the ggml Vulkan
back end on aarch64 and ships `libggml-vulkan.so`. On a Mac mini M1 that back
end loads, finds no Vulkan device, and uses the CPU. The failure is silent.

The expected gain needs correction in two directions. Token generation cannot
improve. A STREAM measurement gives the M1 CPU 59 GB/s and the M1 GPU 60 GB/s.
The two engines reach the same memory bandwidth. Token generation reads all
weights for each token, so bandwidth sets the limit for both.

Prompt processing is different. A GPU path can improve prompt processing, and
the improvement can be large. Two llama.cpp changes in June 2026 raised Apple
GPU prompt processing by 81 percent. The OpenBSD CPU build is also weak on this
axis, for a separate and cheap reason. The `devel/libggml` port passes no
`-mcpu` value and no `-march` value on aarch64. The aarch64 package therefore
uses no dot-product instructions and links no BLAS.

This gives three instructions. An engineer must not start work on an OpenBSD
Apple GPU driver. An engineer must correct the aarch64 CPU build flags in
`devel/libggml` first. An engineer must then run `llama-bench` on the target
machine and publish the result. No such measurement exists in public today.

## 2. What works today

OpenBSD supports the Mac mini M1 as a boot target. The machine needs a UEFI
environment first. The Asahi Linux installer installs that environment. The
arm64 page lists M1 and M2 machines only. Snapshots after OpenBSD 7.9 added the
Apple AIC v3 interrupt controller for M3 and later.

`sys/arch/arm64/conf/GENERIC` configures 31 `apl*` devices. These cover the
interrupt controller, the DART IOMMU, PCIe, NVMe, SMC, I2C, SPI, and SPMI. They
also cover DMA, audio, power management, and the display coprocessor. The port
is active. The last change to `aplsmc.c` has the date 26 July 2026.

OpenBSD 7.5 (5 April 2024) replaced `simplefb(4)` on Apple hardware. The console
now uses the driver pair `apldcp(4)` plus `apldrm(4)`. A boot prints
`apldcp0 at simplebus0`, `apldrm0 at simplebus0`, `drm0 at apldrm0`, and
`wsdisplay0 at apldrm0`.

This pair does mode setting. It does not accelerate anything. Mark Kettenis
wrote in the import commit: “These drivers do _not_ bring us GPU accelerated
graphics.” `sys/dev/pci/drm/apple/apple_drv.c` declares
`.driver_features = DRIVER_MODESET | DRIVER_GEM | DRIVER_ATOMIC` with dumb
buffers. It declares no `DRIVER_RENDER`. The driver therefore creates no
`/dev/dri/renderD*` node. A headless compute client has nothing to open.

The boot log is the clearest single piece of evidence. Real OpenBSD boots on M1
and M2 hardware print these lines:

```
"gpu" at simplebus0 not configured
"uat-handoff" at mainbus0 not configured
"uat-pagetables" at mainbus0 not configured
"uat-ttbs" at mainbus0 not configured
```

UAT is the address-translation unit of the Apple GPU. The kernel sees the GPU
and its reserved memory. The kernel has no driver for either.

X runs with software rendering only. The arm64 X sets ship `modesetting_drv.so`,
`wsfb_drv.so`, and `libglamoregl.so`. Glamor can load. Glamor then runs on the
software rasterizer, which is not acceleration. The community wiki records the
same result: “Graphics acceleration doesn’t work, thus no video playback.”

OpenBSD 7.9 also added `hw.blockcpu`. This sysctl keeps the scheduler off named
CPU classes. `sysctl hw.blockcpu=EL` confines a process to the four Firestorm
performance cores. Section 6 uses this in the measurement procedure.

**Sources**

- OpenBSD arm64 platform page (M1 and M2 machine list, UEFI note), read 1 Aug
  2026 — https://www.openbsd.org/arm64.html
- OpenBSD 7.9 release notes, 19 May 2026 — https://www.openbsd.org/79.html
- OpenBSD -current changelog (AIC v3), read 1 Aug 2026 —
  https://www.openbsd.org/plus.html
- `sys/arch/arm64/conf/GENERIC`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/conf/GENERIC
- OpenBSD 7.5 release notes (new `apldcp` and `apldrm`), 5 Apr 2024 —
  https://www.openbsd.org/75.html
- `apldrm(4)` manual page, dated 23 Jan 2024 — https://man.openbsd.org/apldrm.4
- undeadly.org, KMS on Apple Silicon (Kettenis commit log), 25 Jan 2024 —
  https://undeadly.org/cgi?action=article&sid=20240125064408
- `sys/dev/pci/drm/apple/apple_drv.c`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/dev/pci/drm/apple/apple_drv.c
- M2 MacBook Pro dmesg on misc@ (`"gpu" ... not configured`), 16 Sep 2025 —
  https://www.mail-archive.com/misc@openbsd.org/msg195186.html
- `modesetting(4)` manual page, read 1 Aug 2026 —
  https://man.openbsd.org/modesetting.4
- xenocara arm64 X set lists, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/xenocara/master/distrib/sets/lists/xserv/md.arm64
- openbsdonapple.wiki installation page, last modified 25 Apr 2025 —
  https://openbsdonapple.wiki/doku.php?id=apple_silicon:installation
- `sysctl(2)` manual page (`HW_BLOCKCPU`), dated 4 Apr 2026 —
  https://man.openbsd.org/sysctl.2
- `sys/arch/arm64/arm64/cpu.c` (`cpu_classify`), read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/arm64/cpu.c

## 3. Is anybody working on it?

No public evidence of work exists. This is an absence of evidence. A private
effort can exist and stay invisible. Nine independent checks all give the same
result.

- **The kernel tree.** `sys/dev/pci/drm` contains `amd`, `apple`, `clients`,
  `display`, `i915`, `include`, `radeon`, `scheduler`, and `ttm`. It contains no
  `asahi` and no `agx`. The `apple` directory holds display-coprocessor code
  only. `sys/arch/arm64/dev` contains 22 `apl*` drivers and no GPU driver.
- **The commit archive, `agx`.** A search of `openbsd-cvs` for `agx` returns 11
  results. All 11 are Mesa vendor imports into xenocara by Jonathan Gray. Their
  dates run from 24 February 2022 to 5 June 2025. No result touches `src`.
- **The commit archive, `asahi`.** A search of `openbsd-cvs` for `asahi` returns
  24 mails, from 24 February 2022 to 5 June 2025. None of them adds an Apple GPU
  driver.
- **tech@.** A search for `asahi` finds no proposal and no driver. A search for
  `agx` returns two hits, and both are unrelated substring matches. A search for
  `apldrm` returns three messages about manual-page structure.
- **misc@.** A search for `apple gpu` returns wifi faults and Intel-Mac X11
  problems. The newest Apple Silicon threads cover firmware and dual boot. Gabe
  Bauer asked about whole-disk installation on 5 March 2026. Stefan Sperling
  replied that “OpenBSD relies on the MacOS installation for firmware files”.
  Neither message mentions the GPU.
- **The release notes.** OpenBSD 7.9 mentions Apple for an SDHC controller,
  Apple Virtualization, and a virtual USB digitizer. The `-current` changelog
  after 7.9 adds AIC v3 and nothing for the GPU.
- **Hackathons.** The g2k26 hackathon ran in July 2026 at Kloosterburen with 18
  developers. The one report published by 30 July 2026 covers `rpki-client(8)`.
  No report mentions Apple Silicon graphics.
- **Conferences.** The EuroBSDcon 2026 schedule was published on 15 July 2026.
  It has no talk on GPU work, DRM, or Apple Silicon. The AsiaBSDCon 2026
  schedule has none either.
- **The port is active while it skips the GPU.** Kettenis and others committed
  Apple Silicon code five weeks before this report. A busy port that keeps
  skipping the GPU shows a scope decision.

One person has asked for the work in public. A GitHub gist by gjbauer asks
OpenBSD to allow Rust in the kernel and port the Asahi driver, or to rewrite the
driver in C. It contains no code and names no developer support. Its date is the
gist-wide “last active” timestamp of 13 March 2026. It is a request. It is not a
project.

No BSD-wide effort exists either. The NetBSD Apple Silicon port is
framebuffer-only. Its wiki page was last edited on 7 May 2022, and its newest
status post has the date 11 April 2025. FreeBSD has five files in
`sys/arm64/apple`, for the interrupt controller, pin control, the watchdog, and
the UART. FreeBSD lists no Apple machine in the 14.3 or 15.0 hardware notes.
DragonFly BSD runs on amd64 only.

One limit applies to all the list checks above. They use the marc.info full-body
search. That search ranks by relevance and can miss a message.

**Sources**

- `sys/dev/pci/drm` directory listing, read 1 Aug 2026 —
  https://cvsweb.openbsd.org/src/sys/dev/pci/drm/
- `sys/arch/arm64/dev` directory listing, read 1 Aug 2026 —
  https://cvsweb.openbsd.org/src/sys/arch/arm64/dev/
- `openbsd-cvs` search for `agx`, read 1 Aug 2026 —
  https://marc.info/?l=openbsd-cvs&w=2&r=1&s=agx&q=b
- `openbsd-cvs` search for `asahi`, read 1 Aug 2026 —
  https://marc.info/?l=openbsd-cvs&w=2&r=1&s=asahi&q=b
- `openbsd-tech` search for `asahi`, read 1 Aug 2026 —
  https://marc.info/?l=openbsd-tech&w=2&r=1&s=asahi&q=b
- `openbsd-tech` search for `apldrm`, read 1 Aug 2026 —
  https://marc.info/?l=openbsd-tech&w=2&r=1&s=apldrm&q=b
- misc@ thread “M1 Mac EOL & Full Drive Installation Support”, 5–6 Mar 2026 —
  https://marc.info/?l=openbsd-misc&m=177280567725465&w=2
- OpenBSD 7.9 changelog, 19 May 2026 — https://www.openbsd.org/plus79.html
- undeadly.org front page and g2k26 report, 13 Jul 2026 — https://undeadly.org/
- EuroBSDcon 2026 schedule export, published 15 Jul 2026 —
  https://events.eurobsdcon.org/2026/schedule/export/schedule.json
- AsiaBSDCon 2026 schedule export, read 1 Aug 2026 —
  https://2026.asiabsdcon.org/entry/schedule/export/schedule.json
- gjbauer gist, last active 13 Mar 2026 —
  https://gist.github.com/gjbauer/3ddad161e43f9bae6801095eb92dbcf2
- NetBSD evbarm Apple page, last edited 7 May 2022 —
  https://wiki.netbsd.org/ports/evbarm/apple/
- NetBSD port-arm status post, 11 Apr 2025 —
  http://mail-index.netbsd.org/port-arm/2025/04/11/msg009163.html
- FreeBSD `sys/arm64/apple`, read 1 Aug 2026 —
  https://github.com/freebsd/freebsd-src/tree/main/sys/arm64/apple
- FreeBSD 15.0 hardware notes, read 1 Aug 2026 —
  https://www.freebsd.org/releases/15.0R/hardware/
- DragonFly BSD supported hardware, last edited 4 Jan 2024 —
  https://www.dragonflybsd.org/docs/supportedhardware/

## 4. The four conditions

A GPU inference path must satisfy four conditions. Two are closed. Two are open.
The two open conditions are the two that need no new kernel work.

| #   | Condition                          | State               | What is missing                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | ---------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | AGX kernel driver in OpenBSD       | **Closed**          | `sys/dev/pci/drm` has no `asahi` code and no `agx` code. `apldrm(4)` declares no `DRIVER_RENDER` and creates no render node. The GPU node stays unconfigured at boot. The only implementation anywhere is 24 Rust files in the Asahi `asahi-wip` branch. The OpenBSD kernel has no Rust. Mainline Linux has no `drm/asahi` either.                                                                                                                                                                                                               |
| 2   | Vulkan or OpenCL user-space driver | **Closed**          | xenocara vendors Mesa 25.0.7 with the whole Apple stack, including Honeykrisp under `lib/mesa/src/asahi/vulkan` and the Gallium driver under `lib/mesa/src/gallium/drivers/asahi`. `lib/mesa/mk` has no `libvulkan_asahi` target. `config.mk` has no Apple switch. The only arm64 ICD is `radeon_icd.aarch64.json`. No software Vulkan ICD exists, so there is no lavapipe. No OpenCL runtime exists: no rusticl, no clover, no pocl, no `libclc`.                                                                                               |
| 3   | ggml GPU back end                  | **Open**            | Nothing is missing. `devel/libggml` sets `-DGGML_VULKAN=on` for amd64 and aarch64. It depends on `graphics/shaderc`, `graphics/spirv-headers`, and `graphics/vulkan-loader`. It ships `lib/libggml-vulkan.so`. The aarch64 snapshot package holds a 51.6 MB OpenBSD aarch64 ELF object with `NEEDED libvulkan.so.1.3`. `misc/llama.cpp` (b10063, 20 Jul 2026) has no GPU options and consumes libggml. All 13 libggml patches are riscv64 patches, test patches, or build changes.                                                               |
| 4   | OpenBSD security model             | **Open, with work** | `pledge(2)` has a `drm` promise that permits DRM ioctls. Xorg already runs unprivileged on DRM. Neither port carries a pledge patch or an unveil patch. Stuart Henderson asked for pledge on ports@ on 1 February 2025, and nobody committed one. A GPU path adds three surfaces after startup: `dlopen` of `/usr/local/lib` because the port sets `GGML_BACKEND_DL=ON`, the ICD JSON directory, and a DRM device node. Device permissions cause failures already: an unprivileged user without GPU access gets `vk::InitializationFailedError`. |

Condition 2 has a second problem that is less easy to see. The Mesa in OpenBSD
targets the _unstable_ Apple UAPI. In Mesa 25.0.7, `src/asahi/lib/agx_device.c`
includes `unstable_asahi_drm.h`. That code refuses to run unless the unstable
UABI version matches. Mesa main has moved to the stable header
`drm-uapi/asahi_drm.h`. The Mesa in base today would therefore reject a future
kernel driver that uses the stable UAPI. An Apple Vulkan ICD needs a Mesa update
in xenocara and new build rules.

The Gallium `asahi` files in xenocara carry vendor-branch revisions of the form
1.1.1.N and no OpenBSD Makefile. The report cannot confirm that OpenBSD compiles
them. Treat the user-space state as “source present, build unconfirmed”.

Condition 3 is open while condition 1 is closed, and this causes a silent
failure. `pkg_add llama.cpp` on a Mac mini M1 installs a binary with a Vulkan
back end. The back end loads. The loader enumerates zero ICDs. Inference then
runs on the CPU. The user gets no error message.

**Sources**

- `devel/libggml/Makefile`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/ports/master/devel/libggml/Makefile
- `devel/libggml/pkg/PFRAG.vulkan`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/ports/master/devel/libggml/pkg/PFRAG.vulkan
- `devel/libggml/patches` listing, read 1 Aug 2026 —
  https://github.com/openbsd/ports/tree/master/devel/libggml/patches
- `misc/llama.cpp/Makefile` (b10063), 20 Jul 2026 —
  https://raw.githubusercontent.com/openbsd/ports/master/misc/llama.cpp/Makefile
- OpenBSD aarch64 snapshot packages (`libggml-0.17.0.tgz`,
  `vulkan-loader-1.4.341.0.tgz`), read 1 Aug 2026 —
  https://cdn.openbsd.org/pub/OpenBSD/snapshots/packages/aarch64/
- xenocara `lib/mesa/mk/config.mk`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/xenocara/master/lib/mesa/mk/config.mk
- xenocara `lib/mesa/mk/Makefile`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/xenocara/master/lib/mesa/mk/Makefile
- xenocara `lib/mesa/src/asahi`, read 1 Aug 2026 —
  https://cvsweb.openbsd.org/xenocara/lib/mesa/src/asahi/
- xenocara `lib/mesa/src/gallium/drivers/asahi`, read 1 Aug 2026 —
  https://cvsweb.openbsd.org/xenocara/lib/mesa/src/gallium/drivers/asahi/
- xenocara arm64 xbase set list (`radeon_icd.aarch64.json`), read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/xenocara/master/distrib/sets/lists/xbase/md.arm64
- `pledge(2)` manual page, read 1 Aug 2026 — https://man.openbsd.org/pledge.2
- ports@ “llama.cpp vulkan” thread (pledge question, RX 6600 test), 31 Jan – 2
  Feb 2025 — https://www.mail-archive.com/ports@openbsd.org/msg131310.html and
  https://www.mail-archive.com/ports@openbsd.org/msg131332.html

## 5. Why an OpenBSD Apple GPU driver is hard

### The provenance of the Apple DRM code

OpenBSD takes most DRM code from mainline Linux in bulk. OpenBSD 7.9 records
“Updated drm(4) to Linux 6.18.22”. `sys/dev/pci/drm/apple` is the one exception
in the tree, and it is the relevant one.

All 27 files in `src/sys/dev/pci/drm/apple` carry revision 1.1 with the date 22
January 2024 and the author kettenis. The import commit names its source:

> This is a port of the the Asahi Linux drivers which can be found at
> https://github.com/AsahiLinux/linux/tree/asahi-wip Note that this branch gets
> rebased from time to time.

Three further facts confirm the pattern. Commits on 23 January 2024 cite Janne
Grunau’s out-of-tree series `bits/200-dcp` by hash. Jonathan Gray cherry-picked
from the same Asahi series on 19 September 2024, with the approval of Kettenis.
Gray then adapted the subtree by hand in the commit “update drm to linux
6.18.16” on 9 March 2026, because the mainline sync source holds no Apple DCP
code to overwrite it.

Mainline Linux does hold `drivers/gpu/drm/adp`. That driver serves “pre-DCP
Apple display controllers” on Touch Bar machines. It is a different driver for
different hardware. It does not make the OpenBSD code mainline-derived.

The `apldrm(4)` manual page states the same provenance. Its AUTHORS section
reads: “The apldrm driver was written by Alyssa Rosenzweig and Janne Grunau for
Linux and ported to OpenBSD by Mark Kettenis”. OpenBSD also takes non-graphics
Asahi code. Kettenis committed a `if_bwfm_pci.c` change on 12 July 2024 “Based
on a diff from Hector Martin for Asahi Linux.”

No written OpenBSD policy on out-of-tree DRM imports was found. The conclusion
rests on repeated practice, which is weaker evidence than a policy statement.
The practical result is clear. Entry into mainline Linux is not a precondition
for an OpenBSD Apple GPU driver.

### The blockers, ranked

| Rank | Blocker                                                                                                                                               | Status                                 |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| 1    | No C implementation of an AGX driver exists. The only implementation is 24 Rust files in `AsahiLinux/linux` `asahi-wip`. A port means a rewrite in C. | Verified                               |
| 2    | There is no stable upstream to track. The source branch rebases, and the firmware ABI follows macOS firmware releases.                                | Verified                               |
| 3    | Nobody does the work. No OpenBSD tree, list, hackathon, or conference activity exists for 2024 to 2026.                                               | Verified as absence of public evidence |
| 4    | Mainline Linux has no `drm/asahi` either, so “wait for mainline, then sync” is also unavailable.                                                      | Verified                               |
| —    | The license is not a blocker. The code is `GPL-2.0-only OR MIT`, and OpenBSD already used the MIT arm.                                                | Refuted as a blocker                   |
| —    | User space is not a blocker. Mesa `asahi` source is already in xenocara.                                                                              | Refuted as a blocker                   |
| —    | A mainline-only import rule is not a blocker. No such rule governs practice.                                                                          | Refuted as a blocker                   |

### The Rust question

Rust is a real cost, and it follows from blocker 1. The Asahi driver is about
21,000 lines by itself. It depends on Rust kernel abstractions that were still
landing in Linux 7.1 in March 2026. The OpenBSD base toolchain is LLVM/Clang
19.1.7 and GCC 4.2.1. Rust 1.94.1 exists only as a package. No primary source
states a kernel Rust policy for OpenBSD. The one statement that people cite is
Theo de Raadt’s message of 3 December 2017 about safe languages. It says “In
OpenBSD there is a strict requirement that base builds base”. That message is
nine years old, and it concerns base utilities, not kernel drivers. Report the
observable fact: `src` contains no Rust. Mark the policy as an inference.

### Supporting C code in the tree

OpenBSD already holds much of the C support code. `drm_gpuvm.c`, `drm_exec.c`,
`drm_prime.c`, `drm_gem.c`, the DRM GPU scheduler under `scheduler/`, and an
Apple RTKit implementation in `sys/arch/arm64/dev/rtkit.c` are all present in C.
`drm_gem_shmem_helper.c` is absent. `drm_syncobj.c` is present, and it replaces
the fd export and import paths with `STUB(); return -ENOSYS;`. The Mesa Apple
drivers need `DMA_BUF_IOCTL_IMPORT_SYNC_FILE` and
`DMA_BUF_IOCTL_EXPORT_SYNC_FILE`, and the OpenBSD dma-buf shim does not provide
them.

### The firmware contract

Asahi moved GPU initialization into the m1n1 bootloader in the Linux 7.1 cycle.
The future upstream driver will depend on m1n1 for that step. m1n1 1.6.0 needs
Rust for its stage 2 build. The OpenBSD `sysutils/m1n1` port is at 1.5.2 (5
January 2026). The m1n1 port is therefore the first place where Rust becomes a
requirement on this hardware.

### The DRM sync lag

OpenBSD 7.9 shipped Linux 6.18.22 about five and a half months after Linux 6.18.
Linux then renumbered: 7.0 in April 2026 and 7.1 in June 2026. OpenBSD
`-current` is still on 6.18, so the live gap is about eight months. That lag
would delay an Apple driver by one cycle. The lag is a secondary cost.

### The upstream review status

No full driver series has reached dri-devel. The Asahi 6.19 report (15
February 2026) says that upstreaming work has begun. It says that cleanup is
still required, and that review “is expected to take quite some time”. A search
of the dri-devel archive for January to July 2026 returns two classes of `asahi`
message. The first class is Janne Grunau’s IGT test series of 5 January 2026,
reviewed again on 23 June 2026. The second class is generic Rust DRM
infrastructure work, with the newest message dated 7 July 2026. Neither class is
the driver. One limit applies: lore.kernel.org and patchwork.freedesktop.org
were unreachable, so this check used mail-archive.com and patchwork.kernel.org
instead.

**Sources**

- `sys/dev/pci/drm/apple/apldrm.c` CVS log (import 22 Jan 2024), read 1 Aug 2026
  — https://cvsweb.openbsd.org/src/sys/dev/pci/drm/apple/apldrm.c
- `sys/dev/pci/drm/apple/iomfb_template.c` CVS log (`bits/200-dcp` cherry-picks;
  jsg commit 19 Sep 2024), read 1 Aug 2026 —
  https://cvsweb.openbsd.org/src/sys/dev/pci/drm/apple/iomfb_template.c
- `sys/dev/pci/drm/apple/dcp.h` CVS log ("update drm to linux 6.18.16", 9
  Mar 2026) — https://cvsweb.openbsd.org/src/sys/dev/pci/drm/apple/dcp.h
- Linux `drivers/gpu/drm` at tag v6.7 (no `apple`, no `asahi`), read 1 Aug 2026
  — https://github.com/torvalds/linux/tree/v6.7/drivers/gpu/drm
- Linux `drivers/gpu/drm` at master (no `apple`, no `asahi`), read 1 Aug 2026 —
  https://github.com/torvalds/linux/tree/master/drivers/gpu/drm
- Linux `drivers/gpu/drm/adp/Kconfig` (pre-DCP controllers), read 1 Aug 2026 —
  https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/adp/Kconfig
- `apldrm(4)` manual page, AUTHORS section — https://man.openbsd.org/apldrm.4
- openbsd-cvs, `if_bwfm_pci.c` from an Asahi diff, 12 Jul 2024 —
  https://marc.info/?l=openbsd-cvs&m=172077318907370&w=2
- `AsahiLinux/linux` `drivers/gpu/drm/asahi` (24 Rust files), read 1 Aug 2026 —
  https://github.com/AsahiLinux/linux/tree/asahi-wip/drivers/gpu/drm/asahi
- OpenBSD 7.9 release notes (drm at Linux 6.18.22), 19 May 2026 —
  https://www.openbsd.org/79.html
- `include/uapi/drm/asahi_drm.h` commit history, commit 8 Apr 2025 —
  https://github.com/torvalds/linux/commits/master/include/uapi/drm/asahi_drm.h
- Phoronix, Asahi UAPI header for Linux 6.16, 9 Apr 2025 —
  https://www.phoronix.com/news/Linux-6.16-Ashai-UAPI-Header
- Rust for Linux, Apple AGX GPU driver page, read 1 Aug 2026 —
  https://rust-for-linux.com/apple-agx-gpu-driver
- Asahi Linux, Progress Report: Linux 6.19, 15 Feb 2026 —
  https://asahilinux.org/2026/02/progress-report-6-19/
- Asahi Linux, Progress Report: Linux 7.1 (m1n1 GPU init, Rust in stage 2), 30
  Jun 2026 — https://asahilinux.org/2026/06/progress-report-7-1/
- Phoronix, Rust DRM work for Linux 7.1, 31 Mar 2026 —
  https://www.phoronix.com/news/Rust-DRM-For-Linux-7.1
- dri-devel search for `asahi` (Jan–Jul 2026), read 1 Aug 2026 —
  https://www.mail-archive.com/search?l=dri-devel%40lists.freedesktop.org&q=asahi&start=0
- patchwork.kernel.org, dri-devel filtered on `asahi`, read 1 Aug 2026 —
  https://patchwork.kernel.org/project/dri-devel/list/?q=asahi&state=*&archive=both
- OpenBSD `sys/dev/pci/drm/drm_syncobj.c`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/dev/pci/drm/drm_syncobj.c
- Theo de Raadt, misc@, "Re: Integrating \"safe\" languages into OpenBSD?", 3
  Dec 2017 — https://marc.info/?l=openbsd-misc&m=151233345723889&w=2

## 6. The possible gain

The gain splits by axis. Token generation gains nothing on the M1. Prompt
processing can gain a lot, and a cheaper CPU change gains on the same axis. A
change of target machine gains more than a GPU, on both axes.

### The bandwidth arithmetic, corrected

The Mac mini M1 (2020) has four Firestorm cores, four Icestorm cores, an
eight-core GPU, and 8 GB or 16 GB of unified memory. The memory is 128-bit
LPDDR4X. The specification figure is 68.25 GB/s.

Measurement gives a lower and more useful number. A peer-reviewed STREAM study
measures the M1 CPU at 59 GB/s and the M1 GPU at 60 GB/s. The same study
measures about 85 percent of theoretical peak for every M-series chip. An
independent microbenchmark gives an M1 read figure of 64 GB/s and a DRAM latency
of 91 ns, from about 2021. That page does not state the thread count, so treat
59 to 64 GB/s as the credible range.

The important consequence is simple. The CPU and the GPU reach the same memory
bandwidth on this chip. The GPU has no bandwidth advantage to use.

Token generation at batch 1 reads every weight once for each token. The
arithmetic intensity is about 2 FLOP per byte. Bandwidth therefore sets the
limit.

For a 2.5 GB Qwen3-4B Q4_K_M file:

| Bandwidth basis       | Value      | Token-generation limit     |
| --------------------- | ---------- | -------------------------- |
| Specification peak    | 68.25 GB/s | 27.3 tokens/s, unreachable |
| Measured GPU (STREAM) | 60 GB/s    | 24.0 tokens/s              |
| Measured CPU (STREAM) | 59 GB/s    | 23.6 tokens/s              |

These figures are arithmetic, not measurement. They ignore KV-cache reads, which
grow with context and lower the real number. On the 8 GB model, the KV cache for
long agent contexts is a further constraint.

### The M1 is the slowest supported machine

The same STREAM study measures all four base M-series chips. The limits below
use the same 2.5 GB Qwen3-4B Q4_K_M file.

| Chip | Specification peak | Measured CPU | Measured GPU | CPU limit     | GPU limit     |
| ---- | ------------------ | ------------ | ------------ | ------------- | ------------- |
| M1   | 68.25 GB/s         | 59 GB/s      | 60 GB/s      | 23.6 tokens/s | 24.0 tokens/s |
| M2   | 100 GB/s           | 78 GB/s      | 91 GB/s      | 31.2 tokens/s | 36.4 tokens/s |
| M3   | 102.4 GB/s         | 92 GB/s      | 92 GB/s      | 36.8 tokens/s | 36.8 tokens/s |
| M4   | 120 GB/s           | 103 GB/s     | 100 GB/s     | 41.2 tokens/s | 40.0 tokens/s |

The M2 and the M3 have the same memory: 128-bit LPDDR5-6400. Apple states 100
GB/s for the M2, and the arithmetic gives 102.4 GB/s. The study treats the two
peaks as equal.

The M2 CPU gives 32 percent more bandwidth than the M1 CPU. The M2 GPU gives 52
percent more than the M1 GPU.

One difference changes the GPU argument by a small amount. On the M1 the CPU and
the GPU measure the same, so a GPU adds nothing to token generation. On the M2 a
gap of about 17 percent exists between the CPU and the GPU. The study calls this
an M2 CPU anomaly. The Copy and Scale kernels fall 20 to 30 GB/s behind the
other kernels, which is about 13 percent. The authors write: “It is unclear why
the M2’s CPU performed worse than anticipated.” A GPU on an M2 would therefore
buy about 17 percent on token generation, against zero on an M1. This does not
change the verdict.

### A different machine buys more than a GPU

The OpenBSD arm64 page lists three Mac mini models, and not one: Mac mini (M1,
2020), Mac mini (M2, 2023), and Mac mini (M2 Pro, 2023).

The M2 Pro has a specification peak of 200 GB/s, which is about three times the
M1. The study measured base chips only, so no measured figure exists for the M2
Pro. The 85 percent rule of the study extrapolates to about 170 GB/s. That gives
a token-generation limit near 68 tokens/s. Treat this as an estimate, and not as
a measurement.

This gives the cheapest result in the whole report. A change of target machine
multiplies token generation by about 1.3 (M2) or about 2.9 (M2 Pro). It needs no
new kernel driver, no new user-space driver, and no new ggml back end. An
operator can buy the result today. A GPU path cannot deliver a comparable gain,
because token generation on any of these machines is bandwidth-bound.

Two conditions apply. FuguTTX must confirm that OpenBSD runs on the chosen
machine before it buys one. FuguTTX must measure the machine with `llama-bench`,
because these limits are arithmetic.

### The OpenBSD aarch64 CPU build is not tuned

This is the largest new finding, and it is a cheap fix.

`devel/libggml/Makefile` sets `-DGGML_NATIVE=OFF` for every architecture. It
sets `-DGGML_CPU_ALL_VARIANTS=on` for amd64 and `off` for every other
architecture. It never sets `GGML_CPU_ARM_ARCH`. In ggml v0.17.0 the ARM branch
of `src/ggml-cpu/CMakeLists.txt` needs one of those three switches. No branch
fires, so `ARCH_FLAGS` stays empty and the compiler default applies. The OpenBSD
clang driver returns `"generic"` as the default CPU for non-Darwin targets,
which means baseline armv8-a. The same driver appends `+strict-align` for
OpenBSD targets.

Four consequences follow.

1. `__ARM_FEATURE_DOTPROD` stays undefined. `ggml_vdotq_s32` then expands to two
   `vmull_s8`, two `vpaddlq_s16`, and two `vaddq_s32` instructions, instead of
   one `SDOT`. The Q4_K inner loop therefore does about three times the SIMD
   work per weight.
2. ggml v0.17.0 does no runtime ARM feature detection. Every accessor such as
   `ggml_cpu_has_dotprod()` is a preprocessor test. The lost instruction set
   cannot return at run time.
3. The aarch64 package installs exactly one `lib/libggml-cpu.so`. The amd64
   package installs fourteen tuned variants. The loader on arm64 has nothing to
   select between.
4. ggml enables BLAS by default only on Apple platforms. OpenBSD gets no BLAS
   and no tinyBLAS `sgemm` path. A macOS CPU-only build links Accelerate, which
   drives AMX and reaches 0.90 TFLOPS FP32 SGEMM on an M1. Prompt processing is
   a GEMM, so OpenBSD loses most on that axis.

The OpenBSD kernel does not cause this. `cpu_identify_cleanup()` masks
`ID_AA64ISAR0` but keeps the DP field. It then sets `HWCAP_ASIMDDP` when the CPU
implements dot product. The kernel withholds SVE and SME only, and the M1 has
neither. This is a ports change, not a kernel change.

The 13 patches in the port support this reading. Every functional patch is
riscv64 work or a build change. None touches aarch64 code. A change of the form
`-DGGML_CPU_ARM_ARCH=armv8.4-a+dotprod+fp16` would be small and self-contained.

### The measured numbers

Every Apple GPU row below comes from the llama.cpp Vulkan scoreboard or from a
merged pull request. Scoreboard dates are the commit dates of the stated build,
which is a lower bound.

| Machine                | Back end and OS              | Model and quantization | pp512 (t/s)       | tg128 (t/s)       | Build and date              |
| ---------------------- | ---------------------------- | ---------------------- | ----------------- | ----------------- | --------------------------- |
| M1, 8-core GPU         | Metal, macOS                 | LLaMA 7B Q4_0          | 117.96            | 14.15             | 8e672ef, 22 Nov 2023        |
| **M1**                 | **Vulkan/Honeykrisp, Asahi** | **llama 2 7B Q4_0**    | **38.29**         | **12.47**         | **2370665, 21 Nov 2025**    |
| M2 (MacBook Air)       | Vulkan/Honeykrisp, Asahi     | llama 7B Q4_0          | 38.67             | 11.07             | 017cc5f, 8 Jan 2025         |
| M2                     | Vulkan/Honeykrisp, Asahi     | llama 2 7B Q4_0        | 50.79             | 13.50             | 8c0d6bb, 7 Nov 2025         |
| M2 Pro                 | Vulkan/Honeykrisp, Asahi     | llama 2 7B Q4_0        | 62.70             | 20.95             | 1fe0029, 16 Aug 2025        |
| M2 Ultra               | Vulkan/Honeykrisp, Asahi     | llama 2 7B Q4_0        | 205.98            | 34.34             | dbb852b, 24 Nov 2025        |
| M1 Ultra, 48-core GPU  | Vulkan/Honeykrisp, Asahi     | llama 7B Q4_0          | 207.57            | 33.86             | before PR 24306, 8 Jun 2026 |
| M1 Ultra, 48-core GPU  | Vulkan/Honeykrisp, Asahi     | llama 2 7B Q4_0        | 375.56            | 34.22             | after PR 24663, 30 Jun 2026 |
| M1 Ultra, 48-core GPU  | Metal, macOS                 | LLaMA 7B Q4_0          | 772.24            | 74.93             | 8e672ef, 22 Nov 2023        |
| M3                     | Vulkan/MoltenVK, macOS       | llama 2 7B Q4_0        | 263.70            | 26.39             | b9ab0a4, 11 Feb 2025        |
| M2 Max                 | Metal, macOS                 | 7B Q4_K                | 580.26            | 61.18             | issue 10982, 26 Dec 2024    |
| M2 Max                 | Vulkan, Asahi                | 7B Q4_K                | 92.16             | 21.93             | issue 10982, 26 Dec 2024    |
| M2 Max                 | CPU only, macOS              | llama 7B Q4_0          | 139.60            | 23.11             | discussion 12985, Apr 2025  |
| M2 Max                 | CPU only, Linux container    | llama 7B Q4_0          | 332.43            | 25.74             | discussion 12985, Apr 2025  |
| amd64, two RX 7900 XTX | Vulkan, OpenBSD              | gpt-oss 20B MXFP4      | 2405.75           | 128.82            | ports@, 1 Feb 2026          |
| AMD RX 6900 XT         | Vulkan, Linux                | llama 2 7B Q4_0        | 1901.20           | 108.00            | discussion 10879            |
| AMD RX 7900 XTX        | Vulkan, Linux                | llama 2 7B Q4_0        | 3531.93           | 191.28            | discussion 10879            |
| **Mac mini M1**        | **CPU, OpenBSD/arm64**       | **any**                | **not published** | **not published** | **no measurement exists**   |

The last row is the gap that matters. Searches of openbsd-arm, openbsd-misc,
openbsd-tech, and openbsd-ports for `llama-bench` and for `llama.cpp` return no
Apple Silicon result. The GitHub issue tracker for llama.cpp returns OpenBSD
build failures and amd64 results only.

### Why prompt processing is slow, corrected

The earlier explanation was wrong. That explanation said that Apple GPUs expose
no `VK_KHR_cooperative_matrix`, so the fast Vulkan GEMM path is unavailable. Two
merged pull requests in June 2026 refute it as the main cause.

`vulkan: use medium matmul tile on Asahi Linux` (PR 24306, merged 11 June 2026)
raised M1 Ultra pp512 from 207.57 to 259.00. The cause was a device-detection
bug. The Honeykrisp driver does not report `VK_VENDOR_ID_APPLE`, so llama.cpp
used the generic large-tile default.
`vulkan: roll bk loop in matmul for asahi linux` (PR 24663, merged 30 June 2026)
raised pp512 from 306.75 to 375.56. The cause was instruction-cache pressure
from an unrolled loop body against the 12 KB Apple instruction cache. The total
gain across June 2026 is 81 percent. The device line reads
`int dot: 0 | matrix cores: none` before and after both changes.

Two accelerated fallback paths remain unavailable on Apple GPUs, and this part
of the old explanation still holds. Honeykrisp advertises no cooperative matrix
and no accelerated integer dot product. The DP4A MMQ path (March 2025) needs
`integerDotProduct4x8BitPackedSignedAccelerated`, which Honeykrisp does not set.
The `v_dot2_f32_f16` path (June 2026) needs
`VK_VALVE_shader_mixed_float_dot_product`, which RADV provides and Honeykrisp
does not. Apple GPUs therefore run the plain scalar `mul_mm` path.

This is a driver limit, not a hardware limit. The Metal back end gates its
matrix path on `MTLGPUFamilyApple7` and uses `simdgroup_float8x8`. The same
8-core base M1 GPU reaches 117.96 tokens/s prompt processing under Metal and
38.29 under Honeykrisp, which is 0.32 times the Metal figure. The silicon
exposes a matrix primitive to Metal that Vulkan does not reach.

Nobody has measured a base M1 under Vulkan in 2026. Two extrapolations from the
June 2026 M1 Ultra figure agree. Core scaling gives 375.56 times 8 divided by
48, which is 62.6 tokens/s. Ratio scaling gives 48.6 percent of the base-M1
Metal figure, which is 57.3 tokens/s. Treat 55 to 65 tokens/s as an estimate for
pp512, not as a measurement. Token generation will not move, because it already
sits at 0.88 times the Metal figure.

### Correctness

llama.cpp issue 16188 reported garbage output from Honeykrisp on an M2 Pro with
gpt-oss-20b on 23 September 2025. GitHub shows that issue closed as completed on
11 November 2025. The closing reason could not be retrieved, and no pull request
references the issue. llama.cpp issue 10982, which compares Metal against Vulkan
on an M2 Max, is still open after twenty months, and its numbers were never
refreshed after the June 2026 changes.

### One contrary data point, correctly bounded

A base-M1 MacBook Air comparison on gemma-3 1B Q4_0 (20 April 2025) shows Metal
at 2.27 times the CPU on prompt processing and 0.85 times the CPU on token
generation. That is the strongest available case for a prompt-processing gain
from a GPU. Three limits reduce its value here. It uses a 1B model, not a 4B
model. It uses a fanless laptop, not a fan-cooled mini. It compares against a
macOS CPU build that links Accelerate and uses AMX. The same source shows a
Linux CPU-only build at 2.4 times the macOS CPU prompt-processing speed on an M2
Max. A ratio taken from a macOS CPU baseline must not be applied to OpenBSD.

### Summary of the possible gain

| Axis                           | Effect of a working OpenBSD GPU path                                                                                                            | Confidence                                           |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| Token generation               | No gain on the M1. The CPU and the GPU share 59 to 60 GB/s. Both land near 23.6 tokens/s at best for a 2.5 GB model. About 17 percent on an M2. | High                                                 |
| Prompt processing              | A real gain. An estimated 55 to 65 tokens/s against an untuned OpenBSD CPU build with no dot product and no BLAS.                               | Low, estimate only                                   |
| Cost                           | A kernel driver that does not exist in C, plus Mesa build work, plus a Mesa version bump in base.                                               | High                                                 |
| Cheaper alternative, same axis | One build-flag change in `devel/libggml`, plus a `llama-bench` measurement.                                                                     | High                                                 |
| Cheaper alternative, both axes | A Mac mini M2 or M2 Pro. OpenBSD lists both. No new driver is necessary.                                                                        | High for the machine list, low for the M2 Pro figure |

An estimate of the current OpenBSD CPU rate is 9 to 15 tokens/s as the port
ships, and 15 to 20 tokens/s after a rebuild with dot product and fp16. That
estimate is a derivation from the bandwidth measurement and the
instruction-count argument. It has low confidence, and only a measurement can
replace it.

The measurement procedure is short. Install OpenBSD 7.9 or `-current` on the Mac
mini M1. Run `pkg_add llama.cpp` and `pkg_add libggml`. Run
`sysctl hw.blockcpu=EL` to confine work to the four Firestorm cores. Run
`llama-bench -m qwen3-4b-q4_k_m.gguf -t 4 -p 512 -n 128`. Record the build
number from `llama-bench --version`. Confirm with `ldd` that only
`lib/libggml-cpu.so` loads.

**Sources**

- Hübner, Hu, Peng, Markidis, “Apple vs. Oranges”, arXiv 2502.05317v1, 7 Feb
  2025 — https://arxiv.org/html/2502.05317v1
- 7-cpu.com, Apple M1 (RAM read 64 GB/s, latency 91 ns; run shows Darwin 20.4.0,
  about 2021\) — https://www.7-cpu.com/cpu/Apple_M1.html
- EveryMac Mac mini M1 8-core specification, machine discontinued 17 Jan 2023 —
  https://everymac.com/systems/apple/mac_mini/specs/mac-mini-m1-8-core-2020-specs.html
- Wikipedia, Apple M1 (68.25 GB/s, LPDDR4X, Firestorm and Icestorm), read 1 Aug
  2026 — https://en.wikipedia.org/wiki/Apple_M1
- Wikipedia, Apple M2 (100 GB/s, 128-bit LPDDR5-6400; M2 Pro about 200 GB/s),
  read 1 Aug 2026 — https://en.wikipedia.org/wiki/Apple_M2
- Wikipedia, Apple M3 (102.4 GB/s, 128-bit LPDDR5-6400), read 1 Aug 2026 —
  https://en.wikipedia.org/wiki/Apple_M3
- Wikipedia, Apple M4 (120 GB/s, LPDDR5X), read 1 Aug 2026 —
  https://en.wikipedia.org/wiki/Apple_M4
- OpenBSD arm64 platform page (three Mac mini models: M1 2020, M2 2023, M2 Pro
  2023), read 1 Aug 2026 — https://www.openbsd.org/arm64.html
- `devel/libggml/Makefile`, rev 1.23, 20 Jul 2026 —
  https://cvsweb.openbsd.org/ports/devel/libggml/Makefile
- ggml v0.17.0 `src/ggml-cpu/CMakeLists.txt` —
  https://raw.githubusercontent.com/ggml-org/ggml/v0.17.0/src/ggml-cpu/CMakeLists.txt
- ggml v0.17.0 `src/ggml-cpu/ggml-cpu-impl.h` (`ggml_vdotq_s32` fallback) —
  https://raw.githubusercontent.com/ggml-org/ggml/v0.17.0/src/ggml-cpu/ggml-cpu-impl.h
- ggml v0.17.0 `src/ggml-cpu/ggml-cpu.c` (preprocessor-only feature accessors) —
  https://raw.githubusercontent.com/ggml-org/ggml/v0.17.0/src/ggml-cpu/ggml-cpu.c
- ggml v0.17.0 `CMakeLists.txt` (`GGML_BLAS_DEFAULT` on Apple only) —
  https://raw.githubusercontent.com/ggml-org/ggml/v0.17.0/CMakeLists.txt
- OpenBSD clang driver `ToolChains/Arch/AArch64.cpp` (default `generic`,
  `+strict-align`) —
  https://raw.githubusercontent.com/openbsd/src/master/gnu/llvm/clang/lib/Driver/ToolChains/Arch/AArch64.cpp
- `devel/libggml/pkg/PFRAG.cpu` and `PFRAG.amd64`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/ports/master/devel/libggml/pkg/PFRAG.cpu
  and
  https://raw.githubusercontent.com/openbsd/ports/master/devel/libggml/pkg/PFRAG.amd64
- `sys/arch/arm64/arm64/cpu.c` (`HWCAP_ASIMDDP`), read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/arm64/cpu.c
- `sys/arch/arm64/include/armreg.h` (`ID_AA64ISAR0_MASK`), read 1 Aug 2026 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/include/armreg.h
- llama.cpp discussion 4167, Apple Silicon Metal table, 22 Nov 2023 —
  https://github.com/ggml-org/llama.cpp/discussions/4167
- llama.cpp discussion 10879, Vulkan scoreboard, opened 18 Dec 2024 —
  https://github.com/ggml-org/llama.cpp/discussions/10879
- llama.cpp PR 24306, medium matmul tile on Asahi Linux, merged 11 Jun 2026 —
  https://github.com/ggml-org/llama.cpp/pull/24306
- llama.cpp PR 24663, roll bk loop for Asahi Linux, merged 30 Jun 2026 —
  https://github.com/ggml-org/llama.cpp/pull/24663
- llama.cpp PR 24123, `v_dot2_f32_f16` support, merged 9 Jun 2026 —
  https://github.com/ggml-org/llama.cpp/pull/24123
- llama.cpp issue 10982, Metal versus Vulkan on M2 Max, opened 26 Dec 2024, open
  — https://github.com/ggml-org/llama.cpp/issues/10982
- llama.cpp discussion 12985, M-series CPU, GPU, and container comparison, 16–20
  Apr 2025 — https://github.com/ggml-org/llama.cpp/discussions/12985
- llama.cpp issue 16188, garbage output on Honeykrisp, 23 Sep 2025, closed 11
  Nov 2025 — https://github.com/ggml-org/llama.cpp/issues/16188
- ports@, OpenBSD amd64 Vulkan `llama-bench` results, 1 Feb 2026 —
  https://marc.info/?l=openbsd-ports&m=176996345317519&w=2
- openbsd-arm search for `llama.cpp` (no hits), read 1 Aug 2026 —
  https://marc.info/?l=openbsd-arm&w=2&r=1&s=llama.cpp&q=b
- Qwen3-4B-Instruct-2507 GGUF file sizes, read 1 Aug 2026 —
  https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/tree/main

## 7. Other routes

| Route                                                     | Verdict                            | Why                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| --------------------------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Native AGX GPU on OpenBSD                                 | **Closed**                         | No kernel driver exists. No ICD exists. No C source exists upstream. See sections 4 and 5.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| OpenBSD guest under Apple Virtualization                  | **Boots, no GPU**                  | OpenBSD/arm64 became a working guest in January 2026. helg@ committed the `viogpu_wsmmap` fix on 12 January 2026, and sf@ committed an MTU fix. OpenBSD 7.9 states “Made OpenBSD work on Apple Virtualization”. The `viogpu(4)` manual page carries the date 20 April 2023 and states that the driver exists “to create a `wscons(4)` console”. The January 2026 commits changed `viogpu.c` to revision 1.13 and did not change that scope. `drm(4)`, dated 7 January 2022, lists amdgpu, inteldrm, and radeondrm only, and no newer list exists in the manual pages. The Apple framework exposes no 3D to Linux-style guests.                                                                                                                     |
| OpenBSD guest with API remoting                           | **Closed**                         | This is the fastest measured route on macOS. The guest talks to `/dev/dri`, and the host runs virglrenderer with API remoting and ggml-metal. Red Hat measured about 95 percent of native token generation, with Metal on an M4 Pro. That figure comes from Metal, so it does not transfer to a Linux host on an M1. The ggml side is upstream as `GGML_VIRTGPU` with `docs/backend/VirtGPU.md`. It needs only libdrm and a virtio-gpu DRM device in the guest, and no Vulkan ICD. OpenBSD has no virtio-gpu DRM driver, and that is the single missing piece. Two host options exist: macOS with libkrun or QEMU, and Asahi Linux with KVM and Honeykrisp. This report did not examine the Asahi host option, and no measurement of it was found. |
| macOS host runs `llama-server`, OpenBSD is an HTTP client | **Works today, breaks the design** | This needs no new code. The model runs on Metal on the M1. Inference then leaves the OpenBSD machine, the weights live on macOS, and pledge, unveil, and doas contain an HTTP client only. This is not local inference.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ggml RPC to a Metal host                                  | **Rejected**                       | Upstream states: “the functionality is fragile and insecure. Never run the RPC server on an open network or in a sensitive environment!” `SECURITY.md` advises against it. GHSA-j8rj-fmpv-wcxw (CVE-2026-34159), published 26 March 2026, is an unauthenticated remote code execution in the RPC back end, with CVSS 9.8, up to build b7991. The OpenBSD port does not build it, and the aarch64 package contains no RPC object.                                                                                                                                                                                                                                                                                                                   |
| eGPU over Thunderbolt                                     | **Closed**                         | Apple has never announced Apple Silicon eGPU support. The substantive statement in Apple’s own developer thread (December 2020) is that the M1 SoC does not support external GPUs and that the eGPU kexts target Intel only. The newest activity in that thread is November 2022. OpenBSD on the M1 also has no Thunderbolt stack and no PCIe-tunnelling stack.                                                                                                                                                                                                                                                                                                                                                                                    |
| `vmm(4)` and `vmd(8)` passthrough                         | **Closed for two reasons**         | `man.openbsd.org/arm64/vmm.4` returns HTTP 404, and `sys/arch/arm64` contains no vmm file, so `vmm` does not exist on arm64. On amd64, FAQ 16 lists graphics and hardware passthrough among the features that are “not available at this time”.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Apple Neural Engine                                       | **Closed**                         | The only free ANE driver is an out-of-tree Linux module (`eiln/ane`), and nobody merged it. llama.cpp has no ANE back end. Issue 10453 has been open since 22 November 2024. `ggml/CMakeLists.txt` defines no `GGML_ANE`, no `GGML_COREML`, and no `GGML_NEURAL`. All working ANE code routes through Core ML, which runs on macOS only.                                                                                                                                                                                                                                                                                                                                                                                                           |
| Another BSD on the same hardware                          | **Closed**                         | NetBSD is framebuffer-only, and its wiki page has had no edit since 7 May 2022. FreeBSD has five SoC drivers and claims no Apple support. DragonFly runs on amd64 only.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **amd64 OpenBSD plus an AMD GPU**                         | **Works, different machine**       | This is already real. A user ran the Vulkan back end on OpenBSD amd64 with a Radeon 7900 XTX in April 2026 (issue 21440). Build b8390 worked, build b8391 crashed, and `GGML_VK_ALLOW_GRAPHICS_QUEUE=1` restored it. Another user confirmed an RX 6600 on ports@ on 2 February 2025, and a two-card 7900 XTX result on 1 February 2026. Reference speed on Linux: an RX 6900 XT reaches 1901 pp512 and 108 tg128, which is about 16 times and 7.6 times a base M1. Two costs apply. OpenBSD is not a tested target for llama.cpp Vulkan, so upstream refactors break it without warning, and issue 21440 was closed as not planned. Hardware support beyond RDNA3 on OpenBSD is unverified.                                                        |

A note about amd64. Its advantage is not its CPU. A dual-channel amd64 desktop
has 50 to 90 GB/s of memory bandwidth. That is the same band as the M1
measurement of 59 GB/s, so CPU-only inference lands in the same 10 to 25
tokens/s range. The advantage is that a PCIe slot accepts a Radeon.

**Sources**

- undeadly.org, OpenBSD-current as guest under Apple Hypervisor, 15 Jan 2026 —
  https://www.undeadly.org/cgi?action=article;sid=20260115203619
- `viogpu(4)` manual page, dated 20 Apr 2023 — https://man.openbsd.org/viogpu.4
- `sys/dev/pv` listing (`viogpu.c` rev 1.13, 12 Jan 2026) —
  https://cvsweb.openbsd.org/src/sys/dev/pv/
- `drm(4)` manual page, dated 7 Jan 2022 — https://man.openbsd.org/drm.4
- Red Hat, near-native llama.cpp inference on macOS with API remoting, 18 Sep
  2025 —
  https://developers.redhat.com/articles/2025/09/18/reach-native-speed-macos-llamacpp-container-inference
- llama.cpp `docs/backend/VirtGPU.md`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/backend/VirtGPU.md
- llama.cpp `tools/server/README.md`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md
- llama.cpp `tools/rpc/README.md`, read 1 Aug 2026 —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/rpc/README.md
- GHSA-j8rj-fmpv-wcxw (CVE-2026-34159), 26 Mar 2026 —
  https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-j8rj-fmpv-wcxw
- Apple developer forum, eGPU support on Apple Silicon, Jun 2020 – Nov 2022 —
  https://developer.apple.com/forums/thread/650268
- OpenBSD FAQ 16 (vmm limitations), read 1 Aug 2026 —
  https://www.openbsd.org/faq/faq16.html
- llama.cpp issue 10453, “ggml : add ANE backend”, opened 22 Nov 2024, open —
  https://github.com/ggml-org/llama.cpp/issues/10453
- `ggml/CMakeLists.txt` (authoritative back-end list), read 1 Aug 2026 —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/CMakeLists.txt
- llama.cpp issue 21440, OpenBSD amd64 with 7900 XTX, 4 Apr 2026 —
  https://github.com/ggml-org/llama.cpp/issues/21440

## 8. What to check next

Each item below is a check that a reader can run. Items 1 to 3 are the cheap
checks that answer the open questions in this report. Items 4 to 6 must all pass
before GPU work becomes possible.

1. Run `llama-bench -m qwen3-4b-q4_k_m.gguf -t 4 -p 512 -n 128` on a Mac mini M1
   under OpenBSD, with `sysctl hw.blockcpu=EL`. Publish pp512, tg128, and the
   build number. This replaces the estimate of 9 to 15 tokens/s with a fact.
2. Rebuild `devel/libggml` with `-DGGML_CPU_ARM_ARCH=armv8.4-a+dotprod+fp16` and
   repeat check 1. The difference measures the cost of the missing dot-product
   instructions.
3. Repeat check 1 on a Mac mini M2, and on a Mac mini M2 Pro. OpenBSD lists both
   machines. The measured bandwidth of the M2 is 32 percent above the M1, and
   the specification peak of the M2 Pro is about three times the M1. This check
   costs one machine and no engineering.
4. Check whether an OpenBSD `src` commit adds an Apple GPU driver. Check whether
   a Mac mini dmesg stops printing `"gpu" at simplebus0 not configured`. This
   check does not depend on mainline Linux, because OpenBSD imports out-of-tree
   Apple DRM code already.
5. Check whether xenocara gains `lib/mesa/mk/libvulkan_asahi`, or whether
   `lib/mesa/mk/config.mk` gains an Apple Vulkan switch.
6. Run `vulkaninfo` on a Mac mini M1 under OpenBSD and check whether it
   enumerates a device. Run `llama-bench --list-devices` for the same check on
   the ggml side. One command then converts the whole question from inference to
   observation.
7. Check whether OpenBSD adds `drm_gem_shmem_helper.c`. Check whether the
   `STUB()` bodies leave `drm_syncobj_get_fd()` and
   `drm_syncobj_fd_to_handle()`.
8. Check whether xenocara updates Mesa past 25.0.7, so that the Apple user space
   targets the stable `asahi_drm.h` UAPI.
9. Check whether the llama.cpp Vulkan scoreboard gains a 2026 base-M1 Honeykrisp
   row. The current row dates from 21 November 2025 and predates two
   optimizations.
10. Check whether Mesa Honeykrisp advertises `VK_KHR_cooperative_matrix`, or
    advertises `integerDotProduct4x8BitPackedSignedAccelerated`. Either one
    opens an accelerated llama.cpp matmul path for Apple GPUs.
11. Check whether Asahi posts the full `drm/asahi` driver series to dri-devel.
    Only IGT test patches and generic Rust DRM work appeared up to 7 July 2026.
12. Check whether the OpenBSD `sysutils/m1n1` port moves to 1.6.x. That release
    needs Rust for the stage 2 build.
13. Check whether OpenBSD gains a virtio-gpu DRM driver. That driver would open
    the API-remoting route.
14. Check whether an OpenBSD developer states a plan, or a refusal, for an Apple
    GPU driver in public. No such statement exists today.

## 9. What this means for the specification

Five changes are proposed. The change to `spec/DECISIONS.md` needs human
approval.

**The specification must not treat the M1 as the only target.** OpenBSD lists
three Mac mini models: M1 (2020), M2 (2023), and M2 Pro (2023). The M2 gives 32
percent more measured CPU bandwidth than the M1. Token generation is
bandwidth-bound, so the machine sets the ceiling. A change of machine gains more
than a GPU can, and it needs no new code. `spec/inference.md` must record the
M-series bandwidth table and the machine list.

**D2 must stand, and its reason must change.** The decision “Inference: the
`misc/llama.cpp` port, CPU only” is correct. This research strengthens the
decision. The stated reason, “OpenBSD has no CUDA and no ROCm”, is not complete,
and on arm64 it misleads. It implies that a vendor runtime is the only missing
piece. The real reasons are different and stronger. OpenBSD/arm64 has no kernel
driver for the Apple GPU and no Apple Vulkan ICD. The one Apple GPU driver that
exists is Rust code in a rebasing branch. Token generation would gain nothing
from a GPU, because the M1 CPU and GPU share the same 59 to 60 GB/s of memory
bandwidth. The decision must also note that OpenBSD is not free of GPU support:
`devel/libggml` builds a Vulkan back end on amd64 and aarch64, and AMD GPU
offload works on amd64. The decision must say “CPU only on the target hardware”,
and it must not say “OpenBSD has no GPU path”.

**`spec/inference.md` must record the silent fallback.** An operator on Apple
hardware must know four facts. The package installs a Vulkan back end. The back
end loads. The back end finds no device. Inference then runs on the CPU with no
error. The Runtime section must state this.

**`spec/inference.md` must record the corrected bandwidth ceiling.** The
Performance section says that consumer hardware gives 10 to 15 tokens/s for a
7B-class model. Add the measured arithmetic for the target. A STREAM measurement
gives the M1 CPU 59 GB/s and the M1 GPU 60 GB/s. A 2.5 GB Q4_K_M file therefore
has a hard limit of 23.6 tokens/s on either engine. Remove any use of the 68.25
GB/s specification figure as a limit, because no engine reaches it.

**`spec/inference.md` must record the aarch64 build defect and the required
action.** `devel/libggml` passes no `-mcpu` value and no `-march` value on
aarch64. The aarch64 package therefore uses baseline armv8-a, with no
dot-product instructions and no BLAS. The amd64 package gets fourteen tuned CPU
variants, and the aarch64 package gets one untuned library. The OpenBSD kernel
exports `HWCAP_ASIMDDP` on this hardware, so the defect is in the port. FuguTTX
must measure `llama-bench` on the target machine before and after a rebuild with
`-DGGML_CPU_ARM_ARCH=armv8.4-a+dotprod+fp16`. FuguTTX must then send the result
to the port maintainer. Arm KleidiAI is a further aarch64 CPU back end that
needs no vendor runtime. All of these are in reach. The GPU is not.

The Development loop section stays correct. Local iteration uses llama.cpp with
Metal on Apple Silicon, and the shipped artifact is validated on OpenBSD CPU.
This research adds a reason. Metal on macOS reaches 3.1 times the
prompt-processing speed of the best measured Apple GPU path on a free operating
system.

## 10. Sources

All URLs below were read on 1 August 2026 unless another date is given. Dates
are the source dates, not the fetch dates.

### OpenBSD platform and drivers

- OpenBSD 7.9 release notes, 19 May 2026 — https://www.openbsd.org/79.html
- OpenBSD 7.9 changelog — https://www.openbsd.org/plus79.html
- OpenBSD -current changelog — https://www.openbsd.org/plus.html
- OpenBSD 7.5 release notes, 5 April 2024 — https://www.openbsd.org/75.html
- OpenBSD arm64 platform page — https://www.openbsd.org/arm64.html
- OpenBSD FAQ 16, virtualization — https://www.openbsd.org/faq/faq16.html
- `apldrm(4)`, 23 January 2024 — https://man.openbsd.org/apldrm.4
- `apldcp(4)` — https://man.openbsd.org/apldcp.4
- `drm(4)`, 7 January 2022 — https://man.openbsd.org/drm.4
- `viogpu(4)`, 20 April 2023 — https://man.openbsd.org/viogpu.4
- `modesetting(4)` — https://man.openbsd.org/modesetting.4
- `pledge(2)` — https://man.openbsd.org/pledge.2
- `sysctl(2)`, 4 April 2026 — https://man.openbsd.org/sysctl.2
- `arm64/vmm.4` — HTTP 404 — https://man.openbsd.org/arm64/vmm.4
- `sys/arch/arm64/conf/GENERIC` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/conf/GENERIC
- `sys/arch/arm64/arm64/cpu.c` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/arm64/cpu.c
- `sys/arch/arm64/include/armreg.h` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/include/armreg.h
- `lib/libc/gen/elf_aux_info.c` —
  https://raw.githubusercontent.com/openbsd/src/master/lib/libc/gen/elf_aux_info.c
- `sys/kern/kern_sched.c` (`hw.blockcpu`) —
  https://raw.githubusercontent.com/openbsd/src/master/sys/kern/kern_sched.c
- `sys/dev/pci/drm` listing — https://cvsweb.openbsd.org/src/sys/dev/pci/drm/
- `sys/dev/pci/drm/apple/apldrm.c` CVS log —
  https://cvsweb.openbsd.org/src/sys/dev/pci/drm/apple/apldrm.c
- `sys/dev/pci/drm/apple/iomfb_template.c` CVS log —
  https://cvsweb.openbsd.org/src/sys/dev/pci/drm/apple/iomfb_template.c
- `sys/dev/pci/drm/apple/dcp.h` CVS log —
  https://cvsweb.openbsd.org/src/sys/dev/pci/drm/apple/dcp.h
- `sys/dev/pci/drm/apple/apple_drv.c` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/dev/pci/drm/apple/apple_drv.c
- `sys/dev/pci/drm/drm_syncobj.c` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/dev/pci/drm/drm_syncobj.c
- `sys/arch/arm64/dev` listing —
  https://cvsweb.openbsd.org/src/sys/arch/arm64/dev/
- `sys/dev/pv` listing (`viogpu.c` rev 1.13, 12 January 2026) —
  https://cvsweb.openbsd.org/src/sys/dev/pv/
- OpenBSD clang `ToolChains/Arch/AArch64.cpp` —
  https://raw.githubusercontent.com/openbsd/src/master/gnu/llvm/clang/lib/Driver/ToolChains/Arch/AArch64.cpp
- undeadly.org, KMS on Apple Silicon, 25 January 2024 —
  https://undeadly.org/cgi?action=article&sid=20240125064408
- undeadly.org, guest under Apple Hypervisor, 15 January 2026 —
  https://www.undeadly.org/cgi?action=article;sid=20260115203619
- undeadly.org front page and g2k26 report, 13 July 2026 — https://undeadly.org/
- M2 MacBook Pro dmesg on misc@, 16 September 2025 —
  https://www.mail-archive.com/misc@openbsd.org/msg195186.html
- misc@ thread on M1 dual boot and firmware, 5–6 March 2026 —
  https://marc.info/?l=openbsd-misc&m=177280567725465&w=2
- openbsd-cvs, `if_bwfm_pci.c` from an Asahi diff, 12 July 2024 —
  https://marc.info/?l=openbsd-cvs&m=172077318907370&w=2
- Theo de Raadt on safe languages, 3 December 2017 —
  https://marc.info/?l=openbsd-misc&m=151233345723889&w=2
- openbsd-cvs search for `agx` —
  https://marc.info/?l=openbsd-cvs&w=2&r=1&s=agx&q=b
- openbsd-cvs search for `asahi` —
  https://marc.info/?l=openbsd-cvs&w=2&r=1&s=asahi&q=b
- openbsd-tech search for `asahi` —
  https://marc.info/?l=openbsd-tech&w=2&r=1&s=asahi&q=b
- openbsd-tech search for `apldrm` —
  https://marc.info/?l=openbsd-tech&w=2&r=1&s=apldrm&q=b
- openbsd-arm search for `llama.cpp` —
  https://marc.info/?l=openbsd-arm&w=2&r=1&s=llama.cpp&q=b
- openbsdonapple.wiki, 25 April 2025 —
  https://openbsdonapple.wiki/doku.php?id=apple_silicon:installation
- EuroBSDcon 2026 schedule, published 15 July 2026 —
  https://events.eurobsdcon.org/2026/schedule/export/schedule.json
- AsiaBSDCon 2026 schedule —
  https://2026.asiabsdcon.org/entry/schedule/export/schedule.json

### OpenBSD graphics and ports

- xenocara `lib/mesa/VERSION` (Mesa 25.0.7, merged 5 June 2025) —
  https://raw.githubusercontent.com/openbsd/xenocara/master/lib/mesa/VERSION
- xenocara `lib/mesa/mk/Makefile` —
  https://raw.githubusercontent.com/openbsd/xenocara/master/lib/mesa/mk/Makefile
- xenocara `lib/mesa/mk/config.mk` —
  https://raw.githubusercontent.com/openbsd/xenocara/master/lib/mesa/mk/config.mk
- xenocara `lib/mesa/src/asahi` —
  https://cvsweb.openbsd.org/xenocara/lib/mesa/src/asahi/
- xenocara `lib/mesa/src/gallium/drivers/asahi` —
  https://cvsweb.openbsd.org/xenocara/lib/mesa/src/gallium/drivers/asahi/
- xenocara arm64 xserv set list —
  https://raw.githubusercontent.com/openbsd/xenocara/master/distrib/sets/lists/xserv/md.arm64
- xenocara arm64 xbase set list —
  https://raw.githubusercontent.com/openbsd/xenocara/master/distrib/sets/lists/xbase/md.arm64
- `devel/libggml/Makefile`, rev 1.23, 20 July 2026 —
  https://cvsweb.openbsd.org/ports/devel/libggml/Makefile
- `devel/libggml/pkg/PLIST`, `PFRAG.cpu`, `PFRAG.amd64`, `PFRAG.vulkan` —
  https://raw.githubusercontent.com/openbsd/ports/master/devel/libggml/pkg/PLIST
- `devel/libggml/patches` listing —
  https://github.com/openbsd/ports/tree/master/devel/libggml/patches
- `misc/llama.cpp/Makefile` (b10063, 20 July 2026) —
  https://raw.githubusercontent.com/openbsd/ports/master/misc/llama.cpp/Makefile
- OpenBSD aarch64 snapshot packages —
  https://cdn.openbsd.org/pub/OpenBSD/snapshots/packages/aarch64/
- `graphics/vulkan-loader` 1.4.341.0, page dated 29 July 2026 —
  https://openports.pl/path/graphics/vulkan-loader
- ports@ “llama.cpp vulkan” proposal, 31 January 2025 —
  https://www.mail-archive.com/ports@openbsd.org/msg131307.html
- ports@ pledge question by Stuart Henderson, 1 February 2025 —
  https://www.mail-archive.com/ports@openbsd.org/msg131310.html
- ports@ RX 6600 confirmation, 2 February 2025 —
  https://www.mail-archive.com/ports@openbsd.org/msg131332.html
- ports@ `GGML_CPU_ALL_VARIANTS` for amd64, 5 November 2025 —
  https://marc.info/?l=openbsd-ports&m=176230046830792&w=2
- ports@ amd64 Vulkan `llama-bench` results, 1 February 2026 —
  https://marc.info/?l=openbsd-ports&m=176996345317519&w=2

### Linux, Asahi, and Mesa

- Linux `drivers/gpu/drm` at master —
  https://github.com/torvalds/linux/tree/master/drivers/gpu/drm
- Linux `drivers/gpu/drm` at tag v6.7 —
  https://github.com/torvalds/linux/tree/v6.7/drivers/gpu/drm
- Linux `drivers/gpu/drm/adp/Kconfig` —
  https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/adp/Kconfig
- `include/uapi/drm/asahi_drm.h` commit history, commit 8 April 2025 —
  https://github.com/torvalds/linux/commits/master/include/uapi/drm/asahi_drm.h
- `AsahiLinux/linux` `drivers/gpu/drm/asahi` (24 Rust files) —
  https://github.com/AsahiLinux/linux/tree/asahi-wip/drivers/gpu/drm/asahi
- Phoronix, Asahi UAPI header for Linux 6.16, 9 April 2025 —
  https://www.phoronix.com/news/Linux-6.16-Ashai-UAPI-Header
- Phoronix, Rust DRM for Linux 7.1, 31 March 2026 —
  https://www.phoronix.com/news/Rust-DRM-For-Linux-7.1
- Asahi Linux, Progress Report: Linux 6.19, 15 February 2026 —
  https://asahilinux.org/2026/02/progress-report-6-19/
- Asahi Linux, Progress Report: Linux 7.1, 30 June 2026 —
  https://asahilinux.org/2026/06/progress-report-7-1/
- Asahi Linux, passing the torch, 13 February 2025 —
  https://asahilinux.org/2025/02/passing-the-torch/
- Alyssa Rosenzweig, stepping away, 26 August 2025 —
  https://alyssarosenzweig.ca/blog/asahi-gpu-part-n.html
- Alyssa Rosenzweig, Vulkan 1.4 on Asahi, 2 December 2024 —
  https://alyssarosenzweig.ca/blog/vulkan-14-sur-asahi-linux.html
- Asahi feature support, M1 —
  https://asahilinux.org/docs/platform/feature-support/m1/
- Rust for Linux, Apple AGX GPU driver —
  https://rust-for-linux.com/apple-agx-gpu-driver
- dri-devel search for `asahi` —
  https://www.mail-archive.com/search?l=dri-devel%40lists.freedesktop.org&q=asahi&start=0
- patchwork.kernel.org, dri-devel filtered on `asahi` —
  https://patchwork.kernel.org/project/dri-devel/list/?q=asahi&state=*&archive=both
- Mesa release notes index — https://docs.mesa3d.org/relnotes.html
- Mesa license — https://docs.mesa3d.org/license.html

### llama.cpp, ggml, and performance

- ggml v0.17.0 `CMakeLists.txt` —
  https://raw.githubusercontent.com/ggml-org/ggml/v0.17.0/CMakeLists.txt
- ggml v0.17.0 `src/ggml-cpu/CMakeLists.txt` —
  https://raw.githubusercontent.com/ggml-org/ggml/v0.17.0/src/ggml-cpu/CMakeLists.txt
- ggml v0.17.0 `src/ggml-cpu/ggml-cpu.c` —
  https://raw.githubusercontent.com/ggml-org/ggml/v0.17.0/src/ggml-cpu/ggml-cpu.c
- ggml v0.17.0 `src/ggml-cpu/ggml-cpu-impl.h` —
  https://raw.githubusercontent.com/ggml-org/ggml/v0.17.0/src/ggml-cpu/ggml-cpu-impl.h
- ggml v0.17.0 `src/ggml-cpu/arch/arm/quants.c` —
  https://raw.githubusercontent.com/ggml-org/ggml/v0.17.0/src/ggml-cpu/arch/arm/quants.c
- llama.cpp discussion 4167, Apple Silicon Metal table, 22 November 2023 —
  https://github.com/ggml-org/llama.cpp/discussions/4167
- llama.cpp discussion 10879, Vulkan scoreboard, 18 December 2024 —
  https://github.com/ggml-org/llama.cpp/discussions/10879
- llama.cpp PR 24306, medium matmul tile on Asahi Linux, 11 June 2026 —
  https://github.com/ggml-org/llama.cpp/pull/24306
- llama.cpp PR 24663, roll bk loop for Asahi Linux, 30 June 2026 —
  https://github.com/ggml-org/llama.cpp/pull/24663
- llama.cpp PR 24123, `v_dot2_f32_f16` support, 9 June 2026 —
  https://github.com/ggml-org/llama.cpp/pull/24123
- llama.cpp issue 10982, Metal versus Vulkan, 26 December 2024 —
  https://github.com/ggml-org/llama.cpp/issues/10982
- llama.cpp discussion 12985, M-series container benchmarks, 16–20 April 2025 —
  https://github.com/ggml-org/llama.cpp/discussions/12985
- llama.cpp issue 16188, Honeykrisp garbage output, 23 September 2025, closed 11
  November 2025 — https://github.com/ggml-org/llama.cpp/issues/16188
- llama.cpp issue 21440, OpenBSD amd64 with 7900 XTX, 4 April 2026 —
  https://github.com/ggml-org/llama.cpp/issues/21440
- llama.cpp issue 10453, ANE back end request, 22 November 2024 —
  https://github.com/ggml-org/llama.cpp/issues/10453
- llama.cpp `ggml/CMakeLists.txt` —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/CMakeLists.txt
- llama.cpp `ggml/src/ggml-vulkan/CMakeLists.txt` —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/ggml/src/ggml-vulkan/CMakeLists.txt
- llama.cpp `docs/build.md` —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/build.md
- llama.cpp `docs/backend/VirtGPU.md` —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/backend/VirtGPU.md
- llama.cpp `tools/rpc/README.md` —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/rpc/README.md
- llama.cpp `tools/server/README.md` —
  https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md
- GHSA-j8rj-fmpv-wcxw (CVE-2026-34159), 26 March 2026 —
  https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-j8rj-fmpv-wcxw
- Red Hat, near-native macOS container inference, 18 September 2025 —
  https://developers.redhat.com/articles/2025/09/18/reach-native-speed-macos-llamacpp-container-inference
- geerlingguy/ai-benchmarks README (CPU reference points) —
  https://raw.githubusercontent.com/geerlingguy/ai-benchmarks/master/README.md
- Andreas Kunar, llama.cpp performance and Apple Silicon, 2 December 2023 —
  https://medium.com/@andreask_75652/llama-cpp-performance-apple-silicon-051241dd6eae

### Hardware and other BSDs

- Hübner, Hu, Peng, Markidis, “Apple vs. Oranges: Evaluating the Apple Silicon
  M-Series SoCs for HPC Performance and Efficiency”, arXiv 2502.05317v1, 7
  February 2025 — https://arxiv.org/html/2502.05317v1
- 7-cpu.com, Apple M1 (undated page; run shows Darwin 20.4.0, about 2021) —
  https://www.7-cpu.com/cpu/Apple_M1.html
- EveryMac, Mac mini M1 8-core specification —
  https://everymac.com/systems/apple/mac_mini/specs/mac-mini-m1-8-core-2020-specs.html
- Wikipedia, Apple M1 — https://en.wikipedia.org/wiki/Apple_M1
- Wikipedia, Apple M2 — https://en.wikipedia.org/wiki/Apple_M2
- Wikipedia, Apple M3 — https://en.wikipedia.org/wiki/Apple_M3
- Wikipedia, Apple M4 — https://en.wikipedia.org/wiki/Apple_M4
- Apple developer forum, eGPU on Apple Silicon, June 2020 – November 2022 —
  https://developer.apple.com/forums/thread/650268
- NetBSD evbarm Apple wiki, last edited 7 May 2022 —
  https://wiki.netbsd.org/ports/evbarm/apple/
- NetBSD port-arm status, 11 April 2025 —
  http://mail-index.netbsd.org/port-arm/2025/04/11/msg009163.html
- FreeBSD `sys/arm64/apple` —
  https://github.com/freebsd/freebsd-src/tree/main/sys/arm64/apple
- FreeBSD 15.0 hardware notes — https://www.freebsd.org/releases/15.0R/hardware/
- DragonFly BSD supported hardware, 4 January 2024 —
  https://www.dragonflybsd.org/docs/supportedhardware/
- eiln/ane, out-of-tree Linux ANE driver — https://github.com/eiln/ane
- segaboy/vulkan-netbsd, Lavapipe on NetBSD, compiles but not run —
  https://github.com/segaboy/vulkan-netbsd

## Appendix: incorrect statements

The evidence refutes each statement below. A reader must not repeat them.

- “OpenBSD has no GPU support.” `drm(4)` supports amdgpu, inteldrm, and
  radeondrm, and Vulkan offload works on amd64.
- “OpenBSD imports DRM drivers only from mainline Linux.” Kettenis imported
  `sys/dev/pci/drm/apple` from the Asahi `asahi-wip` branch on 22 January 2024,
  and Gray has carried it through each mainline sync since.
- “Mainline entry is a precondition for an OpenBSD Apple GPU driver.” Practice
  shows otherwise. The blockers are the absence of a C driver, a moving firmware
  ABI, and the absence of a developer.
- “The Apple GPU driver was upstreamed to Linux in 2023.” Only the UAPI header
  is in mainline, since Linux 6.16. Mainline holds `drm/adp`, which serves
  pre-DCP Touch Bar controllers, and that is a different driver.
- “OpenBSD is years behind on DRM.” The live gap is about eight months, and that
  gap is a secondary cost.
- “Licensing blocks a port.” The Asahi driver is `GPL-2.0-only OR MIT`, and
  OpenBSD already used the MIT arm.
- “OpenBSD forbids Rust in the kernel.” This is unproven. `src` contains no
  Rust, and no current primary statement of policy exists.
- “A working GPU path would give no gain at all.” Token generation would gain
  nothing, because the CPU and GPU share 59 to 60 GB/s. Prompt processing would
  gain, and the size of that gain is unmeasured on OpenBSD.
- “The Apple Vulkan path is slow because Apple GPUs lack cooperative matrix.”
  Two changes in June 2026 raised Apple GPU prompt processing by 81 percent with
  the device still reporting `matrix cores: none`. The causes were tile
  selection and instruction-cache pressure.
- “The 68.25 GB/s figure is the token-generation limit on an M1.” Measurement
  gives 59 GB/s for the CPU and 60 GB/s for the GPU. The correct limit for a 2.5
  GB model is 23.6 tokens/s.
- “The OpenBSD aarch64 package is a tuned CPU build.” It is built for baseline
  armv8-a, with one untuned `libggml-cpu.so` and no BLAS.
- “Apple Hypervisor plus virtio-gpu is a GPU path.” The Apple framework exposes
  no 3D, and OpenBSD has no virtio-gpu DRM driver.
- “January 2026 news about an OpenBSD GPU driver fix means Apple GPU progress.”
  Those reports describe a virtio-gpu memory-mapping fix for VM guests.
