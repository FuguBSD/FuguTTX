# Harness

The harness is the Perl software that operates the tool loop of the TTX agent on
OpenBSD. Only the harness executes commands.
The model only proposes.

The harness has two programs, in the pattern of `smtpd(8)`/`smtpctl(8)` and
`vmd(8)`/`vmctl(8)`:

- **`ttxd`** is the daemon.
  It runs as the dedicated unprivileged user `_ttx`. It holds the tool policy, and it
  executes all commands.
- **`ttx`** is the client: the command line and the TUI. The operator runs it under a
  normal user account.
  It speaks to `ttxd` over a local control socket.
  It executes nothing.

This split gives privilege separation in two directions.
The model can reach `doas` only through the fixed protocol of the executor.
The operator account holds no doas rules, and it cannot run the privileged commands
directly.

## Language constraint

The harness body is Perl 5 from OpenBSD base.
The doas target wrappers are C, against libc alone (see [Safety design](#safety-design)).
Decision [D7](decisions.md) sets the rule: Perl on the unprivileged side of doas, C on
the privileged side.
The C never faces the model.
The Perl never runs as root.

The Perl harness uses only modules from base: `OpenBSD::Pledge(3p)` and
`OpenBSD::Unveil(3p)` for the sandbox, `HTTP::Tiny` for the local llama-server API,
`JSON::PP` for tool-call parsing, `Digest::SHA` for the confirmation digest,
`Sys::Syslog` for the audit duplicate, and `Socket` for the control socket.

**Zero CPAN dependencies is a hard constraint.
A CI check enforces it.** The OpenBSD package tools are Perl, written against base
alone. The harness follows the same discipline.
The C wrappers compile with the base toolchain, so they add no port dependency.
No port dependency exists, other than llama.cpp.

Base Perl has no `imsg_init(3)` interface.
The harness frames each internal message as a length-prefixed `JSON::PP` record over
`socketpair(2)`. A length-prefixed frame in Perl is memory-safe by construction.
A framing defect raises an exception.
It does not corrupt the heap.

### Perl execution discipline

Perl can reach a shell through some call forms.
One such call with model-influenced data defeats the architecture.
These rules are normative, and the CI check enforces them:

- Use the list form of `system` and `exec`. Do not use the single-string form.
- Use three-argument `open`. Do not use two-argument `open`, and do not use backticks.
- Run every program under taint mode (`perl -T`).
- Reduce `%ENV` to a fixed safe set before any `exec`.
- Load and exercise every module before the process pledges. A lazy `require` after
  `pledge(2)` needs `rpath`. Its absence kills the process with `SIGABRT`.

## Architecture

`llama-server` (from the `misc/llama.cpp` port) serves the TTX model over an
OpenAI-compatible HTTP API on `127.0.0.1`. `ttxd` operates a perceive → plan → act →
observe loop against it.
Together they make the TTX agent: the model proposes, the harness decides and executes.

`llama-server` constrains tool calls at sample time with its JSON-schema/grammar
support. Thus model output is parseable by construction.
`JSON::PP` validates it again, under a fixed nesting depth (`max_depth`) and a fixed
size (`max_size`). The internal record has a fixed maximum length.
The HTTP client has a fixed timeout.
Each prompt has a fixed budget of tool calls.
A malformed call gets one re-prompt.
Then the step stops.

Three system users divide the components:

| User | Runs | Holds |
| --- | --- | --- |
| `_ttx` | `ttxd` | The doas rules, the audit log, the control socket. |
| `_ttxllm` | `llama-server` | Nothing: no doas rules, no socket, no log. |
| The operator account | `ttx` | Control-socket access, through the `ttxop` group. |

`llama-server` is the largest compiled program in the system, so it must not run as
`_ttx`. A compromised `llama-server` holds no rights.
It can only lie in its HTTP responses, and the model process parses those under a
minimal pledge.

The daemon serves one interactive session at a time, synchronously.
Base Perl has no event library, and this design does not need one.

## The three processes of ttxd

`ttxd` follows the OpenBSD daemon pattern: a parent and unprivileged children, connected
by socket pairs. One rule controls the design: **the process that parses untrusted input
must not hold `exec`**. Model output is untrusted input.

| Process | Role | pledge, after setup | unveil |
| --- | --- | --- | --- |
| Parent (engine) | Policy, tool execution, audit | `stdio rpath wpath cpath proc exec` | the diagnostic binaries (x), the doas wrappers (x), `/usr/bin/doas` (x), the candidate directory (rwc), the `ttxd` binary (x), the audit log (w), `/etc` (r) |
| Model process | HTTP to llama-server, JSON parsing | `stdio` | nothing |
| Frontend process | Control socket, session, confirmations | `stdio unix` | the socket path |

- **The parent** holds the tool policy, executes each command, and writes the audit log.
  It never sees raw model output.
  It parses only the fixed internal record format, which the harness itself defines.
  The unveil row is a complete enumeration: it names each diagnostic binary the parent
  can run without doas, the doas wrappers, the candidate directory it writes, and the
  `ttxd` binary it re-executes to respawn a child. The candidate directory is not
  `/etc`, because `/etc` is read-only to the parent.
- **The model process** speaks HTTP to `llama-server` and parses model output with
  `JSON::PP`. It reduces each valid tool call to a fixed internal record for the parent.
  It opens one persistent HTTP/1.1 connection to `127.0.0.1` during setup, and it then
  pledges `stdio` only. It holds no `inet` promise after setup, because `pledge(2)`
  cannot restrict a destination address, and the one process that parses hostile model
  output must not reach the network. `HTTP::Tiny` opens a socket for each request, so the
  model process must not use it after the pledge; it speaks HTTP/1.1 over the one
  persistent connection itself. When the connection ends, the model process exits, and
  the parent respawns it. The parent treats an abnormal child exit as the respawn
  trigger. The model process has no file system view and no `exec`. An exploited parser
  bug lands in a process that can do nothing and can reach nothing.
- **The frontend process** owns the control socket and the operator session.
  It relays prompts, streamed output, and confirmations between the client and the
  parent.

The parent starts each child with fork and exec of its own program, with a role flag.
Each child thus gets a fresh address-space layout.

Base Perl cannot pass a file descriptor over a socket.
The core `Socket` module wraps neither `sendmsg(2)` nor `recvmsg(2)`, so `SCM_RIGHTS` is
not expressible in base Perl.
The harness therefore does not pass descriptors.
The parent creates each `socketpair(2)` before the fork, and the child inherits its end
across `exec`. Perl sets close-on-exec on each descriptor above `$^F`, so the parent must
clear `FD_CLOEXEC` on the child end before `exec`, or move the descriptor below file
descriptor 3. No pledge set holds `sendfd` or `recvfd`.
The frontend relays bytes, not descriptors.

The table gives the pledge sets for the agent loop.
`ttx fetch` is a standalone mode with its own, separate pledge set.

The client `ttx` pledges `stdio tty unix` and unveils only the socket path.
A defect in the client is worth nothing.

## Control socket

`ttxd` listens on `/var/run/ttxd.sock`. The socket has owner `_ttx`, group `ttxop`, and
mode `0660`. Membership in the `ttxop` group is the operator grant.
For each connection, the frontend reads the peer credentials with `getsockopt(2)` and
`SO_PEERCRED`. On OpenBSD this option returns a `struct sockpeercred`, which holds the
user id, then the group id, then the process id. Base Perl reads it with `getsockopt`
and `unpack`, so no compiled module is necessary. The field order differs from the Linux
`struct ucred`, so do not copy a Linux example. The audit log attributes each session
and each confirmation to that user id.

## Confirmation protocol

The dry-run gate is a protocol, not a prompt:

1. The parent gives each pending mutation an action identifier.
2. The parent computes a SHA-256 digest with `Digest::SHA`. The digest covers the action
   identifier, the exact argument vector, the candidate file content, and the dry-run
   output.
3. The client shows the dry-run output and the diff to the operator.
4. A confirmation message must carry the action identifier and the digest.
5. A confirmation with a stale identifier or a wrong digest fails closed.
6. A confirmation must come from the same peer user id that saw the dry run.
7. A pending mutation has a timeout. After the timeout, it fails closed.
8. When a session disconnects, its pending mutations die.

The digest binds the confirmation to what the system will do, not only to what the
operator saw. The parent holds the candidate content in memory. Before it installs the
file, it verifies the content against the digest. It writes the held bytes to a
temporary file, and it then renames the file into place. The rename is atomic, so a
crash cannot leave a truncated target. The candidate directory has mode 0700 and owner
`_ttx`, and only the parent holds an unveil of it, so no other process can rewrite a
candidate between the confirmation and the install.

A confirmation therefore applies only to the exact action that the operator saw.
No pending action outlives its session.
The daemon serves one session at a time, so a stalled confirmation must not block the
daemon. The timeout of step 7 releases it.

## Tools

Each tool is a function with a JSON schema.

**Read-only tools:**

- Read configuration files under unveiled paths: `/etc/pf.conf`, `/etc/sysctl.conf`,
  `/etc/rc.conf.local`.
- Run diagnostics: `pfctl -s rules|states|info`, `ifconfig`, `netstat`, `sysctl` (read),
  `pkg_info`, `rcctl get|check`, `dmesg`.

The parent runs most read-only tools directly as `_ttx`, with no doas.
`pfctl` is the exception. `pfctl -s` reads `/dev/pf`, which is mode 0600 and owner root.
The `pfctl -s rules|states|info` reads therefore get exact-argument doas rules.
The argument set is finite, so an exact rule is safe here.

**Gated mutations — dry run first, always:**

- Configuration edits: write a candidate file, show the diff, and validate
  (`pfctl -nf pf.conf.candidate`). Install the file only after an explicit confirmation.
- `pkg_add` and `pkg_delete`: run with `-n` first.
  Do the real invocation only after a confirmation.
- `sysctl -w`: record the previous value.
  Apply only after a confirmation.
  Give a rollback option.
- `rcctl enable|start|restart`: apply only after a confirmation.

## Safety design

Safety is first-class, not optional.

- **pledge/unveil, per process.** Each process pledges only the promises of its role,
  and unveils only its own paths.
  The process table above is normative.
  No post-setup pledge holds `inet`. The model process uses `inet` only during setup, to
  open its one connection, and it then drops to `stdio`.
  `proc exec` exists only in the parent.
  A study of these mitigations across 19 OpenBSD releases shows they are practical
  (Ruohonen, Sierszecki & Tiwari, arXiv:2607.03056).

- **doas through fixed-function C wrappers.** A privileged mutation has a dynamic
  argument: an arbitrary package name, a sysctl value, or a service name.
  `doas.conf(5)` has no argument wildcard. An exact-argument rule covers one value only.
  A rule with no `args` clause permits every argument, so `pkg_add` would accept any URL,
  and `pfctl -f` would load any file. Neither form is safe for a dynamic argument. This
  is where a privilege escalation lives.

  Each privileged mutation therefore has a fixed-function C wrapper, for example
  `/usr/local/libexec/ttx/pkg-add`. The wrapper validates its one argument against a
  strict pattern, rejects flags and URLs, pledges, and calls `execv(3)` on the real tool
  with a fixed argument template. The doas rule permits the wrapper and omits the `args`
  clause, so the argument passes through to the wrapper, and the wrapper holds the
  policy.

  ```
  permit nopass _ttx as root cmd /usr/local/libexec/ttx/pf-load
  permit nopass _ttx as root cmd /usr/local/libexec/ttx/pkg-add
  ```

  doas trusts only `_ttx`. The operator account needs no rules.
  Do not run the harness as root.
  A wrapper is about one hundred lines of C, against libc alone.
  It parses no structured input.
  It never faces the model.
  The audit of a wrapper is exhaustive.
  All other commands fail closed.

- **Dry run by default.** A destructive action occurs only after a successful dry run
  and an explicit confirmation through the confirmation protocol.
  No flag can turn this off.

- **Audit.** The parent appends each prompt, tool call, executed command, exit status,
  and confirmation to `/var/log/ttx/audit.log`. Each confirmation entry records the peer
  user id and the digest.
  The parent also writes each record to `syslog(3)`. `sendsyslog(2)` is in the `stdio`
  promise, so this needs no wider pledge. The harness pins the native log method
  (`setlogsock('native')`), so `Sys::Syslog` does not need the `unix` promise. A record
  that reaches `syslogd(8)` sits in a different privilege domain, and `syslogd` can
  forward it to a remote host. A compromised `_ttx` parent can still forge a future
  record, and it can stop logging, but it cannot rewrite a record that already left the
  host.

- **Audit confidentiality.** The audit content can hold a secret: a `pf` diff, a
  WireGuard key, or a sysctl value. The local log has mode 0600 and owner `_ttx`. A
  remote forward crosses the network, so the operator must weigh that leak before the
  operator enables it.

- **Correct privilege drop.** `rc.d` starts `ttxd` as root.
  The parent opens the log in append-only mode, and it binds the control socket.
  It then drops privilege in order: it clears the supplementary groups, it sets the group
  id, and it sets the user id to `_ttx`. It verifies each id after the drop.
  A wrong order leaves a residual privilege.
  After the drop, no `ttxd` process runs as root.

- **Untrusted display.** The client shows dry-run output and diffs that derive from
  model-influenced bytes. A terminal escape sequence in that data can rewrite the
  operator's view, and it can hide the real change. The client must replace each byte
  outside a strict printable set before display. The strict set is printable ASCII, plus
  newline and tab. The client must remove `DEL` (0x7F) and the C1 range (0x80–0x9F), and
  it must not break a UTF-8 sequence when it filters. The client must cap the diff size,
  and it must guard against a scroll that hides a hunk. The displayed diff comes from the
  parent, never from model text.

- **The internal record channel is a trust boundary.** A parser bug can compromise the
  model process, or a lying `llama-server` can feed it. The parent must treat every
  internal record as hostile. The parent validates each record against the tool schema
  and the policy, and it applies each gate, whatever the record claims.

## Model fetch

`ttx fetch` downloads GGUF artifacts with base `ftp(1)`, which speaks HTTPS. It
validates the `signify(1)` signature against the pinned FuguTTX public key before the
model loads. No TLS library dependency enters the harness.

The signify key is per generation, in the OpenBSD practice. The project generates a key
two releases ahead, and each release ships the public key of the next release. A release
thus validates the next key without a new out-of-band step.

`llama-server` loads the GGUF later, as `_ttxllm`, by path. A verified artifact must not
change between the fetch and the load. The weights directory therefore has owner `_ttx`,
and its mode denies write to `_ttxllm` and to other users. `ttx fetch` re-checks the
signature at load time.

## Package

The harness ships as an OpenBSD port, `sysutils/ttx`. The port skeleton lives in the
repository.
The port installs `ttxd`, `ttx`, and the doas target wrappers under
`/usr/local/libexec/ttx`. It creates the `_ttx` user, the `_ttxllm`
user, and the `ttxop` group.
It includes two `rc.d` scripts: one runs `llama-server` with the TTX model, and one runs
`ttxd`. Weights do not ship in the package.
`ttx fetch` downloads the models separately.
