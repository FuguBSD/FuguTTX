# Harness safety

This document is a part of the [harness](harness.md) specification.

## Safety design

Safety is first-class, not optional.

- <a id="hrn-safe-pledge"></a>**pledge/unveil, per process.** Each process
  pledges only the promises of its role, and unveils only its own paths. The
  process table of [HRN-PROC](harness.md#hrn-proc) is normative. The harness
  reaches `pledge(2)` and `unveil(2)` through `Fugu::Sandbox`, a module of the
  Fugu distribution ([D7](DECISIONS.md#d7)). The module is real on OpenBSD, and
  it is a successful no-op off OpenBSD. A test can therefore prove each promise
  set and each unveil list on any host. `Fugu::Sandbox->is_supported` tells
  enforcement from emulation. No post-setup pledge holds `inet`. The model
  process uses `inet` only during setup, to open its one connection, and it then
  drops to `stdio`. `proc exec` exists only in the parent. A study of these
  mitigations across 19 OpenBSD releases shows they are practical (Ruohonen,
  Sierszecki & Tiwari, arXiv:2607.03056).

- <a id="hrn-safe-wrap"></a>**doas through fixed-function C wrappers.** A
  privileged mutation has a dynamic argument: an arbitrary package name, a
  sysctl value, or a service name. `doas.conf(5)` has no argument wildcard. An
  exact-argument rule covers one value only. A rule with no `args` clause
  permits every argument, so `pkg_add` would accept any URL, and `pfctl -f`
  would load any file. Neither form is safe for a dynamic argument. This is
  where a privilege escalation lives.

  Each privileged mutation therefore has a fixed-function C wrapper, for example
  `/usr/local/libexec/ttx/pkg-add`. The wrapper validates its one argument
  against a strict pattern, and it rejects flags and URLs. It pledges, and it
  calls `execv(3)` on the real tool with a fixed argument template. The doas
  rule permits the wrapper and omits the `args` clause. The argument passes
  through to the wrapper, and the wrapper holds the policy.

  ```
  permit nopass _ttx as root cmd /usr/local/libexec/ttx/pf-load
  permit nopass _ttx as root cmd /usr/local/libexec/ttx/pkg-add
  ```

  doas trusts only `_ttx`. The operator account needs no rules. Do not run the
  harness as root. A wrapper is about one hundred lines of C, against libc
  alone. It parses no structured input. It never faces the model. The audit of a
  wrapper is exhaustive. All other commands fail closed.

- <a id="hrn-safe-dryrun"></a>**Dry run by default.** A destructive action
  occurs only after a successful dry run and an explicit confirmation through
  the confirmation protocol. No flag can turn this off.

- <a id="hrn-safe-audit"></a>**Audit.** The session transcript is the audit
  record (see [session transcript](harness-loop.md#session-transcript)). The
  parent appends each prompt, tool call, executed command, exit status, and
  confirmation to the transcript of the session. Each confirmation record holds
  the peer user id and the digest. The parent also writes each record to
  `syslog(3)` through `Fugu::Log`, in syslog mode. `sendsyslog(2)` is in the
  `stdio` promise, so this needs no wider pledge. The module pins the native log
  method (`setlogsock('native')`), so the process needs no `unix` promise. That
  pin must exist in the installed distribution, and the minimum version of
  [HRN-PKG](#hrn-pkg) covers it. A record that reaches `syslogd(8)` sits in a
  different privilege domain, and `syslogd` can forward it to a remote host. A
  compromised `_ttx` parent can still forge a future record, and it can stop
  logging. It cannot rewrite a record that already left the host.

- <a id="hrn-safe-confid"></a>**Audit confidentiality.** The audit content can
  hold a secret: a `pf` diff, a WireGuard key, or a sysctl value. The transcript
  files and the wire logs have mode 0600 and owner `_ttx`. The wire log holds
  everything the model saw, so it needs the same protection as the transcript. A
  remote forward crosses the network, so the operator must weigh that leak
  before the operator enables it.

- <a id="hrn-safe-drop"></a>**Correct privilege drop.** `rc.d` starts `ttxd` as
  root. The parent binds the control socket, and it verifies the log directory
  (owner `_ttx`, mode 0700). It then drops privilege in order: it clears the
  supplementary groups, it sets the group id, and it sets the user id to `_ttx`.
  It verifies each id after the drop. The parent creates each session file after
  the drop, as `_ttx`, because `_ttx` owns the log directory. A wrong order
  leaves a residual privilege. After the drop, no `ttxd` process runs as root.

- <a id="hrn-safe-display"></a>**Untrusted display.** The client shows dry-run
  output and diffs that derive from model-influenced bytes. A terminal escape
  sequence in that data can rewrite the operator's view, and it can hide the
  real change. The client must replace each byte outside a strict printable set
  before display. The strict set is printable ASCII, plus newline and tab. The
  client must remove `DEL` (0x7F) and the C1 range (0x80–0x9F), and it must not
  break a UTF-8 sequence when it filters. The client must cap the diff size, and
  it must guard against a scroll that hides a hunk. The displayed diff comes
  from the parent, never from model text. [HRN-REPL-7](harness-repl.md#hrn-repl)
  puts this filter in the `Fugu::REPL` module, and the module is its one home.
  The filter must work under taint mode, because each client runs with
  `perl -T`.

- <a id="hrn-safe-record"></a>**The internal record channel is a trust
  boundary.** A parser bug can compromise the model process, or a lying
  `llama-server` can feed it. The parent must treat every internal record as
  hostile. The parent validates each record against the tool schema and the
  policy, and it applies each gate, whatever the record claims.

<a id="hrn-fetch"></a>

## Model fetch

`ttx fetch` is one subcommand of the command line of
[HRN-SPLIT](harness.md#hrn-split), and it holds its own pledge set. `ttx fetch`
downloads GGUF artifacts with base `ftp(1)`, which speaks HTTPS. It validates
the `signify(1)` signature against the pinned FuguTTX public key before the
model loads. No TLS library dependency enters the harness.

The signify key is per generation, in the OpenBSD practice. The project
generates a key two releases ahead, and each release ships the public key of the
next release. So a release validates the next key without a new out-of-band
step.

`llama-server` loads the GGUF later, as `_ttxllm`, by path. A verified artifact
must not change between the fetch and the load. The weights directory therefore
has owner `_ttx`, and its mode denies write to `_ttxllm` and to other users.
`ttx fetch` re-checks the signature at load time.

<a id="hrn-pkg"></a>

## Package

The harness ships as an OpenBSD port, `sysutils/ttx`. The port skeleton lives in
the repository. The port lists llama.cpp and p5-Fugu as run dependencies, with a
minimum Fugu version. That version covers each Fugu module that the harness
loads ([D7](DECISIONS.md#d7)). The port installs `ttxd`, `ttx`, and the doas
target wrappers under `/usr/local/libexec/ttx`. It creates the `_ttx` user, the
`_ttxllm` user, and the `ttxop` group. It creates the log directory
`/var/log/ttx` (owner `_ttx`, mode 0700) and the configuration directory
`/etc/ttx`. It includes two `rc.d` scripts: one runs `llama-server` with the TTX
model, and one runs `ttxd`. Weights do not ship in the package. `ttx fetch`
downloads the models separately.
