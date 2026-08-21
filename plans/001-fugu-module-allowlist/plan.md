# 001 — The Fugu module allow-list of the harness

## Status

Proposed. This plan waits for human approval.
This plan adapts the plan template for a decision proposal, so it holds the argument
sections and the human-decision section.

The plan goes against decision D7, so it changes no specification document.
It writes this one file.
A human must answer the one question of the section “What a human must decide”.
No other work in this change set depends on that answer.

## Purpose

D7 permits one module of the Fugu distribution in the harness.
This plan proposes a named allow-list of seven modules.
The list holds `Fugu::REPL`, `Fugu::Sandbox`, `Fugu::Log`, `Fugu::Process`,
`Fugu::Config`, `Fugu::File` and `Fugu::CLI`.

Each module of the list serves a named unit of this specification.
Each module loads with base modules only.
The port dependency set does not change.
The harness then writes less code, and it holds the same behavior as its sibling tools.

## Why FuguTTX holds this work

D7 fixes the module set.
The decision reads: “Perl for the harness body, with base modules plus `Fugu::REPL`.” It
also reads: “and the client loads only this module from the distribution”.

`repository.md` REP-CI states the check of that rule.
The unit reads: “the dependency check (base-module imports plus `Fugu::REPL`, and no
other)”.

`harness.md` HRN-LANG restates the rule.
The unit reads: “A CI check enforces the import rule: base modules plus `Fugu::REPL`,
and no other”.

The `CLAUDE.md` of this repository sets the procedure.
It reads: “When your change goes against a decision, stop.”
It then requires a proposal to `spec/decisions.md`, and human approval first.

This plan is that proposal.
It edits no file under `spec/`, and it holds no implementation.

## Consumers and citations

| Repo | Unit | Rules | Need |
| --- | --- | --- | --- |
| FuguTTX | `HRN-REPL` | HRN-REPL-1 to HRN-REPL-9 | The line editor of the client. D7 permits this module today, so the list changes nothing here |
| FuguTTX | `HRN-SAFE-PLEDGE` | none: the unit holds prose, and it holds no numbered rule | One pledge call and one unveil call for each process. **Blocked by D7** |
| FuguTTX | `HRN-PROC` | none: the unit holds a table and prose, and it holds no numbered rule | The pledge set and the unveil enumeration of each of the three processes. **Blocked by D7** |
| FuguTTX | `HRN-SAFE-AUDIT` | none: the unit holds prose, and it holds no numbered rule | The syslog duplicate of each audit record, under a pledge with no `unix` promise. **Blocked by D7** |
| FuguTTX | `HRN-TOOL-RO` | HRN-TOOL-RO-1 to HRN-TOOL-RO-4 | Run each diagnostic, capture its output, and read its exit status. **Blocked by D7** |
| FuguTTX | `HRN-TOOL-GATE` | HRN-TOOL-GATE-1 to HRN-TOOL-GATE-5 | Run each dry run, then the real call after the confirmation. **Blocked by D7** |
| FuguTTX | `HRN-CANCEL` | none: the unit holds prose, and it holds no numbered rule | Stop a running tool on an operator cancel. **Blocked by D7** |
| FuguTTX | `HRN-CONFIRM` | HRN-CONFIRM-9, HRN-CONFIRM-10 | Write the held candidate bytes, then rename the file into place. **Blocked by D7** |
| FuguTTX | `HRN-SKILLS` | none: the unit holds prose, and it holds no numbered rule | Read one `SKILL.md` file, and check the directory name. **Blocked by D7** |
| FuguTTX | `HRN-SPLIT` | none: the unit holds prose, and it holds no numbered rule | The command line of `ttx`, with its subcommands and its exit codes. **Blocked by D7** |
| FuguTTX | `HRN-FETCH` | none: the unit holds prose, and it holds no numbered rule | `ttx fetch` is one subcommand with its own pledge set. **Blocked by D7** |
| FuguTTX | `HRN-PERL` | none: the unit holds bullets, and they hold no numbered rule | Each module loads before the pledge. Each exec takes a list. Each program runs under taint mode |
| FuguTTX | `HRN-PKG` | none: the unit holds prose, and it holds no numbered rule | The port lists p5-Fugu as a run dependency today |
| FuguPass | `CLI-SPLIT` | CLI-SPLIT-7 | The precedent. FuguPass D-16 reads: “The interface program is Perl on the Fugu library, and Fugu::REPL is its line editor.” The wider rule already exists for a sibling tool |

Each FuguTTX unit above is `open` in the register.
No unit holds code today, so an approval changes no state and deletes no code.

## Scope

In scope:

- The proposed text of D7, ready to paste.
- The seven modules of the list, and the unit that each one serves.
- The argument for the change, and the argument against it.
- The consequence of each answer of the human.

Out of scope:

- Any edit of `spec/decisions.md`, and any edit of an other document under `spec/`.
- Any harness code, and any test.
- `Fugu::Daemon`, `Fugu::EventLoop`, `Fugu::Imsg`, `Fugu::Control`, `Fugu::Privdrop` and
  `Protocol::Imsg`. The list does not hold them.
- A CPAN module. D7 reads: “The harness must not install from CPAN on the target.”
  The list keeps that rule.
- The `fuguvm` tool. The repository operates it as a command, and that use needs no
  change to D7.

## Constraints that shape the design

- **The target installs nothing from CPAN.** D7 reads: “Each harness dependency comes
  from OpenBSD base or from an OpenBSD package.”
  Each module of the list must load with base modules only.
- **Each module must load before the pledge.** HRN-PERL reads: “Load and exercise every
  module before the process pledges.
  A lazy `require` after `pledge(2)` needs `rpath`. Its absence kills the process with
  `SIGABRT`.”
- **The parent pledge holds no `unix` promise.** The HRN-PROC table gives the parent set
  `stdio rpath wpath cpath proc exec`. HRN-SAFE-AUDIT names the consequence: “The
  harness pins the native log method (`setlogsock('native')`), so `Sys::Syslog` does not
  need the `unix` promise.”
- **`Fugu::REPL` must stand alone.** HRN-REPL-2 reads: “The module must load with base
  modules only, and it must stand alone: it must not load an other Fugu module.”
  A wider list must not change that rule.
- **Each program runs under taint mode.** HRN-PERL sets the rule, and REP-CI runs the
  check.
- **The import rule is a machine check.** REP-CI runs it on each push, so the list must
  be a fixed set of names.

## The proposed decision

D7 holds two sentences that name the module set.
The first sentence sits in the first paragraph.
The second sentence ends the second paragraph.

The first sentence reads today:

> Perl for the harness body, with base modules plus `Fugu::REPL`.

The proposal replaces it with:

> Perl for the harness body, with base modules plus the Fugu module allow-list.

The second sentence reads today:

> The module loads with base modules only, and the client loads only this module from
> the distribution ([harness](harness.md#hrn-repl)).

The proposal replaces it with:

> The Fugu module allow-list holds `Fugu::REPL`, `Fugu::Sandbox`, `Fugu::Log`,
> `Fugu::Process`, `Fugu::Config`, `Fugu::File` and `Fugu::CLI`. The harness must not
> load an other module of the distribution.
> Each module of the list loads with base modules only, so the target installs nothing
> from CPAN. `Fugu::REPL` must stand alone, and it must not load an other module of the
> list ([harness](harness.md#hrn-repl)).

The list lives in D7 alone.
REP-CI and HRN-LANG must then name the check and point at D7 for the list.

## The allow-list, module by module

The harness holds no code today.
Each cell of the last column names the code that the specification requires the harness
to hold under D7 as it stands.

| Module | Unit and rules | Methods | What the harness writes under D7 today |
| --- | --- | --- | --- |
| `Fugu::REPL` | `HRN-REPL`; HRN-REPL-1 to HRN-REPL-9 | `new`, `read_line`, `event`, `ready_handle`, `confirm`, `display_filter`, `show`, `help_text`, `history`, `is_interactive`, `restore` | Nothing. D7 permits this module. The module does not exist in Fugu yet, and `/home/user/Fugu/plans/001-fugu-repl/plan.md` holds its contract |
| `Fugu::Sandbox` | `HRN-SAFE-PLEDGE` and `HRN-PROC`; neither unit holds a numbered rule | `is_supported`, `pledge`, `unveil`, `unveil_lock`, `perl_lib_dirs`, `system_paths` | The harness calls `OpenBSD::Pledge` and `OpenBSD::Unveil` itself. It also enumerates the library directories of the perl that runs, and the resolver files, itself |
| `Fugu::Log` | `HRN-SAFE-AUDIT`; the unit holds prose, and it holds no numbered rule | `new` with `mode`, `level`, `ident` and `facility`; `debug`, `info`, `notice`, `warning`, `error`; `set_level`; `reopen`; `default`; `set_default` | The harness calls `Sys::Syslog` itself, and it writes its own level filter. The module does not pin `setlogsock('native')` today, so this row needs Fugu plan 005 |
| `Fugu::Process` | `HRN-TOOL-RO`, HRN-TOOL-RO-1 to HRN-TOOL-RO-4; `HRN-TOOL-GATE`, HRN-TOOL-GATE-1 to HRN-TOOL-GATE-5; `HRN-CANCEL`, which holds no numbered rule | `run` with `cmd`, `timeout`, `stdin`, `cwd` and `passthrough`; `spawn_command` with `cmd`, `daemonize`, `stdin`, `stdout` and `stderr`; `exit_code`; `is_alive`; `terminate` with `grace_period` and `on_kill`; `wait_exit` | The harness writes its own fork and exec, its own reader of two descriptors at the same time, its own timeout, and its own decode of the wait status |
| `Fugu::Config` | `HRN-PKG`; the unit holds prose, and it holds no numbered rule | `new` with `file`; `load`; `get`; `setting_names`; `parse_bool`; `blocks`; `block`; `error` | The harness holds each setting as a constant of the program. HRN-PKG names the configuration directory `/etc/ttx`, and no unit defines a configuration file today |
| `Fugu::File` | `HRN-CONFIRM`, HRN-CONFIRM-9 and HRN-CONFIRM-10; `HRN-SKILLS`, which holds no numbered rule | `read`, `write` with `mode`, `write_atomic` with `mode`, `ensure_dir` with `mode`, `valid_name` | The harness writes its own temporary file and its own rename. It also writes its own mode check for the candidate directory and for `/var/log/ttx`, and its own name check for a skill directory |
| `Fugu::CLI` | `HRN-SPLIT` and `HRN-FETCH`; neither unit holds a numbered rule | `new` with `commands`, `name`, `options`, `usage`, `epilogue` and `log`; `run`; `option`; `options`; `command`; `name`; `log`; `print_help`; `usage_error`; `command_usage_error`; the codes `EXIT_SUCCESS` 0, `EXIT_ERROR` 1, `EXIT_INVALID_ARGS` 2, `EXIT_CONFIG_ERROR` 3 and `EXIT_TIMEOUT` 7 | The harness writes its own `Getopt::Long` setup for `ttx`, its own help text, and its own exit-code set |

Three notes belong to the table.

`Fugu::Sandbox->perl_lib_dirs` and `Fugu::Sandbox->system_paths` serve the unveil
enumeration of HRN-PROC. The parent execs its own program to start each child, so the
child needs the library directories of the perl that runs.
`perl_lib_dirs` names that stable set, from `privlibexp`, `archlibexp`, `sitelibexp` and
`sitearchexp` of `Config`. `system_paths` names the read-only inventory that every
daemon repeats. Neither method calls a syscall, so a test can prove the enumeration off
OpenBSD. The paths of the harness itself stay in the harness: the diagnostic binaries,
the doas wrappers, the candidate directory and the log directory.

Two rows need work in the Fugu repository first.
`Fugu::Log` needs the native syslog pin of Fugu plan 005. `Fugu::Process->terminate`
signals one process today, and HRN-CANCEL reads: “The parent kills the process group of
a running tool.”
The process-group option comes from Fugu plan 006. HRN-PERL also needs a
fixed `%ENV` before each exec, and the `env` argument comes from
`/home/user/Fugu/plans/002-process-child-environment/plan.md`.

The list is closed under the load relation.
`Fugu::CLI` loads `Fugu::Log`. `Fugu::File` loads `Fugu::Log`. `Fugu::Process` loads
`Fugu::CLI`, for the `EXIT_ERROR` constant.
The list holds each of those modules, so the harness loads no module outside the list.

## The arguments for

1. **The port dependency set does not grow.** HRN-PKG reads: “The port lists llama.cpp
   and p5-Fugu as run dependencies, with a minimum Fugu version”.
   D7 reads: “The port dependencies are llama.cpp and p5-Fugu, and no other.”
   The p5-Fugu package already reaches the target.
   The block is the import rule, and not the package.

2. **The target installs nothing from CPAN.** Fugu loads with core Perl only, and
   `t/fugu/coreperl.t` proves the load contract.
   Every CPAN use in Fugu is a lazy `require` behind an optional feature, and no module
   of the list is such a feature.
   The list needs these base modules only: `Config`, `Exporter`, `Fcntl`,
   `File::Basename`, `File::Path`, `File::Spec`, `Getopt::Long`, `IO::Handle`,
   `IO::Select`, `JSON::PP`, `POSIX`, `Sys::Syslog` and `Time::HiRes`. On OpenBSD
   `Fugu::Sandbox` also loads `OpenBSD::Pledge` and `OpenBSD::Unveil`, which ship in
   base.

3. **Each module loads at compile time, so HRN-PERL holds.** `Fugu::Sandbox` loads
   `OpenBSD::Pledge` and `OpenBSD::Unveil` in a `BEGIN` block, so the load happens
   before the pledge. One exception exists today: `Fugu::Process` requires `Config`
   inside `_custom_inc_paths`, and `spawn_perl` calls that sub.
   Fugu plan 002 moves the load to compile time.

4. **One implementation serves every FuguBSD tool.** Fugu holds one pledge wrapper, one
   privilege drop, one audit log, and one process control.
   FuguVM already loads `Fugu::CLI`, `Fugu::Config`, `Fugu::File`, `Fugu::Log` and
   `Fugu::Process`. FuguPass D-16 permits the whole library in its interface program.
   A correction then reaches every tool one time, and the operator behavior stays
   uniform. The list holds the pledge wrapper and the audit log, and it holds no
   privilege drop. Argument 5 of the section below states that limit.

5. **The change deletes no code.** Every HRN unit is `open` in the register, and the
   harness holds no code today.
   An approval therefore costs no rework, and it removes work from each unit of the
   consumers table.

6. **A test can prove the sandbox off OpenBSD.** `Fugu::Sandbox` is real on OpenBSD, and
   it is a successful no-op elsewhere.
   `is_supported` reports which of the two the caller gets, so a test can tell
   enforcement from emulation.
   REP-CI reads: “No-op shims under `harness/t/lib/` stand in for both modules, so
   `perl -c` and `prove` run on any runner.”
   The module removes the need for those two shims.

## The arguments against

1. **The harness gains a version dependency on a sibling project.** HRN-REPL-1 already
   needs “a minimum version” of the p5-Fugu package.
   That minimum version then covers seven modules and not one.
   Three rows of the module table wait on a Fugu plan, and each plan is a proposal
   today. The `Fugu::REPL` row waits on Fugu plan 001, because the module does not exist
   today. The `Fugu::Log` row waits on plan 005, and the `Fugu::Process` row waits on
   plans 002 and 006. A Fugu release then gates a harness feature.

2. **A Fugu defect reaches the harness.** The parent holds the `proc exec` promise, and
   the model process parses hostile model output.
   A defect in a shared module then sits inside a security boundary.
   The Fugu tests are the callers of record of the library, and the harness is not one
   of them. No Fugu test runs under `perl -T` today, and HRN-PERL requires taint mode for
   every program of the harness.

3. **The CI import check grows a list to maintain.** REP-CI holds a one-name rule today,
   and the list makes it a seven-name rule.
   The check and D7 must then agree, and a drift between them is silent.
   The list must also stay closed under the load relation: a new `use` line inside a
   Fugu module can widen what the target loads, with no change in this repository.
   A check that reads the import lines of `harness/` alone does not see that widening.

4. **Four modules stay excluded, so the harness still writes four facilities.**
   `Fugu::Daemon`, `Fugu::EventLoop`, `Fugu::Imsg` and `Fugu::Control` are not on the
   list. The harness therefore writes its own daemon start, its own select loop, its own
   frame codec and its own control socket.
   HRN-PROC keeps the fork and exec of its own program, and the descriptor flag before
   the exec. HRN-LANG keeps the length-prefixed `JSON::PP` record over `socketpair(2)`.
   `Protocol::Imsg` ships in the same distribution and is not on the list, so that
   framing stays in the harness.
   HRN-SOCKET keeps the `SO_PEERCRED` read, and HRN-CONFIRM-6 depends on it.
   Two Fugu plans would close those gaps:
   `/home/user/Fugu/plans/005-pledged-daemon-corrections/plan.md` and
   `/home/user/Fugu/plans/006-privilege-separated-children/plan.md`. Plan 006 states the
   gate itself: “No consumer can call this work today.
   The FuguTTX harness is the only named consumer, and FuguTTX decision D7 blocks it.”
   The list reaches one half of each plan only.
   It holds `Fugu::Process`, so `spawn_peer` and the process-group `terminate` of plan
   006 become reachable.
   It holds no `Fugu::Control`, so the control socket of plan 006 stays unreachable.
   It holds `Fugu::Log`, so the syslog pin of plan 005 becomes reachable.

5. **The privilege drop stays in the harness.** The list holds no `Fugu::Privdrop`, and
   HRN-SAFE-DROP needs the drop order and the verification of each id after the drop.
   The harness therefore writes that code, and Fugu plan 005 corrects the same fault
   inside `Fugu::Privdrop` for its other callers.
   Open question 1 asks the human about that module.

6. **One row of the list is weak today.** `Fugu::Config` serves a configuration read,
   and no unit defines a configuration file of the harness.
   The grammar of the module is `key value` or `key = value`, with `#` comments.
   The frontmatter of HRN-SKILLS is `key: value`, so `Fugu::Config` must not read a
   `SKILL.md` file. The value of the row is a future `/etc/ttx` configuration file, which
   then needs no new parser.

## What a human must decide

One question stands: does D7 widen from `Fugu::REPL` to the seven-module allow-list?

Under “yes”:

- A later change edits `spec/decisions.md` for D7, `spec/repository.md` for the REP-CI
  check text, and `spec/harness.md` for the HRN-LANG import sentence.
  The list lives in D7, and the other two documents point at D7.
- Each unit of the consumers table keeps its text.
  A unit names a facility, and D7 names the module set.
- The register keeps every HRN row `open`. No code changes in this repository.
- The CI dependency check must hold the list, and a test must prove the closure of the
  list.
- Fugu gains a harness caller for plan 002, for the `Fugu::Log` half of plan 005, and
  for the `Fugu::Process` half of plan 006. Plan 006 then holds a caller of record for
  the first time.

Under “no”:

- The specification stays as it is.
  D7 stands, REP-CI stands, and HRN-LANG stands.
- The harness writes each facility itself: the pledge and unveil calls, the unveil
  enumeration, the syslog duplicate, the process control, the atomic file install, the
  command line, and the configuration read.
- Fugu deletes nothing.
  Plans 002 and 005 keep their other consumers: FuguOracle, FuguPass and FuguVM. Plan
  006 waits for an other consumer, or Fugu drops it.
  Plan 006 already carries that gate.
- This is a valid outcome.
  The harness holds no code today, so a “no” answer costs no rework.

Nothing else in this change set depends on the answer.
The `fuguvm` edits, the `Fugu::REPL` contract, and every other edit of this
specification are reachable under D7 as it stands.

## Load contract

Each module of the list loads with base modules only, so the list adds no CPAN
dependency.

| Module | Base modules | Modules of the list |
| --- | --- | --- |
| `Fugu::REPL` | `POSIX`, `IO::Select`, `Encode` | none, by HRN-REPL-2 |
| `Fugu::Sandbox` | `Config`; on OpenBSD also `OpenBSD::Pledge` and `OpenBSD::Unveil` | none |
| `Fugu::Log` | `IO::Handle`, `Sys::Syslog` | none |
| `Fugu::Process` | `Fcntl`, `IO::Select`, `POSIX`, `Time::HiRes` | `Fugu::CLI` |
| `Fugu::Config` | `File::Basename`, `File::Spec` | none |
| `Fugu::File` | `Fcntl`, `File::Basename`, `File::Path`, `File::Spec`, `JSON::PP` | `Fugu::Log` |
| `Fugu::CLI` | `Exporter`, `Getopt::Long` | `Fugu::Log` |

The `deps/` manifests need no new line for a module of the list.
One `dist` line installs the whole distribution, and `scripts/deps` installs the tarball
with cpanm. `deps/Linux.txt` and `deps/Darwin.txt` hold one line each today, for the
Scaleway CLI. REP-CI reads: “CI installs the Fugu distribution through `scripts/deps`,
so `prove` runs with the real module”.
That statement needs the manifest line, under each answer of the human.

## Files

This plan writes one file: `plans/001-fugu-module-allowlist/plan.md`. It creates, edits
and deletes no other file.

Under “yes”, a later change edits these files, and no other:

| File | Change |
| --- | --- |
| `spec/decisions.md` | The two sentences of D7, as the section “The proposed decision” gives them |
| `spec/repository.md` | The REP-CI check text names the list of D7. The REP-TOOLS row for the harness body names the same list |
| `spec/harness.md` | The HRN-LANG import sentence names the list of D7 |
| `deps/Linux.txt`, `deps/Darwin.txt` | One `dist` line for the Fugu distribution. The repository holds these two manifests only |
| `spec/STATUS.md` | No change. Each edited unit is `open`, and no edit adds a unit |

## Tests

This plan adds no code, so it adds no test.

Under “yes”, the CI checks of REP-CI change:

- The dependency check must accept each module of the list, and it must fail on every
  other module of the distribution.
- The check must fail when the list of the check and the list of D7 disagree.
- A harness test must run under `perl -T`, and it must load each module of the list
  before the pledge.
- A harness test must prove that each module of the list loads no module outside the
  list.
- A test can call `Fugu::Sandbox->is_supported` to tell enforcement from emulation, so
  the no-op shims for `OpenBSD::Pledge` and `OpenBSD::Unveil` leave the test tree.

Fugu holds the unit test of each module.
Fugu needs one taint-mode test before the harness loads the list, because no Fugu test
runs under `perl -T` today.

## Acceptance

- `make check` passes in this repository: `uv lock --check`, `ruff format --check`,
  `ruff check`, `flowmark --check` and `make spec-check`.
- `make spec-check` passes.
  `scripts/spec_check.py` scans `CLAUDE.md`, `spec/` and `docs/`, so this file adds no
  link and no citation to validate.
- No file under `spec/` changes.
- A human answers the question of the section “What a human must decide”.

## Open questions

1. **Must the list hold `Fugu::Privdrop`?** HRN-SAFE-DROP needs the drop order and the
   verification of each id after the drop.
   Fugu plan 005 corrects the module for that use.
   The list does not hold it today, so the harness writes the drop itself.
2. **Must the list hold `Fugu::Control` and `Protocol::Imsg`?** HRN-SOCKET and HRN-LANG
   then lose their own code.
   HRN-LANG states the reason for the harness code today: “Base Perl has no
   `imsg_init(3)` interface.”
   A change of that answer needs its own proposal, and Fugu plan 006 holds the
   control-socket half.
3. **Does taint mode hold across the list?** No Fugu test runs under `perl -T` today.
   A taint defect in a shared module reaches every program of the harness, so the proof
   must exist before the harness loads the list.
4. **How does the check stay closed?** A new `use` line inside a Fugu module can widen
   what the target loads.
   A test in Fugu, or a check in this repository, must prove the closure of the list.
5. **Which minimum p5-Fugu version does the port name?** Fugu derives its version from
   its latest `v*` tag.
   The minimum version must cover each module of the list, and it must cover the
   corrections of Fugu plans 002 and 005.
