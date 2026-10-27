# Harness REPL

This document is a part of the [harness](harness.md) specification.

<a id="hrn-repl"></a>

## The operator REPL

The interactive session of `ttx` is a REPL. `Fugu::REPL`, a module of the
sibling Fugu repository, supplies the line editor. FuguPass builds its interface
on the same module, so the interactive behavior stays uniform across the FuguBSD
tools.

- **HRN-REPL-1** — The client reads operator input through the `Fugu::REPL`
  module of the installed Fugu distribution. On the target, the port installs
  the p5-Fugu package as a run dependency, with a minimum version
  ([HRN-PKG](harness-safety.md#hrn-pkg)). The client loads the module before it
  pledges.
- **HRN-REPL-2** — The module must load with base modules only, and it must
  stand alone: it must not load an other Fugu module. The whole editor must fit
  inside the client pledge, and a one-module closure keeps that proof small. It
  must operate inside the `stdio tty` promises of the client pledge: no file
  access, no process creation, and no network access of its own.
- **HRN-REPL-3** — An input line that starts with `/` is a client command from a
  fixed command table. Every other line is a step prompt for the daemon. The
  module generates `/help` from the table, and `/quit` ends the session.
- **HRN-REPL-4** — History lives in memory, for the session only. The client
  must not write a history file.
- **HRN-REPL-5** — While a step runs, the client waits on the control socket and
  shows the liveness events ([HRN-LIVE](harness-loop.md#hrn-live)). An operator
  interrupt during a step sends a cancel
  ([HRN-CANCEL](harness-loop.md#hrn-cancel)). An interrupt at the prompt only
  clears the line.
- **HRN-REPL-6** — A confirmation is an explicit yes/no prompt of the module,
  with the default no. An end of file or an interrupt answers no. On a yes, the
  client builds the confirmation message of [HRN-CONFIRM](#hrn-confirm).
- **HRN-REPL-7** — Every byte from the daemon passes the display filter of the
  module before display. The filter applies the rules of
  [HRN-SAFE-DISPLAY](harness-safety.md#hrn-safe-display).
- **HRN-REPL-8** — At the prompt, the module must watch the control socket as a
  registered handle. A daemon disconnect ends the prompt read, and the client
  reports the disconnect and exits.
- **HRN-REPL-9** — When standard input is not a terminal, the module must read
  plain lines, with no line editing and no escape output. The test suites drive
  the client in this mode.
- **HRN-REPL-10** — The module must not read a terminfo file. It must use a
  fixed escape-sequence set, because the client pledge gives no file access.
- **HRN-REPL-11** — The interface contract of the module is the `.pod` sidecar
  of the module in the Fugu repository. FuguPass PROG-IFACE and PROG-REPL cite
  the same contract, so a change to it coordinates with FuguPass through Fugu.

The module holds the terminal in raw mode only while it reads a line. It
restores the terminal state before command dispatch and on every exit path. The
editor implements a fixed emacs-style key subset over the core `POSIX` termios
interface, with tab completion from a callback.

<a id="hrn-confirm"></a>

## Confirmation protocol

The dry-run gate is a protocol, not a prompt. These rules define it:

- **HRN-CONFIRM-1** — The parent gives each pending mutation an action
  identifier.
- **HRN-CONFIRM-2** — The parent computes a SHA-256 digest with `Digest::SHA`.
  The digest covers the action identifier, the exact argument vector, the
  candidate file content, and the dry-run output.
- **HRN-CONFIRM-3** — The client shows the dry-run output and the diff to the
  operator.
- **HRN-CONFIRM-4** — A confirmation message must carry the action identifier
  and the digest.
- **HRN-CONFIRM-5** — A confirmation with a stale identifier or a wrong digest
  fails closed.
- **HRN-CONFIRM-6** — A confirmation must come from the same peer user id that
  saw the dry run. This rule depends on the control socket
  ([HRN-SOCKET](harness.md#hrn-socket)).
- **HRN-CONFIRM-7** — A pending mutation has a timeout. After the timeout, it
  fails closed.
- **HRN-CONFIRM-8** — When a session disconnects, its pending mutations die.
- **HRN-CONFIRM-9** — The parent holds the candidate content in memory. Before
  it installs the file, it verifies the content against the digest. It installs
  the file with `Fugu::File->write_atomic`, which writes a temporary sibling and
  renames it over the target. The rename is atomic, so a crash cannot leave a
  truncated target.
- **HRN-CONFIRM-10** — The candidate directory has mode 0700 and owner `_ttx`.
  The parent checks the directory with `Fugu::File->ensure_dir`, which refuses a
  symlink. Only the parent holds an unveil of the candidate directory, so no
  other process can rewrite a candidate between the confirmation and the
  install.

The digest binds the confirmation to what the system does, not only to what the
operator saw. A confirmation therefore applies only to the exact action that the
operator saw. No pending action outlives its session. The daemon serves one
session at a time, so a stalled confirmation must not block the daemon. The
timeout of HRN-CONFIRM-7 releases it.
