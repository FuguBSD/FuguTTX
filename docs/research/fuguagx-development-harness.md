# FuguAGX: a development harness for an Apple GPU driver on OpenBSD

**Date: 21 August 2026. Status: research note and brainstorm.
This document changes no code.**

FuguAGX is a working name for a driver that does not exist: a C implementation of an
Apple AGX GPU driver for OpenBSD. This document does not design the driver.
It designs the development and test harness around the driver, so that a coding agent
can drive as much of the build, deploy, test, and recovery loop as possible.

Two companion documents exist.
[OpenBSD and the Apple GPU](openbsd-apple-silicon-gpu.md) gives the evidence that no
such driver exists and that no gain is available for token generation on an M1.
[Draft plan: Apple GPU support for OpenBSD on the Mac mini](apple-gpu-openbsd-draft-plan.md)
sketches the driver work in gates G0 to G9 and argues why that work should not start.
This document supplies the piece both companions lack: the physical lab, the automation,
and the staged de-risk path.

This document is a draft, and it is not part of the specification.
Decision [D2](../../spec/decisions.md#d2) keeps inference on the CPU. The research
report instructs that GPU driver work must not start before the `devel/libggml` build
fix and the `llama-bench` measurements.
A start of FuguAGX therefore needs a change to [decisions](../../spec/decisions.md) with
human approval first.
The harness iterations H0 to H3 below need no such approval, because they serve the CPU
measurement duty that the specification already mandates.

## 1. Three constraints shape the harness

Three facts control every design choice below.

1. **OpenBSD has no loadable kernel modules.** Every driver change means a full kernel
   relink and a reboot of the target.
   The edit-test loop is minutes, not seconds.
   The harness must therefore make reboots free, automatic, and safe.
2. **The AGX firmware is not restartable.** The ASC coprocessor firmware boots once per
   power cycle. When the driver wedges the firmware, no kernel-level recovery exists.
   The machine must reboot.
   Crash-and-reboot is the normal iteration, not the exception.
   The harness must treat a hung target as routine.
3. **No emulator exists for the AGX.** No QEMU model of the GPU exists.
   All driver tests run on physical Apple hardware.
   The harness control plane itself carries no such limit: an OpenBSD/arm64 virtual
   machine can stand in for a target during harness development.

One insight follows from constraints 1 and 2. The harness must offer two loops, not one:

- **The heavy loop.** Edit C, build a kernel, boot the target, run tests.
  Cost: minutes per iteration.
- **The light loop.** Poke the live hardware from Python over the m1n1 proxy, with no
  OpenBSD kernel involved at all.
  Cost: seconds per iteration.
  Asahi Linux developed its driver on this loop first, and the m1n1 tree still carries
  the proof: `proxyclient/experiments/` contains `agx_boot.py`, `agx_1tri.py`,
  `agx_renderframe.py`, and `agx_dumpstructs.py`, which boot the GPU firmware and render
  from Python.

The agent must exhaust the light loop before it pays for the heavy loop.

## 2. Foundations that already exist

The harness does not start from zero.
These pieces exist today, and each one removes work:

- **The Asahi Rust driver is the executable specification.** The 24 Rust files in
  `AsahiLinux/linux` (`asahi-wip`) carry the firmware ABI structures, the UAT page-table
  logic, and the queue management.
  The license is `GPL-2.0-only OR MIT`, and the MIT arm is usable.
  The C rewrite is a translation problem with a reference answer.
- **m1n1 proxy mode.** After m1n1 stage 1 starts, the target enumerates as a USB CDC-ACM
  gadget on its debug USB-C port.
  The host-side Python framework (`proxyclient`) can read and write memory, poke MMIO,
  upload and chainload payloads, and attach a console, over a plain USB-C cable.
- **m1n1 hypervisor mode.** m1n1 can run a guest at EL1 and trace every MMIO access the
  guest makes. Asahi used this to reverse-engineer the macOS GPU driver.
  FuguAGX would use it on the oracle machine, to capture reference firmware traffic.
- **An IGT test series for asahi exists.** Janne Grunau posted it to dri-devel in
  January 2026. It is a ready-made conformance suite to port.
- **OpenBSD already holds much of the C support code.** `rtkit.c` implements the Apple
  coprocessor mailbox protocol.
  The DART IOMMU driver, `drm_gpuvm.c`, `drm_exec.c`, and the DRM GPU scheduler are
  present. Missing pieces: `drm_gem_shmem_helper.c` and the syncobj fd paths (see the
  research report, section 5).
- **`apldog(4)`.** OpenBSD drives the watchdog timer of the Apple SoCs.
  An armed watchdog resets a hung kernel with no external help.
- **`ddb(4)` over serial.** The kernel debugger takes commands on the serial console
  after a panic, so a script can capture a backtrace before it reboots.
  `savecore(8)` preserves crash dumps across the reboot.
- **`autoinstall(8)`.** OpenBSD installs unattended from an answer file over HTTP. This
  is the clean-reinstall mechanism, and it needs no console interaction.
- **The Central Scrutinizer.** An open-hardware board by Marc Zyngier (a FUSB302, level
  shifters, and a Raspberry Pi Pico).
  It speaks USB-PD vendor-defined messages to the debug port of an M1/M2/M3 machine.
  It exposes the pre-boot UART, it can hard-reset the machine through the Mac’s own PD
  controller, and it passes USB 2.0 through for tethered m1n1 boot.
  `macvdmtool` provides the same VDM control from a macOS host.
- **The firmware contract is pinnable.** The Asahi driver ABI is versioned against the
  macOS firmware release.
  The lab must pin every machine to one firmware version, so that traces, structures,
  and tests stay comparable.

## 3. The lab

### Machine roles

| Role | Machine | Purpose |
| --- | --- | --- |
| Target fleet | 2 or 3 used Mac mini M1, 16 GB | The machines under test. Consumables in the loop. One stays known-good to separate driver faults from flaky units. All pinned to one firmware version. |
| Oracle | 1 Mac mini M1 on Asahi Linux | Runs the real Rust driver. Supplies reference results, reference performance, and firmware traffic traces through the m1n1 hypervisor. |
| Build host | Mac mini M2 Pro on OpenBSD | Native kernel builds in minutes. Becomes the G7 target later. |
| Lab controller | Small always-on Linux box (N100 class) | Runs the m1n1 proxy clients, the serial servers, the power control, the artifact store, and the harness API. The only machine the agent talks to. |
| Rescue host | One macOS machine, via a switched USB link | DFU-restores a target whose boot chain is destroyed. The unbrick tier. |

### Links per target

| Link | Hardware | Function |
| --- | --- | --- |
| Proxy and console | Plain USB-C to the controller | m1n1 gadget serial and proxy. Covers about 90 percent of all interactions. |
| Early debug and reset | Central Scrutinizer | Pre-m1n1 UART (iBoot logs, early hangs), VDM hard reset, USB pass-through for tethered boot. |
| Power | One outlet on a metered smart PDU | Hard power cycle at the wall. Power telemetry doubles as observability: the agent can see the GPU ramp up during a job, and a power flatline is a cheap hang detector. |
| Display | USB HDMI capture dongle on the controller | Pixel-exact frames of the console and of early boot, before networking exists. Render correctness does not come from the display: tests read back render targets and compare checksums. The capture answers “what does the console show” when serial is dead. |

The lab network is an isolated VLAN. The targets hold nothing of value.
The controller holds the artifact store and is backed up.

## 4. Kernel deployment and boot control

The deployment design keeps the known-good path untouched at all times.

- **A/B kernel slots.** `/bsd` on the target disk is always the known-good kernel.
  A candidate kernel deploys as `/bsd.test`. The OpenBSD bootloader takes input on the
  console, so the controller selects the kernel at each boot over serial.
  The bootloader timeout default is the known-good kernel: a silent boot is always a
  safe boot.
- **Deploy over SSH when healthy.** A healthy target receives the candidate kernel with
  `scp`, and reboots.
- **Tethered boot as the recovery deploy.** When the disk boot chain is broken, the
  controller boots the target through the Scrutinizer USB pass-through and the m1n1
  proxy, with no working disk required.
- **Reimage tiers.** Tests write to tmpfs, so the root filesystem stays clean.
  When it does not stay clean, `autoinstall(8)` reinstalls the target from the
  controller in about ten minutes, unattended.
  DFU restore from the rescue host is the last tier.

## 5. The recovery ladder

Every failure mode has an automated response.
Each tier arms the next tier on timeout.
A human appears nowhere in the ladder.

| Tier | Trigger | Action |
| --- | --- | --- |
| 0 | Test run complete | Graceful `reboot(8)` over SSH. |
| 1 | Kernel hang | `apldog(4)` fires. The test runner arms the watchdog at boot, and only a completed check-in pats it. A hung kernel resets itself. |
| 2 | Kernel panic | The serial line shows the `ddb>` prompt. The controller scripts `trace`, `ps`, `show panic`, and `show registers`, captures the output, then reboots. `savecore(8)` preserves the dump to `/var/crash`. |
| 3 | Wedged SoC, dead USB gadget | The Scrutinizer sends a VDM hard reset through the PD controller. |
| 4 | VDM reset fails | The PDU power-cycles the outlet. The Mac mini starts when AC power returns. |
| 5 | Boot chain destroyed | The rescue host DFU-restores the target over the switched USB link, then the controller reinstalls with `autoinstall(8)`. |

## 6. Observability

The agent cannot look at the machine.
The harness must convert every physical signal into a queryable artifact.

- **Serial capture.** Every byte of every boot, stored per run.
- **Scripted `ddb`.** Post-panic backtraces without human hands (tier 2 above).
- **Crash dumps.** `savecore(8)` output, collected after reboot.
- **Proxy memory dumps.** After a GPU-side wedge, the m1n1 proxy dumps the firmware log
  ring buffers and the shared-memory regions.
  This is the GPU’s side of the story, and the kernel cannot tell it.
- **SMC sensors.** `aplsmc(4)` exposes temperature and power sensors, read over SSH
  while the target is alive.
- **Power telemetry.** The metered PDU reports draw per outlet.
  A flatline during a GPU job means a hang.
- **HDMI frames.** On demand, when serial is silent.
- **The run database.** Every boot gets a run ID. The row stores the kernel hash, the
  source diff, the console log, the test outcomes, and links to all artifacts.
  The agent bisects by querying its own history instead of re-running work.

## 7. The test ladder

Tests run in levels, cheap to expensive.
Each level gates the next.
The agent reports the rung on which a kernel died.

| Level | Content | Pass condition |
| --- | --- | --- |
| L0 | Boot | The target checks in over SSH within a deadline. |
| L1 | Attach | The driver attaches, the RTKit handshake completes, the firmware version is logged, and the machine stays stable for 60 seconds idle. |
| L2 | One dispatch | One trivial compute job writes a constant into a buffer, and a readback verifies it. This is gate G3 of the draft plan. |
| L3 | Conformance | The ported IGT asahi tests and the DRM selftests pass. Render targets verify by checksum. |
| L4 | Faults | Induced firmware faults recover per gate G4. Expensive: every firmware crash costs a reboot. |
| L5 | End to end | `vulkaninfo` enumerates the device through a Honeykrisp ICD. `llama-bench` runs. Output tokens match the CPU build exactly. Performance lands inside the envelope of the oracle machine. |
| Soak | Nightly | Hours of `llama-bench` in a loop. Kernel malloc statistics and SMC sensors watch for leaks and drift. |

Two test rigs need no Apple hardware at all:

- **The structure-layout extractor.** A tool parses the firmware ABI structures in the
  Asahi Rust source and emits C `static_assert` lines with field offsets.
  The C structures verify against the Rust reference at compile time, for the pinned
  firmware version. ABI drift becomes a build failure instead of a hang on hardware.
- **Marshaling unit tests.** The C code that builds firmware objects tests on the build
  host against traffic captures from the oracle machine.

## 8. Differential testing against the oracle

The strongest correctness tool available is a working reference implementation on
identical hardware.

- The same test job runs on a FuguAGX target and on the Asahi oracle.
- A trace-diff tool compares the firmware mailbox traffic of both runs.
  The oracle traffic comes from the m1n1 hypervisor.
- A corpus of known-good traces, pinned to the firmware version, lives in the artifact
  store. The marshaling unit tests replay it.
- Performance comparisons use the same model file and the same `llama-bench` arguments
  on both machines.

## 9. The agent control plane

The agent talks to one API on the controller, and to nothing else.
Small verb set, everything logged:

| Verb | Effect |
| --- | --- |
| `lease` / `release` | Take or return exclusive use of a target. Parallel agent sessions cannot collide. |
| `boot --kernel <hash>` | Reset the target and select the named kernel at the boot prompt. |
| `console tail` / `console send` | Stream or drive the serial console. |
| `reboot --tier <n>` | Invoke one rung of the recovery ladder. |
| `run-tests --level <n>` | Execute the test ladder up to a level. |
| `dump --region <name>` | Proxy-dump firmware logs or shared memory. |
| `reimage` | Reinstall the target with `autoinstall(8)`. |
| `power-stats` | Read the PDU telemetry. |

Every verb writes to the run database.
The API refuses any operation on a machine outside the lab VLAN.

## 10. The de-risk iterations

The project must not buy all the hardware and then discover a broken assumption.
Each iteration below retires one class of risk, has a testable exit criterion, and keeps
the spend behind the learning.

| # | Name | New hardware | Risk retired |
| --- | --- | --- | --- |
| H0 | CPU baseline | None | A GPU project that chases a gain the CPU already delivers. |
| H1 | Virtual target | None | Control-plane software risk. |
| H2 | First metal | 1 target, controller | Boot-chain controllability over serial. |
| H3 | Unattended recovery | Scrutinizer, PDU, rescue host | 24/7 autonomy. |
| H4 | Reference stack | Oracle machine | Firmware ABI misunderstanding. |
| H5 | Python bring-up | None | Hardware and firmware boot understanding. |
| H6 | First kernel code | None | The driver itself (gates G1 to G3). |
| H7 | Scale out | 1–2 targets, M2 Pro | Throughput and fleet management. |

### H0 — CPU baseline

The standing instruction of the specification, and of D2, executes first.
Rebuild `devel/libggml` with `-DGGML_CPU_ARM_ARCH=armv8.4-a+dotprod+fp16`, run
`llama-bench` on the target before and after, publish both results, and send them to the
port maintainer. Exit: published pp512 and tg128 numbers for the as-shipped and the
retuned build. This iteration produces the number that any GPU path must beat.

### H1 — Virtual target

Build the entire control plane against a fake target: an OpenBSD/arm64 virtual machine
under QEMU on the controller.
The serial console is a QEMU character device.
A power cycle is a process kill and restart.
A forced panic is a serial BREAK into `ddb` followed by the `panic` command.
Everything else is real: the harness API, the boot orchestration, the A/B kernel
selection at the boot prompt, the scripted `ddb` capture, the `autoinstall(8)` reimage,
the test runner, and the run database.
Exit: the agent completes a set number of unattended edit-build-boot-test-recover cycles
against the virtual machine, and that set includes induced panics and induced hangs.
This iteration costs no Apple hardware and proves that an agent can drive the loop at
all.

### H2 — First metal

One Mac mini M1, the controller, and a plain USB-C cable.
Point the H1 control plane at real hardware.
Verify the one assumption that only metal can verify: the OpenBSD boot chain (m1n1,
U-Boot, `efiboot`) accepts kernel selection over the serial console, unattended.
A human stays nearby and performs power cycles by hand.
Exit: twenty consecutive agent-driven kernel-swap cycles on metal, with no human input
except power cycles.

### H3 — Unattended recovery

Add the Central Scrutinizer, the metered PDU, the `apldog(4)` watchdog arming, and the
DFU rescue host with its switched USB link.
Then remove the human.
Exit: the agent recovers from every induced failure class — hang, panic, dead USB
gadget, and destroyed boot chain — with zero human action, and the lab then runs a
one-week soak with zero human touches.
After H3, the lab runs at night and on weekends, which is where an agent-driven project
earns its multiple over a human-driven one.

### H4 — Reference stack

Install Asahi Linux and the Rust driver on the oracle machine.
Bring up m1n1 hypervisor tracing on it.
Build the structure-layout extractor and generate the C `static_assert` set for the
pinned firmware version.
Capture the trace corpus for a set of known-good compute jobs.
Bring up the marshaling unit tests on the build host against that corpus.
Exit: the C structures verify byte-exact against the Rust reference, and the corpus
holds at least one complete, replayable compute job.
This retires the largest driver-correctness risk before any kernel code exists.

### H5 — Python bring-up

Run the existing m1n1 AGX experiments — `agx_boot.py`, then `agx_1tri.py` or
`agx_renderframe.py` — against a lab target from the controller, on the pinned firmware
version. Adapt them where the firmware version differs from what the scripts expect.
Exit: a Python-driven GPU job completes on lab hardware with no OpenBSD kernel involved.
The team (human or agent) that completes H5 understands the firmware boot sequence, the
initialization order, and the job submission path, at a cost of seconds per experiment
instead of minutes per kernel build.

### The decision gate

H6 starts the driver, so H6 starts the work that D2 currently forbids.
Between H5 and H6 sits a human decision: a proposed change to
[decisions](../../spec/decisions.md), argued with the H0 baseline, the H4/H5 evidence,
and the honest expected gain from the research report (prompt processing only, token
generation unchanged on the M1). No harness iteration before this gate violates D2.

### H6 — First kernel code

Gates G1 to G3 of the draft plan, executed on the harness: the attach skeleton, the
RTKit handshake, the UAT page tables, and one compute dispatch through a render node.
The harness now runs in anger, and its run database becomes the driver’s regression
history from the first commit.
Exit: the L2 test passes on a lab target.

### H7 — Scale out

Grow the fleet to two or three targets plus the M2 and M2 Pro machines for gate G7. Turn
on leases, parallel bisection, and the nightly soak.
Exit: two agent sessions work in parallel on separate targets without interference.

### Loop arithmetic

An incremental kernel build on M-class hardware takes low minutes.
A full heavy-loop cycle — build, boot, L0 to L2, recover — lands near four to six
minutes. One target therefore supports hundreds of autonomous iterations per week, and
the light loop supports hundreds per hour.

## 11. Bill of materials

Prices are August 2026 estimates for used or commodity hardware.

| Item | Qty | Est. cost | Iteration |
| --- | --- | --- | --- |
| Mac mini M1, 16 GB (used) | 3 | $900 | H2, H4, H7 |
| Mac mini M2 Pro (build host, later G7 target) | 1 | $1,100 | H2 |
| Rescue Mac, any Apple Silicon (used) | 1 | $300 | H3 |
| Lab controller, N100 class | 1 | $200 | H1 |
| Metered smart PDU | 1 | $150 | H3 |
| Central Scrutinizer (parts, open hardware) | 3 | $60 | H3 |
| USB HDMI capture dongle | 3 | $45 | H2 |
| Switched USB link for DFU, cables, VLAN switch | — | $150 | H3 |
| **Total** |  | **≈ $2,900** |  |

H0 and H1 spend nothing on this list.
H2 spends about $1,500 (one target, the build host, the controller, one dongle).
The rest of the spend waits for the iterations that need it.

## 12. Open questions and checks

Each item is a check that an iteration answers, or a fact to verify before purchase.

1. Does `efiboot` accept kernel selection over the U-Boot serial console on Apple
   Silicon, unattended?
   H2 exists to answer this.
   If the answer is no, the fallback is tethered m1n1 boot on every cycle.
2. What are the exact arming controls and period bounds of `apldog(4)` through the
   kernel watchdog sysctls on this hardware?
   H3 answers this.
3. Confirm that the Mac mini M1 powers on when AC power is applied, with OpenBSD
   installed. Tier 4 of the recovery ladder depends on it.
4. Which firmware version do the current m1n1 AGX experiments expect, and how large is
   the adaptation to the pinned lab version?
   H5 answers this.
5. Which DFU-restore path automates best from the rescue host: Apple Configurator,
   `idevicerestore`, or `macvdmtool` plus manual assets?
   H3 answers this.
6. Can the m1n1 hypervisor host an OpenBSD guest?
   This is unproven and not required — the hypervisor runs on the oracle under Linux —
   but a yes would add MMIO tracing of the FuguAGX driver itself, which would be a major
   debugging tool.
7. Can tethered m1n1 boot chainload the full OpenBSD boot chain (U-Boot plus `efiboot`)
   unattended? H2 or H3 answers this.
8. Sourcing for the Central Scrutinizer: parts and board fabrication, or a prebuilt
   unit.

## 13. Relationship to the specification

This document changes no specification text.
Three connections matter:

- **H0 is already mandated.** The aarch64 build-defect work in
  [spec/inference.md](../../spec/inference.md#inf-arm64) is exactly H0.
- **H1 to H3 serve the CPU duty too.** The `llama-bench` measurements on target hardware
  need a lab: a target, a controller, serial capture, and remote recovery.
  The same lab measures CPU builds and, later, exercises a driver.
  The harness spend is therefore not conditional on FuguAGX.
- **H6 needs a decision change.** Starting the driver contradicts D2 as written.
  The decision gate between H5 and H6 is where a human approves or rejects that change,
  with the H0 baseline and the H4/H5 evidence on the table.

## 14. Sources

All URLs read on 21 August 2026 unless another date is given.

- m1n1 repository, `proxyclient/experiments` (`agx_boot.py`, `agx_1tri.py`,
  `agx_renderframe.py`, `agx_dumpstructs.py`, and others) —
  https://github.com/AsahiLinux/m1n1/tree/main/proxyclient/experiments
- Asahi Linux documentation, debugging via serial console —
  https://asahilinux.org/docs/hw/soc/serial-debug/
- Central Scrutinizer, a serial adapter for M1/M2/M3, by Marc Zyngier —
  https://hackaday.io/project/192826-central-scrutinizer-a-serial-adapter-for-m1m2m3
- macvdmtool, Apple Silicon USB-PD VDM control from macOS —
  https://github.com/AsahiLinux/macvdmtool
- `apldog(4)` manual page (Apple SoC watchdog) — https://man.openbsd.org/apldog.4
- `ddb(4)` manual page (kernel debugger) — https://man.openbsd.org/ddb.4
- `savecore(8)` manual page — https://man.openbsd.org/savecore.8
- `autoinstall(8)` manual page — https://man.openbsd.org/autoinstall.8
- `aplsmc(4)` manual page (SMC sensors) — https://man.openbsd.org/aplsmc.4
- `sys/arch/arm64/conf/GENERIC` (`apldog*`, `aplrtk*`, `aplsmc*`) —
  https://raw.githubusercontent.com/openbsd/src/master/sys/arch/arm64/conf/GENERIC
- `AsahiLinux/linux`, `drivers/gpu/drm/asahi` (the Rust reference driver) —
  https://github.com/AsahiLinux/linux/tree/asahi-wip/drivers/gpu/drm/asahi
- Janne Grunau, IGT test series for asahi on dri-devel, January 2026 — see
  [OpenBSD and the Apple GPU](openbsd-apple-silicon-gpu.md), section 5, for the archive
  links.
- FuguTTX research report, OpenBSD and the Apple GPU, 1 August 2026 —
  [openbsd-apple-silicon-gpu.md](openbsd-apple-silicon-gpu.md)
- FuguTTX draft plan, Apple GPU support for OpenBSD on the Mac mini —
  [apple-gpu-openbsd-draft-plan.md](apple-gpu-openbsd-draft-plan.md)
