# The Apple Silicon lab, and a staged plan for FuguAGX

**Date: 21 August 2026. Status: research note. This document changes no
specification text, and it starts no GPU work.**

FuguAGX is a working name for a driver that does not exist: a C implementation
of an Apple AGX GPU driver for OpenBSD. This document designs the physical lab
around that driver, the automation that operates it, and the staged plan that
must precede any driver code. It also designs the smaller lab that the
specification already requires for CPU measurement on target hardware.

Two companion documents supply the context.
[OpenBSD and the Apple GPU](openbsd-apple-silicon-gpu.md) gives the evidence
that no Apple GPU driver exists for OpenBSD, and that token generation on a Mac
mini M1 gains nothing from a GPU.
[Draft plan: Apple GPU support for OpenBSD on the Mac mini](apple-gpu-openbsd-draft-plan.md)
sketches the driver work as gates G0 to G9, estimates 15 to 30 person-months,
and argues that the work must not start. This document supplies the mechanisms,
the sequence, the gates, and the cost.

One naming rule applies throughout. This document calls the machines and their
automation “the lab”, and the software on the controller “the lab control
plane”. The word “harness” names the `ttx` program of
[spec/harness.md](../../spec/harness.md), which decision
[D7](../../spec/DECISIONS.md#d7) governs. D7 does not constrain the lab control
plane, because that software never runs on an OpenBSD target.

## 1. Verdict

The lab is worth building. The driver is not worth starting yet. Three tiers of
commitment separate the two.

**Tier 1 is mandated, and it is unconditional.**
[INF-ARM64](../../spec/inference.md#inf-arm64) states four measurement steps,
and then states: “GPU work must not start without these results.”
[INF-LATENCY](../../spec/inference.md#inf-latency) sets a five-minute budget for
the reference task on the M1 reference machine, and states that `llama-bench`
numbers do not substitute for a full-turn measurement.
[D2](../../spec/DECISIONS.md#d2) states that the harness smoke suite must pass
on the target arm64 hardware before a release. This duty needs one target
machine, one controller, byte-exact serial capture, and a way to reset a wedged
machine. It needs no change to any decision.

**Tier 2 is three checks, under $600 in total.** Each check can end the GPU
project on its own. K1 measures a Mac mini M2 Pro. K2 finds a named OpenBSD
reviewer. K3 runs `agx_boot.py` on one Mac mini M1. Section 4 gives each check
and its stop rule.

**Tier 3 needs three approvals.** The full lab and the driver must not start
until the three checks pass, until a human amends D2, and until a human approves
the spend.

**The gain is real on one axis only.** Token generation cannot improve on a Mac
mini M1. A STREAM measurement gives the M1 CPU 59 GB/s and the M1 GPU 60 GB/s,
and token generation reads all weights for each token. Prompt processing can
improve. A change of target machine beats the driver on the axis that matters:
the M2 measures 78 GB/s, and the M2 Pro carries a 200 GB/s specification peak.
That is about 2.9 times the M1 on token generation, with no new code, against no
gain at all from an M1 GPU.

**Four platform mechanisms that a lab of this kind assumes do not exist on
OpenBSD/arm64.** Section 6 names each one. The most consequential is that the
kernel writes no crash dumps. The captured serial log is the only kernel-side
post-mortem artifact that the platform can produce.

**Two facts size the driver, and neither is negotiable.** The GPU MMU granule is
a fixed 16 KB, and OpenBSD/arm64 uses 4 KB pages. The OpenBSD m1n1 port is
pinned at 1.5.2, which precedes the release that moved GPU initialization into
the bootloader. Section 5 gives both.

## 2. Method, and how to read the evidence

All URLs in section 19 were read on 21 August 2026 unless another date is given.
Dates are the source dates, not the fetch dates.

Platform claims come from primary sources: the OpenBSD source tree, the OpenBSD
manual pages, the OpenBSD ports tree, the m1n1 tree, the reference driver in the
`asahi-wip` branch, the Asahi documentation, and the Asahi progress reports.

Three markers apply. A claim that a primary source states carries no marker, and
section 19 gives the source. A claim that this document derives from other facts
carries the word **estimate**. A claim that no reachable source proves carries
the word **UNVERIFIED**. A reader must not remove the word UNVERIFIED when the
reader copies a line into another document.

Section 17 lists every open check. Each open check names the method that
resolves it, and the iteration that owns it. A table that mixes measurement with
estimate carries a Confidence column.

Negative results appear as findings. Where this document states that a facility
does not exist, it names the file and the line that show the absence.

## 3. What the specification already requires

The measurement duty exists whatever happens to FuguAGX. It sets the floor for
the lab.

**The duty.** [INF-ARM64](../../spec/inference.md#inf-arm64) states four steps.
Run `llama-bench` on the target machine with the package as it ships. Rebuild
`devel/libggml` with `-DGGML_CPU_ARM_ARCH=armv8.4-a+dotprod+fp16`. Run
`llama-bench` again, and record the difference. Send both results to the port
maintainer. The unit then states: “GPU work must not start without these
results.” That prohibition is specification text.

**The defect behind the duty.** The port sets `-DGGML_NATIVE=OFF` for all
architectures, and `-DGGML_CPU_ALL_VARIANTS=on` for amd64 only. It never sets
`GGML_CPU_ARM_ARCH`, and it passes no `-mcpu` value and no `-march` value. The
aarch64 package therefore builds for baseline armv8-a. `__ARM_FEATURE_DOTPROD`
stays undefined, so each `ggml_vdotq_s32` expands to six NEON instructions in
place of one `SDOT`. ggml does no runtime ARM feature detection, so the loss
cannot return at run time. The aarch64 package installs one untuned
`libggml-cpu.so`, and the amd64 package installs fourteen tuned variants. The
kernel exports `HWCAP_ASIMDDP` on this hardware, so the defect is in the port.

**The second duty.** [INF-LATENCY](../../spec/inference.md#inf-latency) sets a
pre-registered bar. The reference task is “Block inbound SSH, except from
10.0.0.0/8, in pf.conf”, up to the confirmation prompt. It must complete in five
minutes or less on the M1 reference machine, at Q4_K_M, through the harness. The
measurement covers full agent turns: prompt processing, generation, and tool
time. Only a human changes the budget, with a recorded reason, before a
measurement runs.

**Measurement discipline.** Pin the cores with `sysctl hw.blockcpu=SLE`, which
leaves only the four M1 performance cores in the scheduler. Record
`machdep.compatible`, which reads `apple,j274` on a Mac mini M1. Record
`hw.ncpuonline` and the build number from `llama-bench --version` in the run
database. Confirm with `ldd` that only `lib/libggml-cpu.so` loads. The Vulkan
back end loads on aarch64, finds no device, and falls back to the CPU with no
error message.

**The minimum lab.** One target machine, byte-exact serial capture, and a way to
reset a wedged machine. Nothing in this list is conditional on FuguAGX.

## 4. Three checks that can end the project

The three checks below cost under $600 in total. They need no lab. Each one can
end the GPU project on its own. An engineer must run all three before any tier-3
spend.

| Check                              | Cost                              | What it settles                                               | Stop rule                                                                        |
| ---------------------------------- | --------------------------------- | ------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| K1 — measure a Mac mini M2 Pro     | about EUR 6 rented                | Whether a machine change beats a driver on token generation   | A confirmed extrapolation ends the driver ladder, and the project buys a machine |
| K2 — find a named OpenBSD reviewer | correspondence, 2 to 4 weeks      | Whether the result can enter the OpenBSD tree                 | No named reviewer means stop                                                     |
| K3 — run `agx_boot.py` on one M1   | one machine, one cable, one human | Whether the light loop works at all                           | A failure inside the effort bound ends the central premise of the plan           |
| G1 — DRM-core plumbing             | engineering time only             | Not a stop rule. It is useful whether or not FuguAGX proceeds | —                                                                                |

**K1 — measure a Mac mini M2 Pro.** Rent an Apple Silicon instance rather than
buy a machine. The project already installs the Scaleway CLI through
`make deps`. The published rate is about EUR 0.21 to EUR 0.24 per hour with a
24-hour minimum, so about EUR 5 to EUR 6 for one day. The two rates disagree, so
an engineer must confirm the current rate before booking (open check 1). Run the
same model file and the same `llama-bench` arguments as the tier-1 measurement.
One limitation applies: the rental runs macOS, so it settles the
memory-bandwidth ceiling only, and it cannot discharge the OpenBSD measurement
duty.

The reference figures are these. The M1 CPU measures 59 GB/s and the M1 GPU 60
GB/s, which is about 85 percent of the 67 GB/s specification peak, and which
gives a ceiling of 23.6 tokens/s for a 2.5 GB Q4_K_M file. The M2 measures 78
GB/s, which gives 31.2 tokens/s. The M2 Pro carries a 200 GB/s specification
peak and no measured figure, which extrapolates to about 68 tokens/s. An
engineer must not use 68.25 GB/s as a ceiling for the M1, because no engine
reaches it.

**K2 — find a named OpenBSD reviewer.** This is gate G0 of the draft plan, and
this plan schedules it first. Confirm the SoC-to-GPU mapping for all three
machines: t8103 to G13G, t8112 to G14G, and t6020 to G14S. Survey the firmware
ABI versions that the three machines ship. Choose between strategy S2, a rewrite
in C that keeps the Linux UAPI, and strategy S3, a bespoke compute-only driver
with a private UAPI. Then find an OpenBSD developer who will review and commit
the result. Unreviewed kernel code does not enter OpenBSD, and a driver outside
the tree does not survive two DRM syncs.

**K3 — run the light loop once.** One Mac mini M1, one SuperSpeed USB-C cable,
and one human in the room. Prepare the machine once from 1TR as section 7
specifies. Then run `proxyclient/experiments/agx_boot.py`. That script is 27
lines. It powers `/arm-io/gfx-asc` and `/arm-io/sgx` through the PMGR, builds
the init data, boots the gfx-asc firmware, and drops to a Python shell. It is
the only self-contained AGX experiment in the m1n1 tree. An engineer must set an
effort bound before the work starts.

**K3 carries a known risk.** The ten AGX experiments have had no substantive
commit since 25 November 2022, except `agx_tracetimings.py` on 24 November 2024.
The supporting modules `proxyclient/m1n1/agx` and `proxyclient/m1n1/fw/agx` last
moved on 25 November 2024\. The only 2026 commit that touches an experiment is a
tree-wide rename on 25 March 2026\. Hector Martin resigned as project lead in
February 2025. Asahi Lina, who wrote nearly all of the AGX Python code and the
Rust driver, paused Apple GPU driver work in March 2025. Alyssa Rosenzweig
joined Intel in August 2025. `agx_1tri.py` hardcodes `base = "gpudata/bunny/"`
and loads five memory images that the repository does not contain.
`agx_renderframe.py` needs a frame archive that the hypervisor tracer produces.
Only `agx_boot.py` runs from a clean checkout.

**G1 is free value, and it is not a stop rule.** Gate G1 of the draft plan is
DRM-core plumbing. It adds `drm_gem_shmem_helper.c`, implements the
`drm_syncobj` fd export and import paths, which return `-ENOSYS` today, and adds
`DMA_BUF_IOCTL_IMPORT_SYNC_FILE` and `DMA_BUF_IOCTL_EXPORT_SYNC_FILE`. It needs
no Apple hardware. It helps every DRM driver in OpenBSD, and it is committable
whether or not FuguAGX proceeds. Its exit criterion: `inteldrm` and `amdgpu`
still work on amd64, and the new helpers pass their own tests. One licence
question applies first. Linux `drm_gem_shmem_helper.c` carries
`SPDX-License-Identifier: GPL-2.0` with no MIT arm, unlike `drm_gpuvm.c`, which
carries `GPL-2.0-only OR MIT` and which OpenBSD already holds. Open check 12
covers it.

## 5. The constraints that shape every choice

1. **OpenBSD has no loadable kernel modules.** Every driver change needs a full
   kernel relink and a reboot of the target. The procedure is fixed:
   `cd /sys/arch/arm64/conf`, `cp GENERIC.MP FUGUAGX`, `config FUGUAGX`,
   `cd ../compile/FUGUAGX`, `make`, `make install`. An engineer must build on
   the target architecture, because OpenBSD FAQ 5 states that cross-compiling
   tools exist for developers who bring up a new platform, and that those tools
   are not maintained for general use. No public measurement of an OpenBSD/arm64
   kernel build on Apple Silicon exists (open check 4). The lab must therefore
   make reboots free, automatic, and safe.

2. **The GPU has two failure classes, not one.** A GPU MMU fault, a job timeout,
   or a channel error halts the firmware, and the driver resumes it in place. In
   `gpu.rs`, `recover()` waits up to 100 ms for the firmware `halted` flag in
   the shared `fw_status` structure, then writes `halted = 0` and `resume = 1`.
   `handle_channel_error()` sends a `RecoverChannel` device-control message and
   rings the doorbell. In-flight jobs fail with `ETIMEDOUT`, `EIO`, or
   `ECANCELED`, and the machine continues to run. The cost is milliseconds. An
   RTKit-level firmware crash is different: the driver sets `crashed = true`,
   emits a core dump, fails all jobs with `ENODEV`, and does not restart the
   coprocessor. The cost is one reboot. iBoot loads and write-protects the
   firmware at each boot, so a plain reboot restores it. A power cycle is not
   necessary.

3. **No emulator exists for the AGX.** All driver tests run on physical Apple
   hardware. The lab control plane carries no such limit, and an OpenBSD/arm64
   virtual machine can stand in during control-plane development. The limit of
   that substitute is precise. A QEMU `virt` guest has no `apldog`, no `exuart`
   on `apple,s5l-uart`, no m1n1, no U-Boot console routing, no PMU boot error
   counter, and no VDM path, and it does have netboot, which Apple hardware does
   not. A virtual target proves the API, the lease logic, the run database, the
   test runner, and the artifact store. It does not prove the boot, console,
   watchdog, panic-capture, or reimage adapters.

4. **The GPU MMU granule is 16 KB, and OpenBSD/arm64 uses 4 KB pages.**
   `drivers/gpu/drm/asahi/pgtable.rs` sets `UAT_PGBIT = 14`, `UAT_LEVELS = 3`,
   and `UAT_IAS = 39`. The reference driver Kconfig reads
   `depends on PAGE_SIZE_16KB`. `sys/arch/arm64/include/param.h` line 50 sets
   `#define PAGE_SHIFT 12`. Every GPU mapping therefore needs 16 KB of
   physically contiguous and 16 KB-aligned backing, which is an order-2
   allocation on a 4 KB-page kernel. Scattered page lists cannot serve directly.
   Three candidate answers exist: an order-2 contiguous allocation for each
   mapping, a 16 KB-page OpenBSD arm64 build, or a shadow layer. None has a
   precedent in the reference implementation. An engineer must decide this on
   paper before any kernel code starts.

5. **The driver invalidates the GPU TLB with CPU instructions that OpenBSD does
   not provide.** `mem.rs` emits outer-shareable ARMv8.4 forms under
   `.arch armv8.4-a`: `tlbi vmalle1os`, `tlbi aside1os`, `tlbi vae1os`, and
   `tlbi rvae1os`. Its own module comment states that the GPU uses CPU-side
   outer-shareable `tlbi` instructions to manage its TLBs, that the driver picks
   its own ASIDs, that it does not coordinate them with the CPU, and that this
   needs a fix. OpenBSD `sys/arch/arm64/arm64/cpufunc_asm.S` provides the
   inner-shareable forms only, and `sys/arch/arm64/arm64/pmap.c` allocates ASIDs
   in pairs from a global bitmap. New outer-shareable helpers and ASID
   reservation from pmap are both necessary.

6. **The firmware ABI tracks macOS by hand, and the menu is short.** `driver.rs`
   reads `apple,firmware-compat` and accepts exactly five pairs: G13 with 12.3,
   G14 variant G with 12.4, G13 with 13.5, G14 variant G with 13.5, and other
   G14 variants with 13.5, which route to the G14X build. Any other value logs
   an unsupported combination and returns `ENODEV`. m1n1 sets the property from
   the ADT `/chosen` `firmware-version` value, and folds 12.3.1 to 12.3, and
   13.5b4 and 13.6.1 to 13.5. The Asahi installer offers four IPSW choices, and
   on a Mac mini M1, board ID `j274ap`, the default is macOS 13.5 with
   `iBoot-8422.141.2`. A lab that pins every M1 to 13.5 removes this whole class
   of problem.

7. **Two loops exist, and the order between them is fixed.** The heavy loop
   edits C, builds a kernel, boots the target, and runs tests, at minutes for
   each iteration. The light loop drives live hardware from Python over the m1n1
   proxy, with no OpenBSD kernel involved, at seconds for each iteration. Asahi
   Linux developed its driver on the light loop first. The agent must exhaust
   the light loop before it pays for the heavy loop.

## 6. Platform mechanisms, and the state of each

The lab rests on seventeen platform mechanisms. The table gives the state of
each against a primary source. Status takes exactly three values: works, works
with conditions, and does not exist on this platform.

| #   | Mechanism                            | Status                          | Condition or substitute                                                                                                                                                                                                                                                                                                                                                                                                             |
| --- | ------------------------------------ | ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | m1n1 proxy, stage 1                  | works with conditions           | 153 proxy opcodes: memory and MMIO access, cache and MMU control, SMP, DART mapping, PCIe, NVMe reads, framebuffer, PMGR power domains, hypervisor control, and kboot. Needs a `RELEASE` plus `CHAINLOADING` stage 1, a one-time 1TR preparation, and a host that wins a five-second race at each boot. Section 7.                                                                                                                  |
| 2   | m1n1 stage 2, as OpenBSD ships it    | does not exist on this platform | The `sysutils/m1n1` port builds with `RELEASE=1` and without `CHAINLOADING=1`, so `EARLY_PROXY_TIMEOUT` is never compiled in. Its U-Boot payload boots, so it never calls `usb_init()`. No proxy, and no USB gadget.                                                                                                                                                                                                                |
| 3   | `exuart(4)` serial console           | works with conditions           | Console at 115200 baud on compatible `apple,s5l-uart`. `exuart* at fdt?` is line 199 of arm64 GENERIC and line 142 of RAMDISK. The line leaves the SoC on the SBU pins of the DFU port at 1.2 V, and it needs a USB-PD vendor-defined message. A charging cable does not carry it. Section 8.                                                                                                                                       |
| 4   | `/bsd.upgrade` one-shot kernel slot  | works                           | `upgrade()` in `sys/stand/boot/cmd.c` requires the owner execute bit. The loader prints “upgrade detected”, then clears `S_IXUSR`, `S_IXGRP`, and `S_IXOTH` after a successful load. `sysupgrade(8)` uses the same slot, and it must never run on a lab target.                                                                                                                                                                     |
| 5   | efiboot fall-back to `/bsd`          | works                           | On a failed load, efiboot retries `/bsd`, adds a second to the timeout on the first failure, and disables the timeout on the second.                                                                                                                                                                                                                                                                                                |
| 6   | efiboot `esp` device                 | works                           | `boot esp0a:/bsd.rd` loads a kernel from the EFI system partition. It survives a destroyed OpenBSD root filesystem. That partition also holds m1n1, U-Boot, and the vendor firmware, so it must never be recreated.                                                                                                                                                                                                                 |
| 7   | `/obsd` second known-good kernel     | works                           | `make install` runs `ln -f /bsd /obsd` and records a SHA256 in `/var/db/kernel.SHA256`. That checksum is a ready-made kernel identity for the run database.                                                                                                                                                                                                                                                                         |
| 8   | `apldog(4)` watchdog                 | works with conditions           | Resets a hung kernel, and supplies `cpuresetfn`, which is how OpenBSD resets this hardware. `kern.watchdog.auto` defaults to 1, so the kernel pats the watchdog itself; a userland check-in gate needs 0. The period ceiling is `UINT32_MAX` divided by the 24 MHz `clkref`, which is 178 seconds on the t8103. The driver registers only under `#ifndef SMALL_KERNEL`, so bsd.rd has no watchdog. It disarms at `DVACT_POWERDOWN`. |
| 9   | `ddb(4)`                             | works with conditions           | `db_panic` defaults to 1. `db_console` defaults to 0, because `option DDB_SAFE_CONSOLE` is commented out at `sys/conf/GENERIC` line 8. At securelevel above 0 these sysctls can only be lowered. There is no `panic` command: use `call panic`, or `sysctl ddb.trigger=1` from a process whose controlling terminal is the console. It must not be armed together with a watchdog.                                                  |
| 10  | `savecore(8)` and kernel crash dumps | does not exist on this platform | `cpu_dump_mempagecnt()` returns 0, and the per-segment memory loop of `cpu_dump()` sits inside `#if 0`, so `dumpconf()` leaves `dumpsize` at 0 and `dumpsys()` prints “dump to dev %u,%u not possible”. `/var/crash` is always empty. Substitute: the serial log, plus the backtrace that `panic()` prints through `db_stack_dump()`.                                                                                               |
| 11  | `autoinstall(8)` by netboot          | does not exist on this platform | `configs/apple_m1_defconfig` sets `CONFIG_NO_NET=y` in upstream U-Boot and in the Asahi fork, so efiboot has no EFI Simple Network Protocol. Substitute: the two response-file paths of section 10.                                                                                                                                                                                                                                 |
| 12  | `tmpfs`                              | does not exist in GENERIC       | `option TMPFS` is commented out at `sys/conf/GENERIC` line 42, and `option MFS` is enabled at line 35. OpenBSD has no modules to load it with. Substitute: `mount_mfs(8)`.                                                                                                                                                                                                                                                          |
| 13  | `bge(4)` built-in Ethernet           | works                           | 1 Gb Ethernet on a Broadcom BCM57762 with a BCM57765 PHY. The MAC address comes from the device-tree `local-mac-address` property. `bge` is in GENERIC and in RAMDISK, so bsd.rd can use it.                                                                                                                                                                                                                                        |
| 14  | `macvdmtool` and `tuxvdmtool`        | works with conditions           | They give serial mode, debugusb mode, reboot, and DFU entry with no button press. The host must be a second Apple Silicon Mac, because both tools drive that host’s own CD321x controller over i2c at address 0x38. An x86 host cannot send USB-PD vendor-defined messages at all.                                                                                                                                                  |
| 15  | Central Scrutinizer                  | works                           | Pre-boot UART, VDM hard reset through the Mac’s own PD controller, and USB 2.0 pass-through for tethered boot. An FUSB302, level shifters, and an RP2040. No prebuilt unit was found, so the board needs fabrication (open check 11).                                                                                                                                                                                               |
| 16  | `kisd`                               | works with conditions           | Tunnels the SoC hardware UART over DebugUSB, and presents a pty. It needs m1n1 1.6.0 or newer. Entry into DebugUSB still needs a VDM, so `kisd` does not remove the VDM hardware requirement.                                                                                                                                                                                                                                       |
| 17  | PMU boot error counter               | hazard, not a mechanism         | Repeated boot failures divert the machine into macOS recovery. m1n1 clears the counter at each proxy connection, through `PMU(u).reset_panic_counter()`. Nothing on the OpenBSD path clears it. Section 11.                                                                                                                                                                                                                         |

**Note A, on crash dumps.** OpenBSD/arm64 writes no kernel crash dumps.
`savecore(8)`, `/var/crash`, and the `boot crash` and `boot dump` commands
inside `ddb` all produce nothing on this platform. The kernel message buffer is
no substitute, because `msgbufphys` comes from `pmap_steal_avail()` and lands at
a boot-dependent physical address. Section 12 states the consequence: per-run,
byte-exact serial capture is a hard requirement, and not a convenience.

**Note B, on the watchdog and the debugger.** `watchdog(4)` states that a
combination of watchdog timers with `ddb(4)` is unwise, because the debugger can
stop the watchdog from resetting its timeout, and the machine then reboots
before any debugging can happen. The manual page recommends `ddb.panic=0` for
machines that must not stop. A kernel at the `ddb>` prompt runs no timeouts, and
pats nothing. Section 11 turns this into two mutually exclusive boot regimes.

**Note C, on substitutes.** Where a mechanism does not exist, the table names
what replaces it. The serial log and `db_stack_dump()` replace `savecore(8)`.
The two response-file paths replace netboot. `mount_mfs(8)` replaces `tmpfs`.

## 7. The m1n1 proxy: how to have it, and what it costs

The proxy is the light loop and the recovery deploy. Three layers gate it.

**Build time.** `config.h` line 11 reads `//#define EARLY_PROXY_TIMEOUT 5`,
commented out. The build defines it only inside `#ifdef RELEASE` and then
`#ifdef CHAINLOADING`.

| Build                                     | Flags                      | Early proxy       | Rust needed                     |
| ----------------------------------------- | -------------------------- | ----------------- | ------------------------------- |
| Developer build                           | `make`                     | no                | 1.6.0 and later, yes; 1.5.x, no |
| Stage 1, as the Asahi installer builds it | `RELEASE=1 CHAINLOADING=1` | yes, five seconds | always                          |
| Stage 2, as OpenBSD builds it             | `RELEASE=1`                | no                | 1.6.0 and later, yes; 1.5.x, no |

**Run time.** `run_actions()` in `src/main.c` takes the early-proxy branch only
when three conditions hold together. `EARLY_PROXY_TIMEOUT` must be compiled in.
`cur_boot_args.video.display` must be false, which means the machine booted
verbose. `lp_sip0` must equal 127, read from the ADT node `/chosen/asmb`
property `lp-sip0`, which means a permissive boot policy. m1n1 then polls every
USB iodev for five seconds, and enters `uartproxy_run()` the moment the host can
write. Otherwise control falls through to `payload_run()`, and a successful
payload returns without a call to `usb_init()`.

**One-time human preparation, from 1TR on the target.** Two commands:
`csrutil disable`, which prompts for volume selection and authentication, and
`nvram boot-args=-v`. The Asahi documentation states that the proxy backdoor
needs both verbose mode and disabled SIP, and that verbose mode alone gives
debug output but no proxy backdoor in recent m1n1 builds. This is a deliberate
and permanent security downgrade. It is acceptable only because the targets hold
nothing of value. `csrutil enable` reverses it. No agent and no controller can
perform this step.

**Winning the race.** Hold the device open continuously, so that the five-second
window is never missed. `proxyclient/tools/picocom-sec.sh` ships the loop: it
waits for `/dev/ttyACM1` to appear, runs `picocom` at 500000 baud, and sleeps
one second. Run proxy scripts with `M1N1DEVICE=/dev/ttyACM0`.

**The gadget.** `src/usb_dwc3.c` defines a CDC device at VID 0x1209 and PID
0x316d, with an ACM interface. `usb_iodev_init()` brings it up on every
dual-role USB controller in the ADT, so the gadget appears on both Thunderbolt
ports of a Mac mini M1. Each port presents two ACM nodes: the first is the
proxy, and the second is the hypervisor virtual UART.

**Where the proxy lives, and what that bounds.** m1n1 stage 1 lives in the APFS
stub on the target’s internal disk, which `kmutil configure-boot` installs.
Tethered boot therefore recovers everything below stage 1: a corrupt stage 2, a
broken U-Boot, an unbootable efiboot, or a bad kernel, with no working OpenBSD
filesystem. It does not recover a destroyed stage 1 or a destroyed APFS stub.
That is the exact boundary between the last automated recovery tier and the DFU
tier.

**Chainload means two different things.** On-device chainloading is stage 1 that
mounts the EFI system partition and loads stage 2 from it. Over the proxy,
`proxyclient/tools/chainload.py` is a Mach-O and raw loader that sets up Apple
`BootArgs` and preserves SEPFW. It loads a fresh m1n1 or XNU, and it cannot boot
U-Boot or an EFI application. The tool for the OpenBSD chain is
`proxyclient/tools/linux.py`, which takes `-u` for U-Boot and `-E` for an EFI
payload, and which refuses `-E` without `-u`. A precedent exists:
`proxyclient/tools/freebsd.py`, contributed by Kyle Evans on 3 April 2022 and
updated by Ayrton Munoz on 25 September 2024 to use the standard U-Boot
`bootefi` command. No OpenBSD equivalent exists in the tree. An `openbsd.py` on
that model is a modest and well-precedented piece of work.

**The version gap that blocks the driver.** Commit `f9dd8b3`, dated 11 May 2025,
moved GPU initialization out of the kernel driver and into the m1n1 Rust code,
across 3,860 lines and 20 files. `dt_set_gpu()` in `src/kboot_gpu.c` now
publishes the `hw-cal-a`, `hw-cal-b`, and `globals` reserved-memory nodes, the
`uat-handoff`, `uat-pagetables`, and `uat-ttbs` regions, and the
`apple,firmware-version`, `apple,firmware-compat`, `apple,firmware-abi`, and
leak-coefficient properties, together with an OPP table. Asahi states that this
removed the need for the kernel driver to handle the floating-point values in
Apple’s hardware initialization data, and that it simplified the device-tree
bindings. This is a large gift to a non-Linux driver, because m1n1 prepares the
FDT that U-Boot hands onward. It exists only from m1n1 1.6.0, dated 17
June 2026. The OpenBSD `sysutils/m1n1` port sets `GH_TAGNAME= v1.5.2`, at
Makefile revision 1.17, committed on 5 January 2026, and
`sysutils/firmware/apple-boot` tracks it. An update of that port is a hard
prerequisite for FuguAGX, and it is not free: 1.6.0 is the first release that
requires Rust for the stage 2 build. Open check 6 covers whether the published
properties reach the OpenBSD kernel.

## 8. The physical links, and what each one carries

Two different things travel over USB-C to a target. They are alive at different
times, and they need different cables and different hardware.

**The m1n1 USB gadget** is a CDC-ACM device that the m1n1 firmware creates. It
exists only while m1n1 runs, and only under the conditions of section 7. It
disappears the moment m1n1 hands control to its payload. It travels over a plain
USB-C cable.

**The Apple debug UART** is a single 1.2 V line at 115200 baud. iBoot, m1n1,
U-Boot, efiboot, and the OpenBSD `exuart0` all share it. It leaves the SoC on
the SBU pins of one USB-C port, which on a Mac mini is the port nearest the
power plug, and which is also the DFU port. The port enters debug mode only
after a USB-PD vendor-defined message. Serial mode uses the SBU pins, so the
cable must be USB 3.0 SuperSpeed or Thunderbolt with SBU1 and SBU2 connected.
DebugUSB mode works over plain USB 2.0, and it still needs the vendor-defined
message.

| Boot stage       | m1n1 USB gadget                       | Debug UART               | Network                              | HDMI                                        |
| ---------------- | ------------------------------------- | ------------------------ | ------------------------------------ | ------------------------------------------- |
| iBoot            | dead                                  | alive                    | dead                                 | dead                                        |
| m1n1 stage 1     | alive, under the section 7 conditions | alive                    | dead                                 | alive, framebuffer console                  |
| m1n1 stage 2     | dead, as OpenBSD builds it            | alive                    | dead                                 | alive                                       |
| U-Boot           | dead                                  | alive                    | no network device, `CONFIG_NO_NET=y` | alive                                       |
| efiboot          | dead                                  | alive, `boot>` prompt    | dead                                 | alive                                       |
| OpenBSD kernel   | dead                                  | alive, `exuart0` console | alive after `bge0` attaches          | not the kernel console on a headless target |
| OpenBSD userland | dead                                  | alive, getty at 115200   | alive, SSH                           | not the kernel console                      |

| Link                      | Hardware                                           | Cable                              | What it gives                               |
| ------------------------- | -------------------------------------------------- | ---------------------------------- | ------------------------------------------- |
| Proxy                     | Plain USB-C to the controller                      | any                                | The m1n1 gadget, alive only while m1n1 runs |
| Console and pre-boot UART | Central Scrutinizer, or a second Apple Silicon Mac | SuperSpeed or Thunderbolt with SBU | Every boot stage, and VDM reset             |
| Power                     | One outlet on a metered PDU                        | —                                  | Hard power cycle, and draw telemetry        |
| Display                   | USB HDMI capture                                   | —                                  | m1n1 and boot-loader output                 |

**Console routing on a headless machine.** Four layers decide where the console
goes. The Apple device tree sets `/chosen/stdout-path = "serial0"`, and
`serial0` is the `apple,s5l-uart` node. U-Boot `ft_board_setup()` rewrites that
to `/chosen/framebuffer` only when four conditions hold together: the code does
not run at EL1 under the m1n1 hypervisor, a `UCLASS_KEYBOARD` device exists, the
U-Boot `stdout` variable contains `vidconsole`, and `/chosen/framebuffer` is
enabled. A headless Mac mini has no SPI keyboard, and `usb start` finds no USB
keyboard, so the rewrite does not happen and the console stays on the serial
line. Inside efiboot, the `cons`, `com0`, and `fb0` devices all call the same
input and output functions, so `set tty com0` does not move the `boot>` prompt.
It changes only the `/chosen/stdout-path` value that efiboot writes for the
kernel. `cnspeed()` on arm64 always returns 115200, so `stty` is present and
inert.

**One lab rule follows.** An operator must never attach a keyboard to a target.
A keyboard moves `/chosen/stdout-path` to the framebuffer. That silently moves
the OpenBSD kernel console off the serial line, and it removes the only
kernel-side post-mortem channel from that machine, in a way that looks like a
hardware fault. The lab must assert at L0 that the running console device
matches the expected one.

## 9. The lab

**The tier-1 lab, for the measurement duty.** One Mac mini M1 target, one small
always-on controller, one VDM adapter for the console, and byte-exact serial
capture. That is the whole of what the measurement duty needs.

**The tier-3 lab, for the driver.** The roles table below applies.

| Role                  | Machine                        | Tier                            | Purpose                                                                                                                                                                                                                                                                        |
| --------------------- | ------------------------------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Target fleet          | 2 or 3 used Mac mini M1, 16 GB | 1 for the first, 3 for the rest | The machines under test. One stays known-good, to separate driver faults from faulty units. All pinned to macOS 13.5 OS firmware.                                                                                                                                              |
| Oracle                | 1 Mac mini M1 on Asahi Linux   | 3                               | Runs the reference Rust driver. Supplies reference results and firmware traces through the m1n1 hypervisor.                                                                                                                                                                    |
| Build host            | Mac mini M2 Pro on OpenBSD     | 2, in part                      | Native kernel builds. It is a third ABI port, and not a spare M1: t6020 is GPU core G14S, which routes to the separate G14X build with different fault and core-mask registers, up to two clusters, and a compute preemption buffer of 0x25980 bytes against 0x7f80 on the M1. |
| Lab controller        | Small always-on Linux box      | 1                               | Runs the proxy clients, the serial servers, the power control, the artifact store, and the lab API. The only machine the agent talks to. It cannot send vendor-defined messages.                                                                                               |
| Rescue or control Mac | One Apple Silicon Mac          | 3                               | DFU restore and VDM control. Design B below makes it unnecessary as a separate machine.                                                                                                                                                                                        |

Two physical designs exist.

**Design A, a Central Scrutinizer for each target.** One controller does
everything: the m1n1 proxy over plain USB-C, and the pre-boot UART and VDM reset
through the Scrutinizer. DFU needs a separate macOS rescue host. The cost is one
fabricated board for each target, plus the rescue machine.

**Design B, an Apple Silicon Mac as the control hardware.** Wire the DFU port of
each target to a small Apple Silicon Mac. That machine runs `macvdmtool` on
macOS, or `tuxvdmtool` and `kisd` on Asahi Linux, and it covers reboot,
debugusb, serial, and DFU entry over one link. It replaces both the Scrutinizer
and the separate rescue host. The oracle machine is an Apple Silicon Mac that
runs Asahi Linux already, so it can take this role for one target. Design B also
automates the DFU tier, because `macvdmtool dfu` puts a target into DFU with no
button press.

One correction forces the choice. An x86 controller cannot send USB-PD
vendor-defined messages at all, because `macvdmtool` and `tuxvdmtool` both drive
the host Mac’s own CD321x controller over i2c. VDM control needs Apple Silicon
at the other end, or dedicated FUSB302 hardware.

**Firmware pinning, as lab discipline.** Three firmware versions exist on an
Apple Silicon machine. The OS container firmware, ADT
`/chosen/firmware_version`, is what the Asahi installer sets, and it determines
the GPU firmware ABI. Install every M1 target with the installer default, which
gives macOS 13.5 and `iBoot-8422.141.2`. The system firmware, ADT
`/chosen/system_firmware_version`, is global and permanent: Asahi states that
global firmware updates are effectively permanent, and that only a DFU restore
rolls them back. The peripheral firmware blobs live in the EFI system partition.

Three rules follow. The lab must record `iBoot-8422.141.2` for every target in
the run database, and assert it at boot. A target must never take a macOS
update, and a lab machine must never run a developer beta. A mismatch on
`/chosen/firmware_version` must quarantine the target, and must not raise a
warning only.

**Network and isolation.** The lab network is an isolated VLAN. The targets hold
nothing of value. The controller holds the artifact store, and it is backed up.
Built-in Ethernet works: `bge(4)` on a Broadcom BCM57762 with a `brgphy(4)`
BCM57765 PHY, with a distinct MAC address for each machine read from the
device-tree `local-mac-address` property, so DHCP reservations and per-MAC
response files both work.

## 10. Kernel deployment, boot control, and reimaging

The known-good path stays untouched at all times. The normal deploy needs no
console interaction.

**Deploying a candidate kernel.** Use the one-shot slot of the boot loader.
`upgrade()` in `sys/stand/boot/cmd.c` stats `/bsd.upgrade` and requires the
owner execute bit. `boot()` then switches the image, prints “upgrade detected:
switching to /bsd.upgrade”, and after a successful load calls `fchmod()` to
clear `S_IXUSR`, `S_IXGRP`, and `S_IXOTH`. The next boot returns to `/bsd` with
no operator action. The command is
`install -F -m 700 bsd.test /bsd.upgrade && chmod u+x /bsd.upgrade && sync && reboot`.
A candidate that panics or hangs reverts at the next reset, whatever caused that
reset. `sysupgrade(8)` uses the same slot, and it must never run on a lab
target.

**Three backstops.** efiboot falls back to `/bsd` when the selected image fails
to load, adds a second to the timeout on the first failure, and disables the
timeout on the second. `make install` runs `ln -f /bsd /obsd` before it
installs, which gives a second known-good kernel, and records a SHA256 in
`/var/db/kernel.SHA256` that serves as the kernel identity in the run database.
`boot esp0a:/bsd.test` loads a kernel from the FAT partition that already holds
`BOOTAA64.EFI`, m1n1, and U-Boot, which survives a destroyed OpenBSD root
filesystem.

**boot.conf notes.** The loader refuses `/etc/boot.conf` unless uid 0 owns it
and it is not world-writable. The default prompt timeout is 5 seconds, and a
`boot` command in the file suppresses the prompt. arm64 efiboot compiles with
`-DBOOT_STTY`, so the variables are `set howto`, `set device`, `set image`,
`set timeout`, `set tty`, and `set db_console`.

**Tethered boot as the recovery deploy.** Boot the target over the m1n1 proxy
when the disk boot chain is broken. Use `linux.py`-style loading, and not
`chainload.py`: `-u` loads U-Boot first, and `-E` treats the payload as an EFI
stub. An `openbsd.py` on the `freebsd.py` model performs this. The boundary of
section 7 applies: this recovers everything below stage 1, and nothing above it.

**Reimaging, two paths, and no netboot.** `autoinstall(8)` starts
non-interactively from three triggers only: a human who answers (A) at the
install prompt, a netboot, or a response file on the built-in RAM disk of
bsd.rd. Netboot is impossible on this hardware, because
`configs/apple_m1_defconfig` sets `CONFIG_NO_NET=y` in both upstream U-Boot and
the Asahi fork, so efiboot has no network device to bind to. Two paths remain.

Path A upgrades an intact system. Place `/bsd.upgrade`, a copy of bsd.rd, and
`/auto_upgrade.conf` on the root filesystem. The bsd.rd profile runs
`/upgrade -ax`, and `check_unattendedupgrade()` in `install.sub` mounts the `a`
partition of the root disk read-only, requires both files, copies the response
file to the ramdisk root, and proceeds with no console interaction.

Path B installs cleanly after the root filesystem is destroyed. Bake the
response file into bsd.rd with `rdsetroot(8)`: `rdsetroot -x bsd.rd disk.fs`,
`vnconfig vnd0 disk.fs`, `mount /dev/vnd0a /mnt`, copy `auto_install.conf`,
unmount, `vnconfig -u vnd0`, then `rdsetroot bsd.rd disk.fs`. Stage that bsd.rd
through the one-shot slot, or on the EFI system partition. The profile finds the
response file, prints a five-second warning, and starts the autoinstall.

**Three things that will cause failures.** The EFI system partition must
survive. `distrib/arm64/ramdisk/install.md` sets `KEEP_EFI_SYS=true` on Apple
hardware, with the comment that the partition holds boot firmware and must not
be recreated, and the installer reads Wi-Fi firmware from
`vendorfw/firmware.tar` on that same partition. An operator must never run
`installboot -p` on an Apple target, and the lab must check before a reimage
that the partition still holds m1n1, U-Boot, and the vendor firmware. An arm64
bsd.rd is 18,732,300 bytes, which matters when it is staged on that partition
(open check 7). The unattended run carries its own stall watchdog:
`WATCHDOG_PERIOD_SEC=$((30 * 60))` in `distrib/miniroot/install.sub` reboots a
stalled run after 30 minutes. That figure is the only platform-supplied bound on
reinstall duration, and the real duration is open check 5.

**Scratch space.** Tests write to an mfs filesystem through `mount_mfs(8)`, and
not to tmpfs. `option TMPFS` is commented out at `sys/conf/GENERIC` line 42,
`option MFS` is enabled at line 35, and OpenBSD has no modules to load it with.
The lab must assert at L0 that the scratch filesystem is mounted and
memory-backed, so that a failed mount fails the run instead of a silent write to
the root filesystem.

## 11. Two boot regimes, and the recovery ladder

A watchdog and the kernel debugger must not be armed on the same boot. The lab
must choose a regime for each run, and record the choice in the run database.

**The unattended regime is the default.** `/etc/sysctl.conf` carries
`ddb.panic=0`, `ddb.console=0`, and `kern.watchdog.auto=0`. The test runner arms
the watchdog by a write to `kern.watchdog.period` at each check-in, or
`watchdogd(8)` does it. In this regime `panic()` calls `db_stack_dump()` itself,
which prints a full backtrace, and then reboots. The machine therefore prints
its own backtrace on the serial line and reboots without help, so the lab needs
no scripted debugger session and parses the captured log instead.

**The interactive-debug regime is entered deliberately.** `/etc/sysctl.conf`
carries `ddb.panic=1` and `ddb.console=1`, and `kern.watchdog.period=0`. The
kernel stops at the `ddb>` prompt on the serial console. The useful commands are
`show panic`, `trace`, `trace /t <pid>`, `ps`, `show registers`,
`show all pools`, `machine`, and `boot reboot` to leave. An operator must never
use this regime during a soak.

**Three constraints apply to both regimes.** At securelevel above 0 the debugger
sysctls can only be lowered, so `/etc/sysctl.conf` must set them, or `boot.conf`
must set `db_console`, before init raises securelevel. `exuart` discards a BREAK
while `sc->sc_tty` is NULL, so BREAK into the debugger works only after the
console getty starts, and it cannot catch an early-boot hang. To induce a panic
for a test, use `call panic` at the `ddb>` prompt, or `sysctl ddb.trigger=1`
from a process whose controlling terminal is the console. The debugger has no
`panic` command.

| Tier | Trigger                              | Action                                                                                                                                   | Cost                              | Status                                                                                                                    |
| ---- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| T0   | Test run complete                    | Graceful `reboot(8)` over SSH                                                                                                            | seconds                           | verified                                                                                                                  |
| T1   | GPU fault, timeout, or channel error | None. The driver resumes the firmware in place, and jobs fail with `ETIMEDOUT`, `EIO`, or `ECANCELED`                                    | milliseconds                      | verified in the reference driver. This is a test result, and not a machine failure                                        |
| T2   | Kernel panic                         | With `ddb.panic=0` the kernel prints the panic string, then the `db_stack_dump()` backtrace, then reboots. The lab parses the serial log | one boot                          | verified. No crash dump is written                                                                                        |
| T3   | Kernel hang                          | `apldog(4)` fires                                                                                                                        | up to 178 seconds, plus boot time | verified. Needs `kern.watchdog.auto=0` for a userland check-in gate                                                       |
| T4   | Bad candidate kernel                 | Nothing to do. The loader already cleared the execute bits, and the reset returns to `/bsd`                                              | one boot                          | verified                                                                                                                  |
| T5   | Broken root filesystem               | `boot esp0a:/bsd.rd`, then reimage by path A or path B                                                                                   | minutes                           | verified for the `esp` device; the reimage duration is open check 5                                                       |
| T6   | Wedged SoC, no proxy, no SSH         | VDM hard reset through the Central Scrutinizer or `macvdmtool`                                                                           | seconds                           | the tools are verified; untested on a lab target                                                                          |
| T7   | VDM reset fails                      | The PDU power-cycles the outlet                                                                                                          | seconds                           | UNVERIFIED that a Mac mini M1 that runs OpenBSD restarts when AC returns. Open check 3, and a blocking pre-purchase check |
| T8   | Destroyed stage 1 or APFS stub       | DFU restore, then the Asahi installer, then the 1TR preparation, then an OpenBSD install                                                 | hours                             | requires a human                                                                                                          |

One caution belongs with T0. An operator must never issue a bare `halt(8)` on a
target, because `boot()` on arm64 prints a prompt and blocks for a key press,
and `apldog_activate()` has already disarmed the watchdog at `DVACT_POWERDOWN`.

**The tier boundary that matters.** The lab enters the DFU tier exactly when the
target no longer offers the m1n1 proxy after a VDM reset and a power cycle. That
is a testable predicate. It stops the lab from spending the timeout budgets of
the intermediate tiers against an unreachable proxy.

**The rung that needs a human.** A DFU restore returns the machine to stock
macOS. It destroys the APFS stub, m1n1 stage 1, U-Boot, the EFI system
partition, and the OpenBSD install. Between the restore and any `autoinstall(8)`
run sit an Asahi installer run, which is interactive and needs network access
and 1TR authentication, and then the `csrutil disable` and `nvram boot-args=-v`
preparation. This rung is outside any claim of zero-touch operation. The
mitigation is to keep the rung rare, through protection of the EFI system
partition.

**The hazard under every rung.** The Apple PMU keeps a boot error count in
non-volatile scratchpad storage, and enough consecutive failures divert the
machine into macOS recovery. The m1n1 proxy client clears the counter at every
connection, and nothing on the OpenBSD path clears it. Tiers T2 to T7 generate
failed boots by design, all night. Three mitigations exist. The lab can schedule
a deliberate proxy touch for each soak cycle, because any proxy connection
clears the counter. The lab can reimplement the reset in OpenBSD, which already
has SPMI and i2c on Apple SoCs. The lab can accept the risk, and add a
diagnostic step that suspects the counter before it suspects a destroyed boot
chain. The first option is nearly free, and it must be the default.

## 12. Observability

The agent cannot look at the machine. OpenBSD/arm64 gives exactly one
kernel-side post-mortem artifact, so this design has no redundancy on that axis.

**Serial capture is a hard requirement.** Every byte of every boot, stored for
each run. This is the only kernel-side post-mortem channel that the platform
produces, for the reason in section 6 note A. It carries the panic string, the
`db_stack_dump()` backtrace, and every driver message. A run without serial
capture is a run with no evidence.

**The GPU tells its own story.** On a firmware crash the reference driver writes
an ELF64 core dump of every mapped firmware and kernel UAT page, with segment
permissions derived from the UAT page-table entries. It adds two named notes: an
`AGX` note that carries the init-data address, chip ID, GPU generation, variant,
revision, active core count, and a six-word firmware version, and an `RTKIT`
note that carries the firmware crashlog. FuguAGX must do the same. This artifact
reaches userland without the proxy.

**Four firmware receive rings.** The firmware sends a syslog ring with several
sub-channels, a ktrace ring, a statistics ring, and an event ring. The firmware
log is the account that the GPU gives of its own failure, and the lab must
capture it for each run beside the console log.

**Two cheap liveness probes.** ASC register 0x48, `CPU_STATUS`, carries
`CPU_STOPPED` at bit 1 and `CPU_IDLE` at bit 0. The m1n1 proxy reads them over
USB with no kernel involved. That is faster and more specific than a power
flatline.

**Proxy memory dumps.** After a GPU-side wedge, the proxy dumps the firmware log
ring buffers and the shared-memory regions. This covers the GPU side only, and
it needs a machine that still reaches m1n1.

**SMC sensors.** `aplsmc(4)` exposes current, fan, power, temperature, and
voltage sensors through the `hw.sensors` tree, read over SSH while the target is
alive. `sensorsd(8)` can act on thresholds without a poll from the lab.

**Power telemetry.** The metered PDU reports the draw for each outlet. A
flatline during a GPU job means a hang. This signal notifies, and it must not
block.

**HDMI frames.** On demand. Section 8 bounds what they show: m1n1 and
boot-loader output, and not the kernel console.

**The run database.** Every boot gets a run ID. The row stores the kernel SHA256
from `/var/db/kernel.SHA256`, the source diff, the boot regime, the asserted
`apple,firmware-abi` value, the `/chosen/firmware_version` string,
`machdep.compatible`, `hw.blockcpu`, the console log, the test outcomes, and
links to every artifact. The agent bisects through a query against its own
history, instead of a re-run.

## 13. Testing, the structure extractor, and the oracle

[D8](../../spec/DECISIONS.md#d8) states that each outcome has a
machine-checkable definition of done. Every rung below carries a checkable pass
condition.

| Level | Content      | Pass condition                                                                                                                                                                                                                                                                                                       | Cost                        |
| ----- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| L0    | Boot         | The target checks in over SSH inside a deadline. The scratch mfs filesystem is mounted and memory-backed. The console device matches the expected one. `apple,firmware-abi` matches the pinned value                                                                                                                 | one boot                    |
| L1    | Attach       | The driver attaches and the RTKit handshake completes: write `CPU_RUN` to ASC register 0x44, boot RTKit, start endpoints 0x20 and 0x21, send the init-data address on 0x20 and the mode word on 0x21, then ring doorbell 0x10. The firmware version is logged, and the machine stays stable for a stated idle period | one boot                    |
| L2    | One dispatch | One trivial compute job writes a constant into a buffer, and a readback verifies it. This is gate G3                                                                                                                                                                                                                 | one boot                    |
| L3    | Conformance  | The ported IGT asahi tests and the DRM selftests pass. Render targets verify by checksum                                                                                                                                                                                                                             | minutes                     |
| L4    | Faults       | Induced GPU faults and timeouts recover in place, with `fault_control=0`. Only the RTKit-crash path costs a reboot, and it runs separately                                                                                                                                                                           | milliseconds for each fault |
| L5    | End to end   | `vulkaninfo` enumerates the device through a Honeykrisp ICD, `llama-bench` runs, and the generated text matches the CPU output inside a stated tolerance                                                                                                                                                             | minutes                     |
| Soak  | Nightly      | Hours of `llama-bench` in a loop. Kernel malloc statistics and SMC sensors watch for leaks and drift                                                                                                                                                                                                                 | hours                       |

**Two notes on the ladder.** L4 is cheap, and not expensive: induced GPU faults
and timeouts recover in place at millisecond cost, so a fifty-case fault sweep
is not fifty reboots. But `drm_asahi.fault_control` defaults to `0xb`, the macOS
setting, which enables soft faults: shader loads of unmapped memory return zero,
and shader stores are discarded silently. Only shader loads and stores are
affected, and texture sampling still faults. A fault-injection test therefore
passes by accident unless `fault_control=0` is set. The setting applies at GPU
initialization, and it cannot change at run time, so a soft-fault L4 run is
invalid. Two debug flags make L4 usable: bit 39, `NoGpuRecovery`, wedges a fault
for inspection, and bit 63, `OopsOnGpuCrash`, turns a firmware crash into a
kernel panic, which routes it into the panic-capture path of section 11.

L5 depends on gate G5, which no iteration in this plan performs. xenocara has no
`libvulkan_asahi` build rule, no Apple switch in `lib/mesa/mk/config.mk`, and no
Apple ICD JSON file, and the vendored Mesa 25.0.7 targets `unstable_asahi_drm.h`
and refuses a mismatched UAPI version. L5 also states a tolerance, and not
bit-exact equality, because floating-point GPU kernels do not reproduce a CPU
result bit for bit. llama.cpp issue 16188, garbage output from Honeykrisp on an
M2 Pro, opened 23 September 2025 and closed 11 November 2025, is the failure
mode that this rung exists to catch.

**The structure-layout extractor, aimed at the right source.** The Python
`construct` definitions in `proxyclient/m1n1/fw/agx` are the upstream source of
truth for the firmware ABI: about 4,741 lines across 143 construct classes, with
roughly 280 version-conditional fields expressed as `Ver(...)` guards. The Rust
driver structures were generated from them. `ConstructClass.to_rust()` in
`proxyclient/m1n1/constructutils.py` emits `#[versions(AGX)]`,
`#[repr(C, packed(4))]` structures with per-field `#[ver(...)]` attributes, and
`experiments/agx_dumpstructs.py` is a 19-line driver for it.

Write `ConstructClass.to_c()` beside `to_rust()`. For the pinned G13 and V13_5
configuration it emits one packed C structure for each class, one
`_Static_assert(offsetof(...) == N, ...)` for each field, and one
`_Static_assert(sizeof(...) == N, ...)` for each structure. The version
conditionals resolve at generation time, so the C output is unconditional and
readable. This is one Python file against a machine-readable model. It needs no
Rust parser, it does not depend on a rebasing branch, and it raises no licensing
question. It runs on any machine, because `agx_dumpstructs.py` imports nothing
that touches hardware.

Two caveats apply. The exit criterion is agreement with the m1n1 Python firmware
model, and not with the Rust code, because the Rust driver states no field
offsets of its own: the only struct-layout assertion in the whole driver is on
an internal debug type. A generator fault would therefore be self-consistent,
and hardware confirmation still matters. For a driver built on m1n1 1.6.0 or
newer the init-data structures matter less, because m1n1 builds `hw-cal-a`,
`hw-cal-b`, and `globals` itself. The structures that still matter are
`cmdqueue.py`, `channels.py`, and `microsequence.py`, which is 2,375 lines and
114 classes rather than the full 4,741.

**Marshaling unit tests.** The C code that builds firmware objects tests on the
build host against traffic captures from the oracle machine. The test run needs
no Apple hardware.

**Differential testing against the oracle.** A working reference implementation
on identical hardware is the strongest correctness tool available. The same test
job runs on a FuguAGX target and on the Asahi oracle. A trace-diff tool compares
the firmware mailbox traffic of both runs. A corpus of known-good traces, pinned
to the firmware version, lives in the artifact store, and the marshaling tests
replay it. Performance comparisons use the same model file and the same
`llama-bench` arguments on both machines.

**How the AGX tracer works.** It is not MMIO tracing.
`proxyclient/m1n1/trace/agx.py` is 1,530 lines. `proxyclient/hv/trace_agx.py`
traces `/arm-io/sgx`, `/arm-io/gfx-asc`, and `/arm-io/pmp`, plus the UAT GPU
region, the shared region, and a 16 MB window of SGX MMIO, and dumps command
buffers to a directory. It installs page traps on the UAT translation-table
page, on the page tables, and on mapped GPU virtual addresses, because AGX
traffic lives in shared memory and not in registers, and it hooks two mailbox
endpoints. It takes the region bases from the Apple device tree, and not from a
guest structure, so it is guest-agnostic in principle. It registers two
hypercalls so that a guest can pause and resume tracing, and it loads the Mesa
`libagxdecode` library to decode command streams.

**What an oracle costs.** The hypervisor documentation requires a second APFS
volume with a second macOS installation, `bputil -nkcas` to downgrade the
security of that volume, `csrutil disable`, `nvram boot-args=-v`, a
`kmutil configure-boot` command against that volume, and a kernelcache extracted
with `img4tool` or built from an Apple KDK. Apple no longer serves the 13.5 and
14.8.3 installers, and the documentation points at archive.org for both. The
documented guest targets are macOS 13.5 on M1 and M2 series machines, macOS
14.8.3 on M1 to M3 series machines, and Linux.

## 14. The staged plan

The plan must not buy hardware and then find a broken assumption. It must not
build a lab in front of the experiments that can end the project. Every
iteration has a testable exit criterion and a stop rule.

| #    | Name                          | New hardware                    | Exit criterion                                                                                                              | Stop rule                                                                                              |
| ---- | ----------------------------- | ------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| P0.1 | CPU baseline                  | none                            | Published pp512 and tg128 for both builds, plus a full-turn latency figure, sent to the port maintainer                     | none. This work is mandated                                                                            |
| P0.2 | M2 Pro measurement            | rented instance                 | A measured bandwidth figure for the M2 Pro                                                                                  | A confirmed extrapolation ends the driver ladder                                                       |
| P0.3 | Named reviewer                | none                            | A written strategy decision and a named OpenBSD developer                                                                   | No named reviewer means stop                                                                           |
| P0.4 | DRM-core plumbing             | none                            | `inteldrm` and `amdgpu` still work on amd64, and the new helpers pass their tests                                           | none. This work stands alone                                                                           |
| P0.5 | Light loop                    | one M1, one cable               | `agx_boot.py` boots the firmware on the pinned version                                                                      | A failure inside the effort bound ends the plan                                                        |
| P0.6 | Extractor and reference stack | oracle machine                  | The generated C structures agree with the m1n1 firmware model, and the corpus holds one replayable job                      | An unresolvable ABI for the pinned pair means stop                                                     |
| P1.1 | Control plane                 | none                            | A stated number of unattended cycles against a virtual target                                                               | none                                                                                                   |
| P1.2 | First metal                   | controller, VDM adapter         | Twenty consecutive agent-driven deploy-and-revert cycles through `/bsd.upgrade`                                             | A `boot>` prompt that does not appear or does not accept input forces a tethered deploy and a re-scope |
| P1.3 | Measurement duty complete     | none                            | Measured build, watchdog-to-SSH, and reinstall timings in the run database                                                  | none                                                                                                   |
| P2.1 | First kernel code             | none                            | L2 passes on a lab target                                                                                                   | No workable answer to the 16 KB page question means stop                                               |
| P2.2 | Unattended recovery           | Scrutinizer or control Mac, PDU | Recovery from an induced hang, panic, dead gadget, and broken root filesystem, with zero human action, plus a one-week soak | none                                                                                                   |
| P2.3 | Scale out                     | more targets, M2 and M2 Pro     | Two agent sessions work in parallel on separate targets                                                                     | none                                                                                                   |

**Phase P0 costs under $600, and it carries four stop rules.** P0.1 executes the
four steps of INF-ARM64 and measures the reference task against the five-minute
budget. P0.2, P0.3, and P0.5 are checks K1, K2, and K3 of section 4. P0.4 is
gate G1, and an engineer must resolve the licence question of open check 12
first. P0.6 writes `ConstructClass.to_c()`, generates the C assertions for the
pinned configuration, installs the reference driver on the oracle, brings up
hypervisor tracing, and captures a trace corpus. A render experiment needs a
captured corpus first, so this iteration produces the corpus rather than only
runs scripts.

**The three approvals sit between P0 and P1.** Section 15 gives them.

**Phase P1 builds the minimum lab.** P1.1 builds the API, the lease logic, the
run database, the test runner, and the artifact store against an OpenBSD/arm64
virtual machine. Constraint 3 bounds what that proves, so every target-facing
mechanism must sit behind an adapter interface with a virtual implementation and
a metal implementation. P1.2 adds one Mac mini M1, the controller, a SuperSpeed
cable, and a VDM adapter. It has one prerequisite that no agent and no
controller can perform: a human must install the target with the Asahi
installer, then boot into 1TR and run `csrutil disable` and
`nvram boot-args=-v`. A human performs the power cycles by hand at this stage.
P1.3 runs the P0.1 measurements through the lab, and replaces the estimates of
the loop arithmetic with measurements.

**Phase P2 builds the full lab and the driver.** P2.1 executes gates G2 and G3:
the attach skeleton, the RTKit handshake, the UAT page tables, and one compute
dispatch through a render node. P2.2 adds the recovery hardware, and it must
include a check that the PMU boot error counter is cleared on the OpenBSD path.
A destroyed stage 1 sits outside the P2.2 exit criterion, because that rung
needs a human. P2.3 grows the fleet and adds the machines for gate G7.

**Loop arithmetic, as estimate.** An incremental kernel build on M-class
hardware is expected to take low minutes. A full heavy-loop cycle of build,
boot, L0 to L2, and recover is expected near four to six minutes. One target
would then support hundreds of autonomous iterations each week, and the light
loop hundreds each hour. Every figure in this paragraph is an **estimate**,
because no public measurement of an OpenBSD/arm64 kernel build on Apple Silicon
exists. P1.3 measures all of them.

## 15. The three approvals

Three separate approvals exist. They are not interchangeable. All three sit
before any tier-3 spend. They are approvals inside this body of work, and they
are not the five fixed gates of the [roadmap](../../spec/ROADMAP.md).

**Approval 1, the reviewer.** This is gate G0 of the draft plan, and check K2 of
section 4\. The exit is a written strategy decision and a named OpenBSD
developer who will review and commit the result. No named reviewer means the
plan ends at P0, and the CPU measurement duty is the whole of the work. This
gate comes first, because it is the cheapest and the most likely to fail:
OpenBSD has no kernel Rust, and no OpenBSD developer has proposed an AGX driver
in public.

**Approval 2, the spend.** [D8](../../spec/DECISIONS.md#d8) reserves four
decisions to humans: merges, release signatures, licensing lanes, and spend
above the budget. [spec/index.md](../../spec/index.md) sets a monthly budget of
EUR 1,500 for cloud spend, and it names no line for capital hardware. Every
purchase in this document therefore needs a human spend decision, including the
tier-1 controller and the tier-2 rental. This gate is separate from the D2
question.

**Approval 3, the decision.** [D2](../../spec/DECISIONS.md#d2) states that the
decision is “CPU only on the target hardware”, that it is not “OpenBSD has no
GPU path”, and that a move to GPU inference is an escalation that needs a new
decision. Phase P2 is that escalation. A human must approve a change to
[decisions](../../spec/DECISIONS.md) first, argued with the P0.1 baseline, the
P0.2 measurement, the P0.5 light-loop result, the P0.6 ABI evidence, and the
honest expected gain: prompt processing only, with token generation unchanged on
the M1.

Order matters. Approval 1 comes before approval 2, because a failed reviewer
search makes the spend pointless. Approval 2 comes before approval 3, because a
refused spend makes the decision moot.

## 16. Cost, and the alternatives

### The bill of materials

| Item                                   | Qty | Estimated cost | Phase                              | Confidence                                                                               |
| -------------------------------------- | --- | -------------- | ---------------------------------- | ---------------------------------------------------------------------------------------- |
| Mac mini M1, 16 GB, used               | 3   | about $1,275   | P1.2 and P2                        | observed price                                                                           |
| Mac mini M2 Pro                        | 1   | about $1,100   | P0.2, if bought rather than rented | observed price                                                                           |
| Rescue or control Apple Silicon Mac    | 1   | about $400     | P2.2                               | estimate                                                                                 |
| Lab controller                         | 1   | about $200     | P1.1                               | observed price                                                                           |
| Metered smart PDU                      | 1   | about $150     | P2.2                               | estimate                                                                                 |
| Central Scrutinizer, self-fabricated   | 3   | about $110     | P2.2                               | estimate. No prebuilt unit was found, so a PCB run and assembly sit on the critical path |
| Mac mini M2, for gate G7               | 1   | about $400     | P2.3                               | estimate                                                                                 |
| USB HDMI capture dongles               | 3   | about $45      | P2                                 | observed price                                                                           |
| Cables, switched USB link, VLAN switch | —   | about $200     | P1.2 and P2                        | estimate                                                                                 |
| Spares and consumables                 | —   | unpriced       | all                                | UNVERIFIED                                                                               |

The total is about **$3,880**, as an estimate and not as a quotation. It is a
floor: it excludes spares, lab power, artifact storage, and the flash wear of
repeated reimaging. Phase P0 spends at most one rental and one cable, if the
project already owns a Mac mini M1. Phase P1 spends the controller, the VDM
adapter, and one target. Phase P2 spends the rest.

### The cost that the bill of materials does not show

The draft plan prices the driver at about 15 to 30 person-months, and then
maintenance without end. That is 2,400 to 4,800 engineer-hours. Firmware-ABI
kernel code cannot merge without review, so a substantial part of those hours
stays senior human review, and approval 1 exists because the project does not
have that reviewer today. Continuous agent operation across thousands of build,
boot, test, and recover cycles is itself a recurring cost against the monthly
budget that D8 reserves to humans. The hardware is a small fraction of this
project.

One thesis under this plan needs a plain statement: agent automation changes the
person-month arithmetic. That is a claim, and not a finding. The evidence that
tests it is the measured cycle count and human-intervention count from the P1.3
run database. No such evidence exists yet.

### Who maintains this

Three questions need answers before phase P2 starts. Who owns the lab after
P2.2. Who owns the driver after gate G9. What happens to both when that person
stops.

The base rate is available. Asahi Linux carried this work with three full-time
principals, and lost all three inside seven months: Hector Martin resigned as
project lead in February 2025, Asahi Lina paused Apple GPU driver work in March
2025, and Alyssa Rosenzweig joined Intel in August 2025. The AGX Python model
has not moved substantively since November 2024. The project continued under
collective leadership and began upstreaming work in the Linux 6.19 cycle, so the
base rate is a sharp slowdown, and not a stop.

One decommission trigger applies: if no commit lands on FuguAGX for ninety days,
the lab powers down and the machines return to other work.

### Alternatives considered

**Hosted Apple Silicon.** Scaleway sells dedicated Mac minis by the hour with a
24-hour minimum, and the project installs `scw` already. It cannot replace the
lab, because the instances run macOS only: no OpenBSD, no DFU, no USB-C debug
port, and no m1n1 proxy. It settles the memory-bandwidth ceiling of the M2 and
the M2 Pro, which is check K1, and nothing else.

**Contribute upstream instead.** Offer the lab control plane, the IGT port, or
the `to_c()` extractor to Asahi Linux, rather than build a parallel effort. The
cost is engineering time, and no hardware.

**amd64 with an AMD card.** This delivers working GPU inference today, with no
new kernel code, through the ggml Vulkan back end that OpenBSD supports on
amd64. It is wrong for the target hardware of the product, and it is right for
training, evaluation, and CI, which the project runs on amd64 guests already.

**Wait for mainline.** This costs nothing, and its probability rises rather than
falls. The UAPI header landed in mainline on 8 April 2025 and shipped in Linux
6.16, and Asahi began upstreaming the driver in the 6.19 cycle. The route pays
off if mainline gains `drm/asahi` and OpenBSD gains kernel Rust, or if OpenBSD
takes a mainline driver in a DRM sync, as it took `apldcp(4)` and `apldrm(4)`
from the Asahi tree in January 2024.

## 17. Open checks

Each item below is a fact that this document could not establish. Each names the
method that resolves it, and the iteration that owns it.

1. The current Scaleway hourly rate for an Apple Silicon M2 Pro instance. Two
   figures were found: about EUR 0.21 and about EUR 0.24 per hour. Resolve by a
   read of the current price page, or by a `scw` query before booking. Owner:
   P0.2.
2. Whether the OpenBSD `boot>` prompt appears on the Apple debug UART on a
   headless Mac mini M1 with a stock Asahi U-Boot, and whether it accepts input.
   The code paths indicate yes, and the default `stdin` and `stdout` values of
   U-Boot on this board could not be established from source. The Apple
   defconfig stores no persistent environment. Resolve by a record of both
   variables on the first metal target. Owner: P1.2.
3. Whether a Mac mini M1 that runs OpenBSD restarts when AC power returns. The
   mechanism is an SMC power-state setting, and not an unconditional power-on:
   Linux exposes it as `ac_power_mode` with values `off` and `restore`, and
   macOS sets it with `pmset -a autorestart 1`. It restores the previous state,
   so it powers the machine on only if the machine was on when AC power was
   lost, which does cover the T7 case. `aplsmc(4)` provides no way to set it, so
   a human must configure it once from macOS or Asahi Linux, and that step
   belongs in the target preparation checklist. `AsahiLinux/docs` issue 156 is
   open on this question. Resolve by a set of the value, a boot into OpenBSD, an
   outlet pull, and a restore. This is a blocking pre-purchase check for the
   PDU: a failure makes T7 a no-op, and the fallback is a relay on the power
   button, which changes the bill of materials. Owner: P1.2.
4. OpenBSD/arm64 `GENERIC.MP` kernel build time on an M1 and on an M2 Pro, full
   and incremental, and whether `make -j` is reliable for the arm64 kernel. No
   public measurement exists. Resolve by measurement. Owner: P1.3.
5. The duration of an unattended arm64 reinstall over gigabit Ethernet from a
   local mirror. The only known bound is the 30-minute self-reboot watchdog of
   the installer. Resolve by measurement. Owner: P1.3.
6. Whether the device-tree properties that `dt_set_gpu()` writes survive the
   handoff to OpenBSD: the `hw-cal-a`, `hw-cal-b`, and `globals` reserved-memory
   nodes, the three UAT regions, and `apple,firmware-abi`. m1n1 hands the FDT to
   U-Boot, and U-Boot passes an FDT to efiboot over EFI, and the arrival was not
   confirmed. Resolve with `ofwdump` on one machine that runs an updated m1n1.
   This decides whether FuguAGX inherits the power and DVFS calibration, or
   repeats it. Owner: P2.1.
7. Free space in the Asahi-created EFI system partition on a Mac mini M1 after a
   UEFI-environment-only install. An arm64 bsd.rd is 18,732,300 bytes, a
   candidate kernel is a similar size, and the partition must not be recreated.
   Resolve by measurement on a real target. Owner: P1.2.
8. The throughput of the m1n1 proxy link, and the time to push a full OpenBSD
   kernel over it. If tethered boot becomes a primary deploy path, this figure
   dominates the cost of each iteration. Resolve by measurement. Owner: P1.2.
9. Whether OpenBSD can write Apple NVRAM. The proxy backdoor needs
   `boot-args=-v`, and Asahi notes that an installed OS can alter that property.
   A negative answer means that a visit to 1TR is necessary to re-arm the
   backdoor, which breaks unattended operation. Resolve by an attempt on one
   target. Owner: P1.2.
10. Whether the m1n1 hypervisor can host an OpenBSD guest. Nobody has done it:
    the documented guests are macOS and Linux, and no record shows any BSD as a
    guest. The obstacle is the guest entry interface, and not the tracer.
    `run_guest.py` loads a guest as a Mach-O or a raw image, hands it an Apple
    `BootArgs` structure and a modified ADT, and enters it at EL1h, and the
    Linux recipe works because m1n1 itself becomes the guest with the kernel
    appended. The plausible OpenBSD route mirrors it: m1n1 as the guest, with
    U-Boot appended. Resolve by an attempt at that substitution. A positive
    answer gives MMIO tracing of the FuguAGX driver itself. Owner: P2.1.
11. The 2026 build cost of a Central Scrutinizer, and whether a prebuilt unit
    exists. No prebuilt unit was found. Resolve by a price for a PCB run and
    assembly. This matters less under design B, which removes the board. Owner:
    P2.2.
12. Whether the `GPL-2.0` licence of Linux `drm_gem_shmem_helper.c`, which
    carries no MIT arm, blocks a copy into OpenBSD base. The OpenBSD DRM tree
    already carries `drm_gpuvm.c` and `drm_exec.c` under dual licences. Resolve
    by a question to the reviewer found at approval 1. Owner: P0.3 and P0.4.

Three further checks belong to the driver, and not to the lab.

13. How a 4 KB-page OpenBSD kernel backs a 16 KB UAT granule. Resolve on paper
    before any kernel code starts.
14. Whether the OpenBSD `rtkit.c` version range covers what the AGX firmware
    announces in its handshake on macOS 13.5 firmware. Resolve by a read of the
    handshake on a target.
15. How many of the version-conditional sites of the reference driver differ
    between V12_3 and V13_5 on G13. This is the true cost of support for two
    firmware versions in C. Resolve by an expansion of the macro for both
    variants, and a comparison.

## 18. Decision pressure

This document changes no specification text. It touches five decisions.

**D2 — one escalation, and one duty that runs the other way.**
[D2](../../spec/DECISIONS.md#d2) states “CPU only on the target hardware”, and
states that a move to GPU inference needs a new decision. Phases P0 and P1 run
no GPU inference on the target hardware, so they do not touch D2. Phase P2 does,
and approval 3 is where a human approves or refuses it. D2 also supplies an
argument for the lab: the harness smoke suite must pass on the target arm64
hardware before a release, whatever happens to FuguAGX.

**D7 — a naming collision, and not a conflict.**
[D7](../../spec/DECISIONS.md#d7) fixes Perl 5 with base modules plus the Fugu
module allow-list for the harness body, states that Python must not ship to the
OpenBSD target, and states that the harness must not install from CPAN on the
target. The lab control plane runs on the controller, and never on an OpenBSD
target, so D7 does not constrain its language. The collision is in the word
alone, and the naming rule at the head of this document removes it.

**D8 — two obligations.** D8 reserves spend above the budget to humans, which is
why approval 2 exists. D8 also states that each outcome has a machine-checkable
definition of done, which is why every rung of section 13 carries a checkable
pass condition, and why the idle period of L1 and the tolerance of L5 must be
numbers.

**D9 — name the kind of every control.** [D9](../../spec/DECISIONS.md#d9)
requires the specification to state which controls block and which notify only.
The same discipline applies here. The lab API refuses an operation on a machine
outside the lab VLAN, and that blocks. The firmware-ABI assertion at L0 blocks.
The watchdog blocks. Power telemetry and SMC sensors notify. The mitigation for
the PMU boot error counter gates, because it runs as lab code before each soak
cycle.

**D10 — the plan method, and one more naming collision.**
[D10](../../spec/DECISIONS.md#d10) states that work proceeds in vertical slices,
that a measurement ends each slice, that a slice must not end at an unmeasured
component, and that risk retired per euro orders the slices. The staged plan of
section 14 obeys all four. Every iteration ends in a measurement, and phase P0
comes first because it retires the most risk for the least money. An engineer
who starts this work must write each iteration as a plan in `plans/`, and must
name its kind. The collision is in the word “gate”.
[roadmap](../../spec/ROADMAP.md) fixes five gates in a fixed order, and a human
decides at each one. The three approvals of section 15 are not those gates. They
are approvals inside one body of work, and a reader must not confuse them with
the pin, retrieval, CPT, release, and variant gates of the roadmap.

**One security note.** The controller holds SSH keys to every target, drives DFU
restores, power-cycles outlets, and exposes an API to an autonomous agent. The
one-time 1TR preparation downgrades the security posture of each target
permanently. The threat model is plain: the targets hold nothing of value and
live on an isolated VLAN, the controller holds the artifact store and is backed
up, and the two non-OpenBSD machines hold the reference implementation and the
restore assets and need the same isolation. Gate G8 of the draft plan covers the
security surface of the driver itself — the pledge `drm` promise, the
device-node permissions, W^X against the Mesa shader compiler, and the unveil
path list — and no iteration in this plan performs it.

## 19. Sources

All URLs below were read on 21 August 2026 unless another date is given. Dates
are the source dates, and not the fetch dates.

### OpenBSD kernel and boot chain

- `sys/arch/arm64/arm64/machdep.c`, showing `cpu_dump_mempagecnt()` returning 0
  and the `cpu_dump()` memory loop under `#if 0` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/arm64/machdep.c
- `sys/arch/arm64/conf/GENERIC`, with `apldog*` at line 170 and `exuart*` at
  line 199 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/conf/GENERIC
- `sys/arch/arm64/conf/RAMDISK`, with `exuart` at line 142 and `bge` at line 323
  —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/conf/RAMDISK
- `sys/conf/GENERIC`, with `DDB_SAFE_CONSOLE` commented out at line 8, `MFS` at
  line 35, and `TMPFS` commented out at line 42 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/conf/GENERIC
- `sys/arch/arm64/include/param.h`, `PAGE_SHIFT 12` at line 50 —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/include/param.h
- `sys/arch/arm64/dev/apldog.c`, with the period ceiling, the `SMALL_KERNEL`
  guard, and `cpuresetfn` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/dev/apldog.c
- `sys/arch/arm64/dev/rtkit.c`, the Apple coprocessor mailbox protocol in C —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/dev/rtkit.c
- `sys/arch/arm64/arm64/pmap.c`, allocating ASIDs in pairs from a global bitmap
  —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/arm64/pmap.c
- `sys/arch/arm64/arm64/cpufunc_asm.S`, providing inner-shareable TLB operations
  only —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/arm64/cpufunc_asm.S
- `sys/kern/subr_prf.c`, with `db_panic`, `db_console`, and `panic()` calling
  `db_stack_dump()` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/kern/subr_prf.c
- `sys/stand/boot/cmd.c`, `upgrade()` requiring the owner execute bit on
  `/bsd.upgrade` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/stand/boot/cmd.c
- `sys/stand/boot/boot.c`, printing “upgrade detected” and clearing the execute
  bits —
  https://raw.githubusercontent.com/openbsd/src/master/sys/stand/boot/boot.c
- `sys/arch/arm64/stand/efiboot/efiboot.c`, with the `esp` device and
  `cnspeed()` —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/stand/efiboot/efiboot.c
- `sys/dev/fdt/exuart.c`, matching `apple,s5l-uart` and discarding a BREAK
  before the tty exists —
  https://raw.githubusercontent.com/openbsd/src/master/sys/dev/fdt/exuart.c
- `sys/dev/pci/if_bge.c`, reading `local-mac-address` from the device tree —
  https://raw.githubusercontent.com/openbsd/src/master/sys/dev/pci/if_bge.c

### OpenBSD manual pages, installer, and ports

- `watchdog(4)`, stating that a watchdog must not be combined with `ddb(4)` —
  https://man.openbsd.org/watchdog.4
- `watchdogd(8)` — https://man.openbsd.org/watchdogd.8
- `ddb(4)`, whose command list contains no `panic` command —
  https://man.openbsd.org/ddb.4
- `autoinstall(8)`, stating the three non-interactive triggers —
  https://man.openbsd.org/autoinstall.8
- `rdsetroot(8)` — https://man.openbsd.org/rdsetroot.8
- `aplsmc(4)` — https://man.openbsd.org/aplsmc.4
- `apldog(4)` — https://man.openbsd.org/apldog.4
- `mount_mfs(8)` — https://man.openbsd.org/mount_mfs.8
- `distrib/arm64/ramdisk/install.md`, with `KEEP_EFI_SYS=true` and the vendor
  firmware extraction —
  https://raw.githubusercontent.com/openbsd/src/master/distrib/arm64/ramdisk/install.md
- `distrib/miniroot/install.sub`, with the 30-minute stall watchdog and
  `check_unattendedupgrade()` —
  https://raw.githubusercontent.com/openbsd/src/master/distrib/miniroot/install.sub
- `distrib/miniroot/dot.profile`, with the five-second non-interactive timeout —
  https://raw.githubusercontent.com/openbsd/src/master/distrib/miniroot/dot.profile
- OpenBSD 7.9 release notes, 19 May 2026 — https://www.openbsd.org/79.html
- OpenBSD FAQ 5, on kernel builds and cross-compilation —
  https://www.openbsd.org/faq/faq5.html
- OpenBSD copyright policy — https://www.openbsd.org/policy.html
- `sysutils/m1n1` Makefile, setting `GH_TAGNAME= v1.5.2` and building with
  `RELEASE=1` and no `CHAINLOADING=1` —
  https://raw.githubusercontent.com/openbsd/ports/master/sysutils/m1n1/Makefile
- `sysutils/m1n1` Makefile revision history, revision 1.17 committed 5 January
  2026 — https://cvsweb.openbsd.org/log/ports/sysutils/m1n1/Makefile,v
- Mark Kettenis, “Apple M1 teaser”, openbsd-arm, 20 February 2021, with the
  first M1 dmesg showing `bge0` and `brgphy0` —
  https://marc.info/?l=openbsd-arm&m=161386122115249&w=2

### m1n1 and Asahi tooling

- m1n1 `config.h`, with `EARLY_PROXY_TIMEOUT` commented out at line 11 —
  https://raw.githubusercontent.com/AsahiLinux/m1n1/main/config.h
- m1n1 `src/main.c`, gating the early proxy on verbose boot and the boot policy
  — https://raw.githubusercontent.com/AsahiLinux/m1n1/main/src/main.c
- m1n1 `src/usb_dwc3.c`, the CDC-ACM gadget at VID 0x1209 and PID 0x316d —
  https://raw.githubusercontent.com/AsahiLinux/m1n1/main/src/usb_dwc3.c
- m1n1 `src/kboot_gpu.c`, `dt_set_gpu()` publishing the GPU device-tree
  properties —
  https://raw.githubusercontent.com/AsahiLinux/m1n1/main/src/kboot_gpu.c
- m1n1 `src/firmware.c`, the firmware version table and the GPU compatibility
  remap — https://raw.githubusercontent.com/AsahiLinux/m1n1/main/src/firmware.c
- m1n1 commit `f9dd8b3`, moving GPU blob generation into m1n1, 11 May 2025 —
  https://github.com/AsahiLinux/m1n1/commit/f9dd8b3761d0dfe64a04e7c9bbb4de570acd3892
- m1n1 `proxyclient/m1n1/proxy.py`, the 153-opcode proxy protocol —
  https://github.com/AsahiLinux/m1n1/blob/main/proxyclient/m1n1/proxy.py
- m1n1 `proxyclient/m1n1/constructutils.py`, with `Ver.MATRIX` and `to_rust()` —
  https://raw.githubusercontent.com/AsahiLinux/m1n1/main/proxyclient/m1n1/constructutils.py
- m1n1 `proxyclient/m1n1/hw/pmu.py`, resetting the boot error counter —
  https://github.com/AsahiLinux/m1n1/blob/main/proxyclient/m1n1/hw/pmu.py
- m1n1 `proxyclient/experiments`, the ten AGX scripts —
  https://github.com/AsahiLinux/m1n1/tree/main/proxyclient/experiments
- m1n1 `proxyclient/tools/freebsd.py`, contributed 3 April 2022, updated 25
  September 2024 —
  https://github.com/AsahiLinux/m1n1/blob/main/proxyclient/tools/freebsd.py
- m1n1 `proxyclient/tools/linux.py`, with `-u` and `-E` —
  https://github.com/AsahiLinux/m1n1/blob/main/proxyclient/tools/linux.py
- m1n1 `proxyclient/m1n1/trace/agx.py`, the 1,530-line AGX tracer —
  https://raw.githubusercontent.com/AsahiLinux/m1n1/main/proxyclient/m1n1/trace/agx.py
- m1n1 user guide, documenting the proxy backdoor and its preparation —
  https://raw.githubusercontent.com/AsahiLinux/docs/main/docs/sw/m1n1-user-guide.md
- m1n1 hypervisor documentation, with the supported guest targets —
  https://raw.githubusercontent.com/AsahiLinux/docs/main/docs/sw/m1n1-hypervisor.md
- Asahi serial-debug documentation, with the DFU-port location, 1.2 V logic, and
  the VDM requirement — https://asahilinux.org/docs/hw/soc/serial-debug/
- Asahi AGX hardware notes, on the ASC coprocessor and the write-protected
  firmware —
  https://raw.githubusercontent.com/AsahiLinux/docs/main/docs/hw/soc/agx.md
- Asahi ASC documentation, with `CPU_CTRL` at 0x44 and `CPU_STATUS` at 0x48 —
  https://raw.githubusercontent.com/AsahiLinux/docs/main/docs/hw/soc/asc.md
- Asahi installer, pinning the Mac mini M1 stub to macOS 13.5 —
  https://raw.githubusercontent.com/AsahiLinux/asahi-installer/main/src/main.py
- `macvdmtool` — https://github.com/AsahiLinux/macvdmtool
- `tuxvdmtool`, driving the host CD321x over i2c —
  https://github.com/AsahiLinux/tuxvdmtool
- `kisd`, tunnelling the SoC UART over DebugUSB —
  https://github.com/AsahiLinux/kisd
- Central Scrutinizer, a serial adapter for M1, M2, and M3 machines, by Marc
  Zyngier —
  https://hackaday.io/project/192826-central-scrutinizer-a-serial-adapter-for-m1m2m3
- `AsahiLinux/docs` issue 156, on automatic power-on after power loss —
  https://github.com/AsahiLinux/docs/issues/156

### The reference driver, and Linux

- Reference driver tree, 45 Rust files —
  https://github.com/AsahiLinux/linux/tree/asahi-wip/drivers/gpu/drm/asahi
- `pgtable.rs`, `UAT_PGBIT = 14` and `UAT_LEVELS = 3` —
  https://raw.githubusercontent.com/AsahiLinux/linux/asahi-wip/drivers/gpu/drm/asahi/pgtable.rs
- `Kconfig`, `depends on PAGE_SIZE_16KB` —
  https://raw.githubusercontent.com/AsahiLinux/linux/asahi-wip/drivers/gpu/drm/asahi/Kconfig
- `gpu.rs`, with `recover()` and the RTKit handshake —
  https://raw.githubusercontent.com/AsahiLinux/linux/asahi-wip/drivers/gpu/drm/asahi/gpu.rs
- `mem.rs`, emitting outer-shareable ARMv8.4 TLB instructions —
  https://raw.githubusercontent.com/AsahiLinux/linux/asahi-wip/drivers/gpu/drm/asahi/mem.rs
- `driver.rs`, accepting five GPU and firmware ABI pairs —
  https://raw.githubusercontent.com/AsahiLinux/linux/asahi-wip/drivers/gpu/drm/asahi/driver.rs
- `debug.rs`, with `NoGpuRecovery` and `OopsOnGpuCrash` —
  https://raw.githubusercontent.com/AsahiLinux/linux/asahi-wip/drivers/gpu/drm/asahi/debug.rs
- `crashdump.rs`, writing an ELF64 core with `AGX` and `RTKIT` notes —
  https://raw.githubusercontent.com/AsahiLinux/linux/asahi-wip/drivers/gpu/drm/asahi/crashdump.rs
- `rust/macros/versions.rs`, the procedural macro that emits five copies —
  https://raw.githubusercontent.com/AsahiLinux/linux/asahi-wip/rust/macros/versions.rs
- `include/uapi/drm/asahi_drm.h`, in mainline since Linux 6.16, merged 8 April
  2025 —
  https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/drm/asahi_drm.h
- Device-tree binding for the Apple AGX, which carries no `iommus` property —
  https://raw.githubusercontent.com/torvalds/linux/master/Documentation/devicetree/bindings/gpu/apple,agx.yaml
- Linux `drm_gem_shmem_helper.c`, `SPDX-License-Identifier: GPL-2.0` —
  https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/drm_gem_shmem_helper.c
- U-Boot `arch/arm/mach-apple/board.c`, rewriting `stdout-path` only when a
  keyboard exists —
  https://raw.githubusercontent.com/u-boot/u-boot/master/arch/arm/mach-apple/board.c
- U-Boot `configs/apple_m1_defconfig`, `CONFIG_NO_NET=y` —
  https://raw.githubusercontent.com/AsahiLinux/u-boot/asahi/configs/apple_m1_defconfig
- Apple M1 device tree, `/chosen/stdout-path = "serial0"` and the 24 MHz
  `clkref` —
  https://raw.githubusercontent.com/AsahiLinux/linux/asahi-wip/arch/arm64/boot/dts/apple/t8103-jxxx.dtsi

### Project reports, performance, and internal documents

- Asahi Linux, progress report for Linux 6.19, 15 February 2026 —
  https://asahilinux.org/2026/02/progress-report-6-19/
- Asahi Linux, progress report for Linux 7.1, 30 June 2026 —
  https://asahilinux.org/2026/06/progress-report-7-1/
- The Register, on the pause of Apple GPU driver work, 20 March 2025 —
  https://www.theregister.com/software/2025/03/20/asahi-linux-loses-another-prominent-dev-as-gpu-guru-quits/1212230
- Hübner, Hu, Peng, Markidis, “Apple vs. Oranges”, STREAM measurements for the
  M-series, arXiv 2502.05317v1, 7 February 2025 —
  https://arxiv.org/html/2502.05317v1
- llama.cpp issue 16188, garbage output on Honeykrisp, 23 September 2025, closed
  11 November 2025 — https://github.com/ggml-org/llama.cpp/issues/16188
- FuguTTX research report, OpenBSD and the Apple GPU, 1 August 2026 —
  [openbsd-apple-silicon-gpu.md](openbsd-apple-silicon-gpu.md)
- FuguTTX draft plan, Apple GPU support for OpenBSD on the Mac mini —
  [apple-gpu-openbsd-draft-plan.md](apple-gpu-openbsd-draft-plan.md)
- FuguTTX specification, inference —
  [spec/inference.md](../../spec/inference.md)
- FuguTTX specification, decisions —
  [spec/DECISIONS.md](../../spec/DECISIONS.md)
- FuguTTX specification, roadmap — [spec/ROADMAP.md](../../spec/ROADMAP.md)
