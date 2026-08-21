# 012 — The Fugu module allow-list of the harness

## Status

Approved, and applied in the specification.
The remaining work is the harness code.

A human approved the allow-list of seven modules.
D7 holds the list, and it holds it alone.
`repository.md` REP-CI names the dependency check, and REP-TOOLS names the same rule for
the harness body. Each one points at D7 for the names.
`harness.md` HRN-LANG names the import rule, and each unit of the module table below
names its module. `deps/Linux.txt` and `deps/Darwin.txt` install the Fugu distribution,
so `prove` runs against the real modules.

The harness holds no code, so the adoption starts from an empty tree.
`roadmap.md` gives that work its scope in two phases.
The harness slice adopts `Fugu::Process` for the read-only tools and the gated
mutations, and it adopts `Fugu::File` for the candidate install of HRN-CONFIRM-9. The
harness completion adopts each other row of the module table.
`STATUS.md` gives each unit its “Done by” phase, and every HRN unit is `open` there.

## Purpose

D7 permits seven modules of the Fugu distribution in the harness.
The list holds `Fugu::REPL`, `Fugu::Sandbox`, `Fugu::Log`, `Fugu::Process`,
`Fugu::Config`, `Fugu::File` and `Fugu::CLI`.

This plan is the adoption map.
It names the unit that each module serves, the methods that each unit needs, and the
code that the harness does not write.

Each module of the list loads with base modules only.
The port dependency set does not change.
The harness therefore writes less code, and it holds the same behavior as its sibling
tools.

## Why FuguTTX holds this work

The harness lives in this repository, and the import check lives here too.
Fugu holds each module, and Fugu holds no consumer policy.
The decision that permits a module therefore belongs here.

`repository.md` REP-CI states the check.
The unit reads: “The dependency check permits a base-module import and a module of the
allow-list of D7, and it refuses each other module.”

`harness.md` HRN-LANG states the import rule.
The unit reads: “A CI check enforces the import rule: a base module, or a module of the
allow-list, and no other”.

The list lives in D7 alone.
REP-CI, REP-TOOLS and HRN-LANG each point at D7 for the names.

## Consumers and citations

| Repo | Unit | Rules | Need |
| --- | --- | --- | --- |
| FuguTTX | `HRN-REPL` | HRN-REPL-1 to HRN-REPL-11 | The line editor of the client, through `Fugu::REPL` |
| FuguTTX | `HRN-SAFE-PLEDGE` | none: the unit holds prose, and it holds no numbered rule | One pledge call and one unveil call for each process, through `Fugu::Sandbox` |
| FuguTTX | `HRN-PROC` | none: the unit holds a table and prose, and it holds no numbered rule | The pledge set and the unveil enumeration of each of the three processes, through `Fugu::Sandbox` |
| FuguTTX | `HRN-SAFE-AUDIT` | none: the unit holds prose, and it holds no numbered rule | The syslog duplicate of each audit record, through `Fugu::Log`, under a pledge with no `unix` promise |
| FuguTTX | `HRN-TOOL-RO` | HRN-TOOL-RO-1 to HRN-TOOL-RO-4 | Run each diagnostic, capture its output, and read its exit status, through `Fugu::Process` |
| FuguTTX | `HRN-TOOL-GATE` | HRN-TOOL-GATE-1 to HRN-TOOL-GATE-5 | Run each dry run, then the real call after the confirmation, through `Fugu::Process` |
| FuguTTX | `HRN-CANCEL` | none: the unit holds prose, and it holds no numbered rule | Stop a running tool on an operator cancel, through the process-group form of `Fugu::Process->terminate` |
| FuguTTX | `HRN-CONFIRM` | HRN-CONFIRM-9, HRN-CONFIRM-10 | Write the held candidate bytes, then rename the file into place, through `Fugu::File->write_atomic` |
| FuguTTX | `HRN-SKILLS` | none: the unit holds prose, and it holds no numbered rule | Read one `SKILL.md` file, and check the directory name, through `Fugu::File` |
| FuguTTX | `HRN-SPLIT` | none: the unit holds prose, and it holds no numbered rule | The command line of `ttx`, with its subcommands and its exit codes, through `Fugu::CLI` |
| FuguTTX | `HRN-FETCH` | none: the unit holds prose, and it holds no numbered rule | `ttx fetch` is one subcommand with its own pledge set, through `Fugu::CLI` |
| FuguTTX | `HRN-PERL` | none: the unit holds bullets, and they hold no numbered rule | Each module loads before the pledge. Each exec takes a list, with the fixed `%ENV` of the `env` argument. Each program runs under taint mode |
| FuguTTX | `HRN-PKG` | none: the unit holds prose, and it holds no numbered rule | The port lists p5-Fugu as a run dependency, with a minimum version |
| FuguPass | `CLI-SPLIT` | CLI-SPLIT-7 | The precedent. FuguPass D-16 reads: “The interface program is Perl on the Fugu library, and Fugu::REPL is its line editor.” The wider rule holds for a sibling tool |

Each FuguTTX unit above is `open` in the register.
The adoption therefore writes new code, and it deletes none.

## Scope

In scope:

- The adoption map: the seven modules, and the unit that each one serves.
- The methods that each unit needs, and the code that the harness does not write.
- The load closure of the list.
- The cost of the list, and the facilities that stay in the harness.

Out of scope:

- Any edit of a document under `spec/`. The specification holds the list already.
- The harness code and its tests.
  `roadmap.md` gives that work its phase.
- `Fugu::Daemon`, `Fugu::EventLoop`, `Fugu::Imsg`, `Fugu::Control`, `Fugu::Privdrop` and
  `Protocol::Imsg`. The list does not hold them.
- A CPAN module. D7 reads: “The harness must not install from CPAN on the target.”
  The list keeps that rule.
- The `fuguvm` tool. The repository operates it as a command, and REP-TOOLS-1 holds that
  rule.

## Constraints that shape the design

- **The target installs nothing from CPAN.** D7 reads: “Each harness dependency comes
  from OpenBSD base or from an OpenBSD package.”
  Each module of the list must load with base modules only.
- **Each module must load before the pledge.** HRN-PERL reads: “Load and exercise every
  module before the process pledges.
  A lazy `require` after `pledge(2)` needs `rpath`. Its absence kills the process with
  `SIGABRT`.”
- **The parent pledge holds no `unix` promise.** The HRN-PROC table gives the parent set
  `stdio rpath wpath cpath proc exec`. HRN-SAFE-AUDIT names the consequence: “The module
  pins the native log method (`setlogsock('native')`), so the process needs no `unix`
  promise.”
- **`Fugu::REPL` must stand alone.** HRN-REPL-2 reads: “The module must load with base
  modules only, and it must stand alone: it must not load an other Fugu module.”
  The list must not change that rule.
- **Each program runs under taint mode.** HRN-PERL sets the rule, and REP-CI runs the
  check.
- **The import rule is a machine check.** REP-CI runs it on each push, so the list is a
  fixed set of names.

## The decision as it stands

D7 holds two sentences that name the module set.
The first sentence sits in the first paragraph:

> Perl for the harness body, with base modules plus the Fugu module allow-list.

The second paragraph holds the list itself:

> The Fugu module allow-list holds `Fugu::REPL`, `Fugu::Sandbox`, `Fugu::Log`,
> `Fugu::Process`, `Fugu::Config`, `Fugu::File` and `Fugu::CLI`. The harness must not
> load an other module of the distribution.
> Each module of the list loads with base modules only, so the target installs nothing
> from CPAN. `Fugu::REPL` must stand alone, and it must not load an other module of the
> list.

D7 then states where the list lives: “The list lives in this decision alone.”
REP-CI names the check, and it points at D7 for the list.

## The allow-list, module by module

The harness holds no code today.
Each cell of the last column names the code that the harness does not write, because the
module of the row holds it.

| Module | Unit and rules | Methods | What the module removes from the harness |
| --- | --- | --- | --- |
| `Fugu::REPL` | `HRN-REPL`; HRN-REPL-1 to HRN-REPL-11 | `new`, `read_line`, `event`, `ready_handle`, `confirm`, `display_filter`, `show`, `help_text`, `history`, `is_interactive`, `restore` | The line editor, its key table and its display filter. The module does not exist in Fugu yet, and `/home/user/Fugu/plans/001-fugu-repl/plan.md` holds its contract |
| `Fugu::Sandbox` | `HRN-SAFE-PLEDGE` and `HRN-PROC`; neither unit holds a numbered rule | `is_supported`, `pledge`, `unveil`, `unveil_lock`, `perl_lib_dirs`, `system_paths` | The `OpenBSD::Pledge` and `OpenBSD::Unveil` calls. Also the enumeration of the library directories of the perl that runs, and of the resolver files |
| `Fugu::Log` | `HRN-SAFE-AUDIT`; the unit holds prose, and it holds no numbered rule | `new` with `mode`, `level`, `ident` and `facility`; `debug`, `info`, `notice`, `warning`, `error`; `set_level`; `reopen`; `default`; `set_default` | The `Sys::Syslog` calls and the level filter. The module does not pin `setlogsock('native')` today, so this row needs Fugu plan 005 |
| `Fugu::Process` | `HRN-TOOL-RO`, HRN-TOOL-RO-1 to HRN-TOOL-RO-4; `HRN-TOOL-GATE`, HRN-TOOL-GATE-1 to HRN-TOOL-GATE-5; `HRN-CANCEL`, which holds no numbered rule | `run` with `cmd`, `timeout`, `stdin`, `cwd` and `passthrough`; `spawn_command` with `cmd`, `daemonize`, `stdin`, `stdout` and `stderr`; `exit_code`; `is_alive`; `terminate` with `grace_period`, `on_kill` and the process group; `run` with the new session; `wait_exit` | The fork and the exec. Also the reader of two descriptors, the timeout, and the decode of the wait status |
| `Fugu::Config` | `HRN-PKG`; the unit holds prose, and it holds no numbered rule | `new` with `file`; `load`; `get`; `setting_names`; `parse_bool`; `blocks`; `block`; `error` | The parser of a configuration file. HRN-PKG names the configuration directory `/etc/ttx`, and no unit defines a configuration file today |
| `Fugu::File` | `HRN-CONFIRM`, HRN-CONFIRM-9 and HRN-CONFIRM-10; `HRN-SKILLS`, which holds no numbered rule | `read`, `write` with `mode`, `write_atomic` with `mode`, `ensure_dir` with `mode`, `valid_name` | The temporary file and the rename. `ensure_dir` refuses a symlink, and `valid_name` refuses an unsafe path component. The harness keeps the mode and owner check of the candidate directory, and the character set and length of a skill name |
| `Fugu::CLI` | `HRN-SPLIT` and `HRN-FETCH`; neither unit holds a numbered rule | `new` with `commands`, `name`, `options`, `usage`, `epilogue` and `log`; `run`; `option`; `options`; `command`; `name`; `log`; `print_help`; `usage_error`; `command_usage_error`; the codes `EXIT_SUCCESS` 0, `EXIT_ERROR` 1, `EXIT_INVALID_ARGS` 2, `EXIT_CONFIG_ERROR` 3 and `EXIT_TIMEOUT` 7 | The `Getopt::Long` setup of `ttx`, the help text, and the exit-code set |

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
a running tool with `Fugu::Process->terminate`, in its process-group form”.
The process-group option comes from Fugu plan 006. HRN-PERL also needs a fixed `%ENV`
before each exec, and the `env` argument comes from
`/home/user/Fugu/plans/002-process-child-environment/plan.md`.

The list is closed under the load relation.
`Fugu::CLI` loads `Fugu::Log`. `Fugu::File` loads `Fugu::Log`. `Fugu::Process` loads
`Fugu::CLI`, for the `EXIT_ERROR` constant.
The list holds each of those modules, so the harness loads no module outside the list.

## The arguments for

1. **The port dependency set does not grow.** HRN-PKG reads: “The port lists llama.cpp
   and p5-Fugu as run dependencies, with a minimum Fugu version”.
   D7 reads: “The port dependencies are llama.cpp and p5-Fugu, and no other.”
   The p5-Fugu package already reaches the target, so the list adds no port dependency.

2. **The target installs nothing from CPAN.** Fugu loads with core Perl only, and
   `t/fugu/coreperl.t` proves the load contract.
   Every CPAN use in Fugu is a lazy `require` behind an optional feature, and no module
   of the list is such a feature.
   The list needs these base modules only: `Config`, `Encode`, `Exporter`, `Fcntl`,
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

5. **The adoption deletes no code.** Every HRN unit is `open` in the register, and the
   harness holds no code today.
   The list therefore costs no rework, and it removes work from each unit of the
   consumers table.

6. **A test can prove the sandbox off OpenBSD.** `Fugu::Sandbox` is real on OpenBSD, and
   it is a successful no-op elsewhere.
   `is_supported` reports which of the two the caller gets, so a test can tell
   enforcement from emulation.
   REP-CI reads: “The harness reaches pledge(2) and unveil(2) through `Fugu::Sandbox`,
   which restricts nothing off OpenBSD and returns success, so `perl -c` and `prove` run
   on any runner.”

## The arguments against

1. **The harness gains a version dependency on a sibling project.** HRN-REPL-1 needs “a
   minimum version” of the p5-Fugu package.
   That minimum version covers seven modules and not one.
   Three rows of the module table wait on a Fugu plan, and each plan is a proposal
   today. The `Fugu::REPL` row waits on Fugu plan 001, because the module does not exist
   today. The `Fugu::Log` row waits on plan 005, and the `Fugu::Process` row waits on
   plans 002 and 006. A Fugu release therefore gates a harness feature.

2. **A Fugu defect reaches the harness.** The parent holds the `proc exec` promise, and
   the model process parses hostile model output.
   A defect in a shared module then sits inside a security boundary.
   The Fugu tests are the callers of record of the library, and the harness is not one
   of them. No Fugu test runs under `perl -T` today, and HRN-PERL requires taint mode for
   every program of the harness.

3. **The CI import check holds a list to maintain.** REP-CI holds a seven-name rule.
   The check and D7 must agree, and a drift between them is silent.
   The list must also stay closed under the load relation.
   A new `use` line inside a Fugu module can widen what the target loads.
   That widening needs no change in this repository.
   A check that reads the import lines of `harness/` alone does not see it.

4. **Four modules stay excluded, so the harness still writes four facilities.**
   `Fugu::Daemon`, `Fugu::EventLoop`, `Fugu::Imsg` and `Fugu::Control` are not on the
   list. The harness therefore writes its own daemon start, its own select loop, its own
   frame codec and its own control socket.
   HRN-PROC keeps the fork and exec of its own program, and the descriptor flag before
   the exec. HRN-LANG keeps the length-prefixed `JSON::PP` record over `socketpair(2)`.
   `Protocol::Imsg` ships in the same distribution and is not on the list, so that
   framing stays in the harness.
   HRN-SOCKET keeps the `SO_PEERCRED` read, and HRN-CONFIRM-6 depends on it.
   Two Fugu plans hold that ground:
   `/home/user/Fugu/plans/005-pledged-daemon-corrections/plan.md` and
   `/home/user/Fugu/plans/006-privilege-separated-children/plan.md`. The list reaches
   one half of each plan only.
   It holds `Fugu::Log`, so the syslog pin of plan 005 is reachable.
   It holds `Fugu::Process`, so the process-group `terminate` of plan 006 is reachable.
   It holds no `Fugu::Privdrop`, so the privilege-drop half of plan 005 stays
   unreachable. It holds no `Fugu::Control`, so the control socket of plan 006 stays
   unreachable. HRN-PROC keeps its own fork and exec, so `spawn_peer` and the `inherit`
   list of plan 006 stay unreachable too.

5. **The privilege drop stays in the harness.** The list holds no `Fugu::Privdrop`, and
   HRN-SAFE-DROP needs the drop order and the verification of each id after the drop.
   The harness therefore writes that code, and Fugu plan 005 corrects the same fault
   inside `Fugu::Privdrop` for its other callers.
   The second open question of the section below names that module.

6. **One row of the list is weak today.** `Fugu::Config` serves a configuration read,
   and no unit defines a configuration file of the harness.
   The grammar of the module is `key value` or `key = value`, with `#` comments.
   The frontmatter of HRN-SKILLS is `key: value`, so `Fugu::Config` must not read a
   `SKILL.md` file. The value of the row is a future `/etc/ttx` configuration file, which
   then needs no new parser.

## What the approval settled

The approval settles these facts:

- D7 holds the allow-list of seven modules, and the list lives in D7 alone.
- The harness must not load an other module of the distribution.
- REP-CI holds the dependency check.
  REP-TOOLS and HRN-LANG name the same rule, and each one points at D7 for the names.
- A unit of the consumers table names its module and its methods.
  D7 names the list, and no unit repeats the list.
- The register keeps every HRN unit `open`, so the approval changes no code in this
  repository.
- Fugu gains a reachable consumer for plan 002, for the `Fugu::Log` half of plan 005,
  and for the process-group `terminate` of plan 006.

Two questions stay open.

1. **Does `Fugu::Config` earn a configuration file for the harness?** HRN-PKG names the
   configuration directory `/etc/ttx`, and no unit defines a file in it.
   The module holds the OpenBSD grammar, so a file needs no new parser.
   A file also needs its own unit, its settings and its defaults.
   Until that unit exists, the harness holds each setting as a constant of the program.
2. **Does the harness need a module outside the list?** Two candidates stand.
   `Fugu::Privdrop` would serve HRN-SAFE-DROP, which needs the drop order and the
   verification of each id after the drop.
   `Fugu::Control` and `Protocol::Imsg` would serve HRN-SOCKET and HRN-LANG. HRN-LANG
   states the reason for the harness code: “Base Perl has no `imsg_init(3)` interface.”
   Each candidate needs its own proposal to D7, and a human must approve it.

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

One `dist` line installs the whole distribution, so no module of the list needs a line
of its own. `deps/Linux.txt` and `deps/Darwin.txt` each hold that line for the Fugu
distribution, and one `bin` line for the Scaleway CLI. `scripts/deps` installs the
tarball with cpanm. REP-CI reads: “CI installs the Fugu distribution through
`scripts/deps`, so `prove` runs with the real modules”.

## Files

The specification holds the list, so no document under `spec/` changes.
The adoption writes the harness tree of the REP-LAYOUT block, and it writes the check
that guards the list.

| File | Change |
| --- | --- |
| `harness/bin/ttx` | The client. It loads `Fugu::CLI` for the command line, `Fugu::REPL` for the operator session, and `Fugu::Sandbox` for the pledge and the unveil |
| `harness/sbin/ttxd` | The daemon. It loads `Fugu::Sandbox`, `Fugu::Log`, `Fugu::Process`, `Fugu::File`, `Fugu::Config` and `Fugu::CLI` before it pledges |
| `harness/lib/TTX/Sandbox.pm` | The pledge set and the unveil enumeration of each process, over `Fugu::Sandbox` |
| `harness/lib/TTX/Tools.pm` | Each tool call, over `Fugu::Process`, and each candidate install, over `Fugu::File` |
| `harness/lib/TTX/Audit.pm` | The transcript and its syslog duplicate, over `Fugu::File` and `Fugu::Log` |
| `harness/lib/TTX/Agent.pm`, `harness/lib/TTX/LLM.pm` | No module of the list. The loop and the model client hold base modules only |
| `harness/t/` | One test loads each module of the list before the pledge, under `perl -T`. One test proves the closure of the list |
| `harness/port/` | The port names p5-Fugu as a run dependency, with a minimum version |
| `scripts/` | The dependency check holds the list of D7, and it refuses each other module of the distribution |
| `.github/workflows/check-code.yml` | The workflow runs `perl -c`, `prove`, the taint check, the dependency check and the execution-discipline check |
| `Makefile` | The `harness-test` target runs `prove` over `harness/t/` |

When the harness code lands, the same change sets the state of each implemented unit in
`spec/STATUS.md`.

## Tests

This plan adds no code, so it adds no test.

The CI checks of REP-CI hold these rules:

- The dependency check must accept each module of the list, and it must fail on every
  other module of the distribution.
- The check must fail when the list of the check and the list of D7 disagree.
- A harness test must run under `perl -T`, and it must load each module of the list
  before the pledge.
- A harness test must prove that each module of the list loads no module outside the
  list.
- A test can call `Fugu::Sandbox->is_supported` to tell enforcement from emulation.

Fugu holds the unit test of each module.
Fugu needs one taint-mode test before the harness loads the list, because no Fugu test
runs under `perl -T` today.

## Acceptance

- `make check` passes in this repository: `uv lock --check`, `ruff format --check`,
  `ruff check`, `flowmark --check` and `make spec-check`.
- D7 holds the seven module names, and no other document under `spec/` enumerates them.
- REP-CI, REP-TOOLS and HRN-LANG each point at D7 for the list.
- `deps/Linux.txt` and `deps/Darwin.txt` each hold the `dist` line of the Fugu
  distribution.
- Each unit that the module table cites exists in `harness.md`, and each cited rule
  exists in its unit.
- Every HRN unit is `open` in `spec/STATUS.md`.

## Open questions

1. **Does taint mode hold across the list?** No Fugu test runs under `perl -T` today.
   A taint defect in a shared module reaches every program of the harness, so the proof
   must exist before the harness loads the list.
2. **How does the check stay closed?** A new `use` line inside a Fugu module can widen
   what the target loads.
   A test in Fugu, or a check in this repository, must prove the closure of the list.
3. **Which minimum p5-Fugu version does the port name?** Fugu derives its version from
   its latest `v*` tag.
   The minimum version must cover each module of the list.
   It must also cover the `env` argument of HRN-PERL, the native syslog pin of
   HRN-SAFE-AUDIT, and the process-group form of HRN-CANCEL.
