# Harness

Four more documents specify the harness: the [operator REPL](harness-repl.md),
the [tools](harness-tools.md), the [agent loop](harness-loop.md), and the
[safety design](harness-safety.md).

<a id="hrn-split"></a>

The harness is the Perl software that operates the tool loop of the TTX agent on
OpenBSD. Only the harness executes commands. The model only proposes.

The harness has two programs, in the pattern of `smtpd(8)`/`smtpctl(8)` and
`vmd(8)`/`vmctl(8)`:

- **`ttxd`** is the daemon. It runs as the dedicated unprivileged user `_ttx`.
  It holds the tool policy, and it executes all commands.
- **`ttx`** is the client: the command line and the operator REPL
  ([HRN-REPL](harness-repl.md#hrn-repl)). The operator runs it under a normal
  user account. It speaks to `ttxd` over a local control socket. It executes
  nothing.

This split gives privilege separation in two directions. The model can reach
`doas` only through the fixed protocol of the executor. The operator account
holds no doas rules, and it cannot run the privileged commands directly.

The `ttx` command line comes from `Fugu::CLI`. It takes the subcommand dispatch,
the option parsing, the help text, and the shared exit codes 0, 1, 2, 3 and 7.
An exit code that belongs to FuguTTX starts above those.

<a id="hrn-lang"></a>

## Language constraint

The harness body is Perl 5 from OpenBSD base. The doas target wrappers are C,
against libc alone (see [Safety design](harness-safety.md#safety-design)).
Decision [D7](DECISIONS.md) sets the rule: Perl on the unprivileged side of
doas, C on the privileged side. The C never faces the model. The Perl never runs
as root.

The Perl harness uses the modules from base. It uses `HTTP::Tiny` for the local
llama-server API, and `JSON::PP` for tool-call parsing. It uses `Digest::SHA`
for the confirmation digest, and `Socket` for the control socket. Three more
base modules arrive through a Fugu module. `Fugu::Sandbox` calls
`OpenBSD::Pledge(3p)` and `OpenBSD::Unveil(3p)` for the sandbox
([HRN-SAFE-PLEDGE](harness-safety.md#hrn-safe-pledge)). `Fugu::Log` calls
`Sys::Syslog` for the audit duplicate
([HRN-SAFE-AUDIT](harness-safety.md#hrn-safe-audit)). The Fugu modules come from
outside base, from the installed Fugu distribution, and each one loads with base
modules only (Fugu ARC-COREPERL). The optional-feature rule of
[D7](DECISIONS.md#d7) bounds each load. A loaded module gains no right: the
pledge set and the unveil list of its process bound what it can do
([HRN-SAFE-PLEDGE](harness-safety.md#hrn-safe-pledge)). The client reads
operator input through `Fugu::REPL` ([HRN-REPL](harness-repl.md#hrn-repl)).

**No CPAN install on the target is a hard constraint. A CI check enforces the
import rule: a base module, or a module of the Fugu distribution, and no other
([D7](DECISIONS.md#d7)).** The OpenBSD package tools are Perl, written against
base alone. The harness follows the same discipline in its own code. The C
wrappers compile with the base toolchain, so they add no port dependency. Two
port dependencies exist: llama.cpp and p5-Fugu.

Base Perl has no `imsg_init(3)` interface. The harness frames each internal
message as a length-prefixed `JSON::PP` record over `socketpair(2)`. A
length-prefixed frame in Perl is memory-safe by construction. A framing defect
in the harness code raises an exception. It does not corrupt the heap.

The Fugu distribution holds `Protocol::Imsg`, a core-Perl imsg(3) frame codec.
The codec reports a framing failure through `$!` and a return value, and not
through an exception. The harness needs the exception discipline above, so it
keeps its own frame code.

<a id="hrn-perl"></a>

### Perl execution discipline

Perl can reach a shell through some call forms. One such call with
model-influenced data defeats the architecture. These rules are normative, and
the CI check enforces them:

- Use the list form of `system` and `exec`. Do not use the single-string form.
- Use three-argument `open`. Do not use two-argument `open`, and do not use
  backticks.
- Run every program under taint mode (`perl -T`).
- Reduce `%ENV` to a fixed safe set before any `exec`. The fixed set comes from
  the `env` argument of `Fugu::Process`. That argument must exist in the
  installed distribution, and the minimum version of
  [HRN-PKG](harness-safety.md#hrn-pkg) covers it.
- Load and exercise every module before the process pledges. A lazy `require`
  after `pledge(2)` needs `rpath`. Its absence kills the process with `SIGABRT`.
  A compile-time load is not enough. Some Fugu methods run a lazy `require` at
  call time, so the harness must not reach one after the pledge call.

<a id="hrn-arch"></a>

## Architecture

`llama-server` (from the `misc/llama.cpp` port) serves the TTX model over an
OpenAI-compatible HTTP API on `127.0.0.1`. `ttxd` operates a perceive → plan →
act → observe loop against it. Together they make the TTX agent: the model
proposes, the harness decides and executes.

`llama-server` constrains tool calls at sample time with its JSON-schema/grammar
support. So model output is parseable by construction. `JSON::PP` validates it
again, under a fixed nesting depth (`max_depth`) and a fixed size (`max_size`).
The internal record has a fixed maximum length. The HTTP client has a fixed
timeout. Each step has a fixed budget of turns. A malformed call gets one
re-prompt. Then the step stops. The [agent loop](harness-loop.md#the-agent-loop)
section defines the loop, and the
[failure budgets](harness-loop.md#failure-budgets) table defines every recovery
path. The loop design follows the
[harness-loop research](../docs/research/harness-loops/index.md).

Three system users divide the components:

| User                 | Runs           | Holds                                                        |
| -------------------- | -------------- | ------------------------------------------------------------ |
| `_ttx`               | `ttxd`         | The doas rules, the session transcripts, the control socket. |
| `_ttxllm`            | `llama-server` | Nothing: no doas rules, no socket, no log.                   |
| The operator account | `ttx`          | Control-socket access, through the `ttxop` group.            |

`llama-server` is the largest compiled program in the system, so it must not run
as `_ttx`. A compromised `llama-server` holds no rights. It can only lie in its
HTTP responses, and the model process parses those under a minimal pledge.

The daemon serves one interactive session at a time, synchronously. Base Perl
has no event library, and this design does not need one.

<a id="hrn-proc"></a>

## The three processes of ttxd

`ttxd` follows the OpenBSD daemon pattern: a parent and unprivileged children,
connected by socket pairs. One rule controls the design: **the process that
parses untrusted input must not hold `exec`**. Model output is untrusted input.

| Process          | Role                                   | pledge, after setup                 | unveil                                                                                                                                                                                                                                                           |
| ---------------- | -------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Parent (engine)  | Policy, tool execution, audit          | `stdio rpath wpath cpath proc exec` | the diagnostic binaries (x), the doas wrappers (x), `/usr/bin/doas` (x), `/usr/bin/diff` (x), the candidate directory (rwc), the `ttxd` binary (x), `/var/log/ttx` (rwc), `/etc` (r), `/usr/share/man` (r), the perl library directories (r), `/dev/urandom` (r) |
| Model process    | HTTP to llama-server, JSON parsing     | `stdio`                             | nothing                                                                                                                                                                                                                                                          |
| Frontend process | Control socket, session, confirmations | `stdio unix`                        | the socket path                                                                                                                                                                                                                                                  |

- **The parent** holds the tool policy, executes each command, and writes the
  session transcript (see
  [session transcript](harness-loop.md#session-transcript)). It never sees raw
  model output. It parses only the fixed internal record format, which the
  harness itself defines. The unveil row is a complete enumeration. It names
  each diagnostic binary the parent can run without doas, the doas wrappers, and
  `diff(1)`. It also names the candidate directory it writes, the log directory,
  and the `ttxd` binary it re-executes to respawn a child. The enumeration takes
  the perl library directories from `Fugu::Sandbox->perl_lib_dirs`. It takes the
  read-only system inventory from `Fugu::Sandbox->system_paths`, and `/etc`
  already covers each entry of that inventory except `/dev/urandom`. The parent
  execs its own program to start each child, so each child needs the library
  directories of the perl that runs. The paths of the harness itself stay in the
  harness: the diagnostic binaries, the doas wrappers, the candidate directory
  and the log directory. The parent builds each diff of
  [HRN-TOOL-GATE-1](harness-tools.md#hrn-tool-gate) with base `diff(1)`, so the
  enumeration holds that binary. The candidate directory is not `/etc`, because
  `/etc` is read-only to the parent.
- **The model process** speaks HTTP to `llama-server` and parses model output
  with `JSON::PP`. It reduces each valid tool call to a fixed internal record
  for the parent. It opens one persistent HTTP/1.1 connection to `127.0.0.1`
  during setup, and it then pledges `stdio` only. It holds no `inet` promise
  after setup, because `pledge(2)` cannot restrict a destination address. The
  one process that parses hostile model output must not reach the network.
  `HTTP::Tiny` opens a socket for each request, so the model process must not
  use it after the pledge. The model process speaks HTTP/1.1 over the one
  persistent connection itself. When the connection ends, the model process
  exits, and the parent respawns it. The parent treats an abnormal child exit as
  the respawn trigger. The model process has no file system view and no `exec`.
  An exploited parser bug lands in a process that can do nothing and can reach
  nothing. The model process appends each raw request and each raw response to
  the wire log. It writes through a descriptor that it inherits from the parent
  (see [session transcript](harness-loop.md#session-transcript)).
- **The frontend process** owns the control socket and the operator session. It
  relays prompts, output, liveness events, and confirmations between the client
  and the parent (see [Liveness](harness-loop.md#liveness)).

The parent starts each child with fork and exec of its own program, with a role
flag. Each child therefore gets a fresh address-space layout.

Base Perl cannot pass a file descriptor over a socket. The core `Socket` module
wraps neither `sendmsg(2)` nor `recvmsg(2)`, so `SCM_RIGHTS` is not expressible
in base Perl. The harness therefore does not pass descriptors. The parent
creates each `socketpair(2)` before the fork, and the child inherits its end
across `exec`. Perl sets close-on-exec on each descriptor above `$^F`. The
parent must clear `FD_CLOEXEC` on the child end before `exec`, or move the
descriptor below file descriptor 3. No pledge set holds `sendfd` or `recvfd`.
The frontend relays bytes, not descriptors.

The table gives the pledge sets for the agent loop. `ttx fetch` is a standalone
mode with its own, separate pledge set.

The client `ttx` pledges `stdio tty unix` and unveils only the socket path. A
defect in the client is worth nothing.

<a id="hrn-socket"></a>

## Control socket

`ttxd` listens on `/var/run/ttxd.sock`. The socket has owner `_ttx`, group
`ttxop`, and mode `0660`. Membership in the `ttxop` group is the operator grant.
For each connection, the frontend reads the peer credentials with
`getsockopt(2)` and `SO_PEERCRED`. On OpenBSD this option returns a
`struct sockpeercred`, which holds the user id, then the group id, then the
process id. Base Perl reads it with `getsockopt` and `unpack`, so no compiled
module is necessary. The field order differs from the Linux `struct ucred`, so
do not copy a Linux example. The session transcript attributes each session and
each confirmation to that user id.
