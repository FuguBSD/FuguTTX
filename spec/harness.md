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

The language is Perl 5 from OpenBSD base, and nothing else.
The harness uses only modules from base: `OpenBSD::Pledge(3p)` and `OpenBSD::Unveil(3p)`
for the sandbox, `HTTP::Tiny` for the local llama-server API, `JSON::PP` for tool-call
parsing, and `Socket` for the control socket.

**Zero CPAN dependencies is a hard constraint.
A CI check enforces it.** The OpenBSD package tools are Perl, written against base
alone. The harness follows the same discipline.
No compilation is necessary.
No port dependency exists, other than llama.cpp.

Base Perl has no `imsg_init(3)` interface.
The harness frames each internal message as a length-prefixed `JSON::PP` record over
`socketpair(2)`.

## Architecture

`llama-server` (from the `misc/llama.cpp` port) serves the TTX model over an
OpenAI-compatible HTTP API on `127.0.0.1`. `ttxd` operates a perceive → plan → act →
observe loop against it.
Together they make the TTX agent: the model proposes, the harness decides and executes.

`llama-server` constrains tool calls at sample time with its JSON-schema/grammar
support. Thus model output is parseable by construction.
`JSON::PP` validates it again.
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
| Parent (engine) | Policy, tool execution, audit | `stdio rpath wpath cpath sendfd recvfd proc exec` | `/usr/bin/doas` (x), the audit log (w), `/etc` (r) |
| Model process | HTTP to llama-server, JSON parsing | `stdio inet` | nothing |
| Frontend process | Control socket, session, confirmations | `stdio unix sendfd recvfd` | the socket path |

- **The parent** holds the tool policy, executes each command, and writes the audit log.
  It never sees raw model output.
  It parses only the fixed internal record format, which the harness itself defines.
- **The model process** speaks HTTP to `llama-server` and parses model output with
  `JSON::PP`. It reduces each valid tool call to a fixed internal record for the parent.
  It has no file system view and no `exec`. An exploited parser bug lands in a process
  that can do nothing.
- **The frontend process** owns the control socket and the operator session.
  It relays prompts, streamed output, and confirmations between the client and the
  parent.

The parent starts each child with fork and exec of its own program, with a role flag.
Each child thus gets a fresh address-space layout.

The table gives the pledge sets for the agent loop.
`ttx fetch` is a standalone mode with its own, separate pledge set.

The client `ttx` pledges `stdio tty unix` and unveils only the socket path.
A defect in the client is worth nothing.

## Control socket

`ttxd` listens on `/var/run/ttxd.sock`. The socket has owner `_ttx`, group `ttxop`, and
mode `0660`. Membership in the `ttxop` group is the operator grant.
For each connection, the frontend reads the peer credentials with `getsockopt(2)` and
`SO_PEERCRED`. The audit log attributes each session and each confirmation to that user
id.

## Confirmation protocol

The dry-run gate is a protocol, not a prompt:

1. The parent gives each pending mutation an action identifier.
2. The parent computes a digest over the dry-run output and the diff.
3. The client shows the dry-run output and the diff to the operator.
4. A confirmation message must carry the action identifier and the digest.
5. A confirmation with a stale identifier or a wrong digest fails closed.
6. When a session disconnects, its pending mutations die.

A confirmation therefore applies only to the exact action that the operator saw.
No pending action outlives its session.

## Tools

Each tool is a function with a JSON schema.

**Read-only tools:**

- Read configuration files under unveiled paths: `/etc/pf.conf`, `/etc/sysctl.conf`,
  `/etc/rc.conf.local`.
- Run diagnostics: `pfctl -s rules|states|info`, `ifconfig`, `netstat`, `sysctl` (read),
  `pkg_info`, `rcctl get|check`, `dmesg`.

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
  `inet` exists only in the model process.
  `proc exec` exists only in the parent.
  A study of these mitigations across 19 OpenBSD releases shows they are practical
  (Ruohonen, Sierszecki & Tiwari, arXiv:2607.03056).

- **doas, narrow scope.** Privileged actions go through `doas` with per-command rules
  for the `_ttx` user.
  doas trusts only `_ttx`. The operator account needs no rules.
  Do not run the harness as root.
  Example rules:

  ```
  permit nopass _ttx as root cmd /sbin/pfctl args -nf /etc/pf.conf.candidate
  permit nopass _ttx as root cmd /usr/sbin/pkg_add args -n nginx
  ```

  Rules list exact commands and arguments.
  All other commands fail closed.

- **Dry run by default.** A destructive action occurs only after a successful dry run
  and an explicit confirmation through the confirmation protocol.
  No flag can turn this off.

- **Audit.** The parent appends each prompt, tool call, executed command, exit status,
  and confirmation to `/var/log/ttx/audit.log`. Each confirmation entry records the peer
  user id and the digest.
  `rc.d` starts `ttxd` as root.
  The parent opens the log in append-only mode, binds the control socket, and then drops
  to `_ttx`. After the drop, no `ttxd` process runs as root.

## Model fetch

`ttx fetch` downloads GGUF artifacts with base `ftp(1)`, which speaks HTTPS. It
validates the signify signature against the pinned FuguTTX public key before the model
loads. No TLS library dependency enters the harness.

## Package

The harness ships as an OpenBSD port, `sysutils/ttx`. The port skeleton lives in the
repository.
The port installs `ttxd` and `ttx`. It creates the `_ttx` user, the `_ttxllm`
user, and the `ttxop` group.
It includes two `rc.d` scripts: one runs `llama-server` with the TTX model, and one runs
`ttxd`. Weights do not ship in the package.
`ttx fetch` downloads the models separately.
