# 001 — The Fugu modules of the harness

## Status

Approved, and applied in the specification. The remaining work is the harness
code, and each harness slice holds its own plan. This plan maps decision
[D7](../../spec/DECISIONS.md#d7) onto the units that adopt a Fugu module, per
the [plan contract](../../spec/index.md#plan-contract). It holds no slice, and
it states no measurement. Nothing in this plan waits on the Fugu repository: the
installed distribution holds each module and each method that the map names.

## Purpose

D7 permits any module of the Fugu distribution in the harness body. This plan is
the adoption map. It names the unit that each adopted module serves, the methods
that each unit needs, and the code that the harness does not write.

The harness holds no code, so the adoption starts from an empty tree. The
walking skeleton of `ROADMAP.md` takes `Fugu::Process` for the read-only tools
and the gated mutations. It takes `Fugu::File` for the candidate install of
HRN-CONFIRM-9. A later slice takes each other row of the map. Every HRN unit is
`open` in `STATUS.md`.

## Constraints that shape the adoption

- **The target installs nothing from CPAN.** D7 reads: "The harness must not
  depend on an optional CPAN feature of a Fugu module." REP-CI names the checks
  that enforce it.
- **Each module loads and runs before the pledge.** HRN-PERL reads: "Load and
  exercise every module before the process pledges." Some Fugu methods run a
  lazy `require` at call time, so the harness must not reach one after the
  pledge call.
- **The parent pledge holds no `unix` promise.** HRN-SAFE-AUDIT depends on the
  native log method of `Fugu::Log` (`setlogsock('native')`).
- **`Fugu::REPL` must stand alone.** HRN-REPL-2 holds that rule.
- **Each program runs under taint mode.** HRN-PERL sets the rule, and REP-CI
  runs the check.

## The adoption map

Each cell of the last column names the code that the harness does not write,
because the module of the row holds it.

| Module          | Unit and rules                                                                                                                                 | Methods                                                                                                                                                                                | What the module removes from the harness                                                                                                                                                                                                      |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Fugu::REPL`    | `HRN-REPL`; HRN-REPL-1 to HRN-REPL-11                                                                                                          | `new`, `read_line`, `event`, `ready_handle`, `confirm`, `display_filter`, `show`, `help_text`, `history`, `is_interactive`, `restore`                                                  | The line editor, its key table and its display filter (Fugu LIB-REPL)                                                                                                                                                                         |
| `Fugu::Sandbox` | `HRN-SAFE-PLEDGE` and `HRN-PROC`; neither unit holds a numbered rule                                                                           | `is_supported`, `pledge`, `unveil`, `unveil_lock`, `perl_lib_dirs`, `system_paths`                                                                                                     | The `OpenBSD::Pledge` and `OpenBSD::Unveil` calls. Also the enumeration of the library directories of the perl that runs, and of the resolver files                                                                                           |
| `Fugu::Log`     | `HRN-SAFE-AUDIT`; the unit holds prose, and it holds no numbered rule                                                                          | `new` with `mode`, `level`, `ident` and `facility`; `debug`, `info`, `notice`, `warning`, `error`; `set_level`; `reopen`; `default`; `set_default`                                     | The `Sys::Syslog` calls, the native log pin, and the level filter                                                                                                                                                                             |
| `Fugu::Process` | `HRN-TOOL-RO`, HRN-TOOL-RO-1 to HRN-TOOL-RO-4; `HRN-TOOL-GATE`, HRN-TOOL-GATE-1 to HRN-TOOL-GATE-5; `HRN-CANCEL`, which holds no numbered rule | `run` with `cmd`, `env`, `timeout`, `stdin`, `cwd`, `passthrough` and the new session; `spawn_command`; `exit_code`; `is_alive`; `terminate` with `grace_period` and the process group | The fork and the exec, the fixed child environment, the reader of two descriptors, the timeout, and the decode of the wait status                                                                                                             |
| `Fugu::Config`  | `HRN-PKG`; the unit holds prose, and it holds no numbered rule                                                                                 | `new` with `file`; `load`; `get`; `setting_names`; `parse_bool`; `blocks`; `block`; `error`                                                                                            | The parser of a configuration file. HRN-PKG names the configuration directory `/etc/ttx`, and no unit defines a configuration file today                                                                                                      |
| `Fugu::File`    | `HRN-CONFIRM`, HRN-CONFIRM-9 and HRN-CONFIRM-10; `HRN-SKILLS`, which holds no numbered rule                                                    | `read`, `write` with `mode`, `write_atomic` with `mode`, `ensure_dir` with `mode`, `valid_name`                                                                                        | The temporary file and the rename. `ensure_dir` refuses a symlink, and `valid_name` refuses an unsafe path component. The harness keeps the mode and owner check of the candidate directory, and the character set and length of a skill name |
| `Fugu::CLI`     | `HRN-SPLIT` and `HRN-FETCH`; neither unit holds a numbered rule                                                                                | `new` with `commands`, `name`, `options`, `usage`, `epilogue` and `log`; `run`; `option`; `command`; `print_help`; `usage_error`; the exit codes 0, 1, 2, 3 and 7                      | The `Getopt::Long` setup of `ttx`, the help text, and the exit-code set                                                                                                                                                                       |

Three notes belong to the map.

`Fugu::Sandbox->perl_lib_dirs` and `Fugu::Sandbox->system_paths` serve the
unveil enumeration of HRN-PROC. The parent execs its own program to start each
child, so the child needs the library directories of the perl that runs. Neither
method calls a syscall, so a test can prove the enumeration off OpenBSD. The
paths of the harness itself stay in the harness: the diagnostic binaries, the
doas wrappers, the candidate directory and the log directory.

The map is not a bound. D7 permits any module of the distribution, so a slice
can adopt an other module when a unit needs it. The harness keeps its own frame
code (HRN-LANG) and its own privilege drop (HRN-SAFE-DROP). An adoption of
`Fugu::Control`, `Protocol::Imsg` or `Fugu::Privdrop` needs a change to those
units first.

The interface contract of each module is the `.pod` sidecar of the module in the
Fugu repository. HRN-REPL-11 states that rule for `Fugu::REPL`, and FuguPass
CLI-IFACE cites the same contract.

## Files

| File                                                 | Change                                                                                                                                          |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `harness/bin/ttx`                                    | The client. It loads `Fugu::CLI` for the command line, `Fugu::REPL` for the operator session, and `Fugu::Sandbox` for the pledge and the unveil |
| `harness/sbin/ttxd`                                  | The daemon. It loads `Fugu::Sandbox`, `Fugu::Log`, `Fugu::Process`, `Fugu::File`, `Fugu::Config` and `Fugu::CLI` before it pledges              |
| `harness/lib/TTX/Sandbox.pm`                         | The pledge set and the unveil enumeration of each process, over `Fugu::Sandbox`                                                                 |
| `harness/lib/TTX/Tools.pm`                           | Each tool call, over `Fugu::Process`, and each candidate install, over `Fugu::File`                                                             |
| `harness/lib/TTX/Audit.pm`                           | The transcript and its syslog duplicate, over `Fugu::File` and `Fugu::Log`                                                                      |
| `harness/lib/TTX/Agent.pm`, `harness/lib/TTX/LLM.pm` | No Fugu module. The loop and the model client hold base modules only                                                                            |
| `harness/t/`                                         | One test loads each adopted module before the pledge, under `perl -T`                                                                           |
| `harness/port/`                                      | The port names p5-Fugu as a run dependency, with a minimum version                                                                              |
| `scripts/`                                           | The dependency check reads the manifest of the installed distribution (REP-CI)                                                                  |
| `.github/workflows/check.yml`                        | The workflow runs `perl -c`, `prove`, the taint check, the dependency check and the execution-discipline check                                  |
| `GNUmakefile`                                        | The `harness-test` target runs `prove` over `harness/t/`                                                                                        |

When the harness code lands, the same change sets the state of each implemented
unit in `spec/STATUS.md`.

## Tests

This plan adds no code, so it adds no test.

The CI checks of REP-CI hold these rules:

- The dependency check must accept a base-module import and a module that the
  installed Fugu distribution supplies, and it must refuse each other module.
- A harness test must run under `perl -T`, and it must load each adopted module
  before the pledge.
- CI installs no CPAN module beyond the Fugu distribution. A test that reaches
  an optional CPAN feature of a Fugu module fails on the runner.
- A test can call `Fugu::Sandbox->is_supported` to tell enforcement from
  emulation.

## Open questions

1. **Does `Fugu::Config` earn a configuration file for the harness?** HRN-PKG
   names the configuration directory `/etc/ttx`, and no unit defines a file in
   it. The module holds the OpenBSD grammar, so a file needs no new parser.
   Until that unit exists, the harness holds each setting as a constant of the
   program.
2. **Which minimum p5-Fugu version does the port name?** Fugu derives its
   version from its latest `v*` tag. The minimum version must cover each adopted
   module, and the `env` argument of `Fugu::Process`. It must also cover the
   native syslog pin of `Fugu::Log`, and the process-group form of
   `Fugu::Process->terminate` (HRN-PKG).
