# Harness security review

Date: 2026-08-03. Scope: `spec/harness.md`, with decision D7 in
`spec/DECISIONS.md` and `spec/risks.md`. Method: a design review of the
specification against the OpenBSD privilege-separation idiom. No harness code
exists yet, so each finding targets the specification. “Line” is the line in
`spec/harness.md` at commit `077dfa9d84942660e4b544a6a9ccd473c0e89710`.

## 1. Summary

The architecture is sound. The review confirms the three central choices:

1. The `ttxd`/`ttx` split with three system users gives real privilege
   separation.
2. The rule “the process that parses untrusted input must not hold `exec`” is
   the correct core invariant.
3. Perl 5 from base is the correct language for the harness body. Section 3
   gives the full argument.

The review finds three high-severity gaps and a set of medium ones. None of them
breaks the direction. All of them are specification defects that code would
inherit. Three cold reviewers verified each finding against primary sources;
section 5 records the outcomes and four findings they added.

- The doas argument model does not generalize. Exact-argument rules cannot cover
  dynamic values, and rules without `args` permit every argument. The correction
  is a set of fixed-function wrapper programs, and C is the right language for
  them (finding 1, section 3.3).
- Base Perl cannot pass file descriptors, so the `sendfd`/`recvfd` design cannot
  be built as written (finding 3).
- The parent unveil set is too small to run the tool list the same document
  defines (finding 4).
- The confirmation digest does not cover the candidate file content or the
  argument vector, so a confirm-to-install race exists (finding 2, Medium after
  review).

## 2. Findings

Order is by severity.

| #   | Severity | Line             | Finding                                                                                                                                                                                                                                                                                                                                                                                                                                            | Correction                                                                                                                                                                                                                                                                                                                                       |
| --- | -------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | High     | 159–166          | doas rules with exact `args` cannot express dynamic arguments (package names, sysctl values, service names). A rule without `args` permits every argument of the command.                                                                                                                                                                                                                                                                          | Route each privileged action through a fixed-function wrapper program that validates its arguments. Permit only the wrappers in doas. Write the wrappers in C. See 2.1 and 3.3.                                                                                                                                                                  |
| 2   | Medium   | 110–121, 134–137 | The digest covers the dry-run output and the diff, not the candidate file content or the argument vector. Nothing makes confirm-to-install atomic, so a second model-driven write can swap content the operator never saw, and the doas path re-open adds a verify-to-reopen gap. (Downgraded from High: the sibling-rewrite mechanism is refuted — pledge and unveil gate file access per process, so no sibling holds the candidate write path.) | The digest must cover the action identifier, the exact argument vector, the candidate file content, and the dry-run output. The parent must hold the content in memory, verify before install, write to a temporary file, and rename atomically. The candidate directory must be mode 0700, owner `_ttx`, unveiled by the parent alone. See 2.2. |
| 3   | High     | 36–38, 77, 79    | The pledge sets grant `sendfd` and `recvfd`, which implies `SCM_RIGHTS` descriptor passing. Base Perl has no `sendmsg`/`recvmsg` interface, so it cannot pass descriptors.                                                                                                                                                                                                                                                                         | Children must inherit their socket pairs across fork and exec. The frontend must relay bytes, not descriptors. Remove `sendfd` and `recvfd` from every pledge set. The result is a smaller pledge. See 2.3.                                                                                                                                      |
| 4   | High     | 77, 127–144      | The parent unveils only `/usr/bin/doas` (x), the audit log (w), and `/etc` (r). It therefore cannot execute `ifconfig`, `netstat`, `pkg_info`, or the other diagnostics, cannot write candidate files, and cannot re-execute its own program to respawn a crashed child.                                                                                                                                                                           | Enumerate the unveil set: each allowlisted diagnostic binary (x), a candidate directory (rwc), and the `ttxd` binary (x) if children respawn after lockdown. See 2.4.                                                                                                                                                                            |
| 5   | Medium   | 78               | `pledge("stdio inet")` permits connections to every address, not only `127.0.0.1`. A compromised model process can exfiltrate data to the network. The `llama-server` port is also open to every local user.                                                                                                                                                                                                                                       | The model process must connect to `llama-server` during setup and must then drop to `pledge("stdio")`. On disconnection it must exit, and the parent must respawn it. Add a pf rule that blocks outbound traffic for `_ttx` and `_ttxllm` except loopback. See 2.5.                                                                              |
| 6   | Medium   | 23–38            | The specification fixes the language but not the execution discipline. Perl’s single-string `system` and two-argument `open` invoke a shell.                                                                                                                                                                                                                                                                                                       | Make the coding rules normative: list-form `exec`/`system` only, three-argument `open` only, no backticks, taint mode (`-T`) on, `%ENV` reduced to a fixed safe set before any exec. Enforce the rules in the existing CI check. See 3.2.                                                                                                        |
| 7   | Medium   | 111–121          | The client shows dry-run output and diffs verbatim. Terminal escape sequences inside that data can rewrite what the operator sees, and so can forge the confirmation view.                                                                                                                                                                                                                                                                         | The client must replace every non-printable byte outside newline and tab before display. The displayed diff must come from the parent, never from model text.                                                                                                                                                                                    |
| 8   | Medium   | 176–180          | `_ttx` owns the audit log, so a compromised parent can unlink and rewrite history. An `O_APPEND` descriptor does not prevent this.                                                                                                                                                                                                                                                                                                                 | The parent must also write each audit record with `syslog(3)`. `sendsyslog(2)` is permitted under the `stdio` promise, so no pledge widens. `syslogd(8)` can then forward the records to a remote host.                                                                                                                                          |
| 9   | Medium   | 36–38, 110–117   | The digest algorithm, the record limits, and the loop limits are unspecified.                                                                                                                                                                                                                                                                                                                                                                      | Specify SHA-256 through `Digest::SHA` (in base Perl). Bind each confirmation to the peer user id that saw the dry run. Cap the internal record length, the `JSON::PP` nesting depth, the `HTTP::Tiny` timeout, and the tool calls per prompt.                                                                                                    |
| 10  | Medium   | 83–87            | The internal record channel is a trust boundary, but the specification does not say so. A compromised model process can emit any well-formed record. (Raised from Low after review: a missing statement here can produce a missing control.)                                                                                                                                                                                                       | State the rule: the parent must validate every internal record against the tool schemas and the policy, and must treat the model process as hostile. The gates already contain this compromise; make the reasoning explicit.                                                                                                                     |
| 11  | Low      | 130              | `pfctl -s` reads require root, unlike the other read-only diagnostics.                                                                                                                                                                                                                                                                                                                                                                             | State that read-only tools run as `_ttx` without doas, except the enumerated `pfctl -s` reads, which get exact-argument doas rules. Exact rules work here because the argument set is finite.                                                                                                                                                    |
| 12  | Low      | 26–28, 78        | Perl loads modules lazily. A `require` after pledge fails without `rpath`.                                                                                                                                                                                                                                                                                                                                                                         | Each process must load and initialize all modules before it pledges. Record this as an implementation rule.                                                                                                                                                                                                                                      |
| 13  | Low      | 184–186          | `ttx fetch` pins one public key.                                                                                                                                                                                                                                                                                                                                                                                                                   | Pin per-generation keys and let each release name the next key, as the OpenBSD release process does with signify keys.                                                                                                                                                                                                                           |

### 2.1 The doas boundary is the weakest point (finding 1)

The example rules pin exact commands and exact arguments. That form is safe and
non-general. `pkg_add -n nginx` covers one package. The agent needs arbitrary
package names, sysctl values, and service names. doas has no argument wildcard,
so only two forms exist: the exact rule, which cannot generalize, and the rule
without `args`, which permits everything. `pkg_add` without argument control
accepts arbitrary URLs. `pfctl -f` without argument control loads any file. This
is where the privilege escalation lives.

The correction is the standard OpenBSD idiom: small fixed-function helper
programs, for example `/usr/local/libexec/ttx/pkg-add-dry`. Each wrapper accepts
one validated argument, rejects flags and URLs by pattern, pledges, and calls
`execv(3)` on the real tool with a fixed argument template. doas permits only
the wrappers, with no argument passthrough. The policy then lives in auditable
code, not in an unbounded rule. Section 3.3 argues that these wrappers must be
C.

### 2.2 The confirmation gate must bind content, not description (finding 2)

The protocol binds the confirmation to what the operator saw: the dry-run output
and the diff. It does not bind the confirmation to what the system will do: the
argument vector and the candidate file content.

The review first stated this as a sibling-process attack. Peer review refuted
that mechanism. All `ttxd` processes share the `_ttx` user, but the same user id
does not grant file access on OpenBSD: pledge and unveil gate each process. Only
the parent holds `wpath cpath` and an unveil of the candidate directory. The
model process unveils nothing, and the frontend unveils only the socket path. So
no sibling can rewrite a candidate. The reachable gap is a logic-level race.
Nothing makes confirm-to-install atomic, so a second model-driven write can swap
the content between the confirmation and the install. The doas path re-open adds
a second gap: a privileged command that re-opens the candidate path reads
whatever is there at open time, not what the parent verified. The digest must
therefore cover the content and the argument vector. The parent must hold the
content in memory, verify it before install, write it to a temporary file, and
rename atomically. A candidate directory of mode 0700, owner `_ttx`, unveiled by
the parent alone, closes the re-open gap: no other process can write there. This
is defense in depth, and it stands even though the original mechanism does not.

### 2.3 Descriptor passing cannot be built in base Perl (finding 3)

Core Perl exposes `send` and `recv` without ancillary data, and the core
`Socket` module wraps neither `sendmsg(2)` nor `recvmsg(2)`. `SCM_RIGHTS`
passing is therefore not expressible in base Perl without fragile `syscall()`
construction of raw control messages. The design does not need it. The parent
creates each socket pair before fork and exec, and the child inherits its end.
The frontend already relays prompts, streamed output, and confirmations as
bytes. Removing `sendfd` and `recvfd` from the pledge sets makes every process
tighter.

### 2.4 The parent unveil table contradicts the tool table (finding 4)

The tool list runs `ifconfig`, `netstat`, `sysctl`, `pkg_info`, `rcctl`, and
`dmesg` directly, and writes candidate configuration files. The unveil row for
the parent permits none of this. The specification must enumerate the full
unveil set, and the enumeration is itself valuable: it is the complete list of
programs the harness can ever run without doas.

### 2.5 The model process must not keep `inet` (finding 5)

`pledge(2)` cannot restrict a destination address. With `inet`, the one process
that parses hostile model output can also reach the network. The connection to
`127.0.0.1` can happen in the setup phase, before the final pledge. After setup,
`pledge("stdio")` suffices: read the socket, parse, write records to the parent.
When `llama-server` restarts, the child exits and the parent respawns it. This
removes the whole network from the post-setup attack surface, and it follows the
“pledge, after setup” pattern the table already uses.

## 3. Language critique: Perl against C

### 3.1 Perl is correct for the harness body

The decisive argument is the shape of the input. The harness is a policy engine
over untrusted structured text. Its hardest job is to parse hostile JSON, and
OpenBSD base has no C JSON parser. A C harness under the zero-dependency
constraint must hand-write a JSON parser for hostile input in a memory-unsafe
language. That trade converts every parser defect from a Perl exception into a
potential memory-corruption primitive, inside the process that faces the model.
The design already puts the parser in a process that can do nothing; Perl makes
the parser itself unable to corrupt memory. The two mitigations compose.

The supporting arguments:

- **Precedent.** `pkg_add(1)` and the OpenBSD package tools are base-only Perl
  and carry root-level responsibility. The discipline the specification copies
  is proven in the same threat position.
- **First-class mitigations.** `OpenBSD::Pledge(3p)` and `OpenBSD::Unveil(3p)`
  ship in base. The pledge granularity is identical from Perl and from C.
- **The absence of imsg argues for Perl, not against it.** `imsg_init(3)` exists
  because length-prefixed framing in C is dangerous. The same framing in Perl is
  memory-safe by construction. A framing defect dies with an exception instead
  of a corrupted heap.
- **Performance is irrelevant.** The model produces tens of tokens per second.
  The harness is never the bottleneck.
- **Reach.** No compilation, twelve architectures, and one readable artifact to
  audit.

The cost of Perl is the interpreter: a large C program in the trusted computing
base. The same interpreter already runs the package tools on every OpenBSD
system, and pledge confines it per process. The cost is real and accepted.

### 3.2 Perl’s footguns need normative rules

Perl can reach a shell through the single-string forms of `system` and `exec`
(when the argument holds a shell metacharacter), through the pipe forms of
two-argument `open`, and through backticks. A two-argument `open` is also
injectable through mode characters in the filename, even without a shell. One
such call with model-influenced data defeats the whole architecture. The
specification fixes the language and must also fix the discipline (finding 6):
list-form execution only, three-argument `open` only, no backticks, taint mode
on, `%ENV` scrubbed, all modules loaded before pledge. The CI check that
enforces zero CPAN dependencies must also enforce these rules.

### 3.3 C is justified in exactly one place: the doas targets

Finding 1 requires argument-validating wrapper programs, and these run in the
root context. There, the balance inverts:

- A root-context Perl program starts a full interpreter under doas, with the
  interpreter startup surface. A C wrapper of about one hundred lines has none.
- The wrappers parse nothing structured. They compare one argument against a
  fixed pattern and call `execv(3)` with a fixed template. No dynamic allocation
  is necessary. This is the narrow domain where C is safe, and the audit is
  exhaustive.
- Base libc gives everything: `pledge(2)`, `unveil(2)`, `strlcpy(3)`,
  `execv(3)`. This is the OpenBSD idiom of the small privileged helper.

The rule that falls out: **Perl on the unprivileged side of doas, C on the
privileged side.** The C never faces the model. The Perl never runs as root.

### 3.4 Components that must not move to C

Model-output parsing, JSON handling, the HTTP client, the internal record
framing, the policy engine, and the TUI must stay Perl. Each of them handles
variable-length untrusted or semi-trusted data, which is the domain where C
fails. A full C rewrite with `imsg`, `libevent`, and a vendored JSON parser
would enlarge the attack surface it means to shrink.

### 3.5 Impact on decision D7

D7 fixes “Perl for the harness, with base modules only”. The wrappers of 3.3 are
C programs compiled with the base toolchain, so they add no dependency outside
base, but they are not Perl. Adoption therefore needs an amendment to D7 before
any plan implements them. A minimal amendment: “Perl for the harness.
Fixed-function doas target wrappers are C against libc alone. Both use base
tools only.”

## 4. Recommended specification changes

1. Amend D7, then specify the C wrapper set: one wrapper per privileged action,
   the validation pattern of each, and doas rules that name only wrappers
   (finding 1).
2. Extend the confirmation protocol: digest algorithm SHA-256, digest coverage
   (action identifier, argument vector, candidate content, dry-run output), peer
   user id binding, and re-verification before installation (findings 2, 9).
3. Replace descriptor passing with inherited socket pairs and byte relay. Remove
   `sendfd` and `recvfd` from the pledge table (finding 3).
4. Rewrite the parent unveil row as a complete enumeration (finding 4).
5. Reduce the model process to `pledge("stdio")` after setup, with
   exit-and-respawn on disconnection. Add the pf egress rule for `_ttx` and
   `_ttxllm` (finding 5).
6. Add the normative Perl coding rules and extend the CI check (finding 6).
7. Add display sanitization to the client requirements (finding 7).
8. Add the syslog duplicate of the audit stream (finding 8).
9. Add the record, depth, timeout, and per-prompt tool budgets (finding 9).
10. State the trust boundary at the internal record channel, the doas exception
    for `pfctl -s` reads, the preload-before-pledge rule, and the per-generation
    signify key practice (findings 10–13).

## 5. Peer review

Three cold reviewers checked the findings against primary sources: OpenBSD
facts, Perl facts, and design logic. Each reviewer tried to refute, not to
confirm.

### 5.1 Outcomes

- Findings 1, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13 hold. The corrections below refine
  them.
- Finding 2 drops from High to Medium. The sibling-rewrite mechanism is refuted;
  the content-binding correction stands as defense in depth against a
  logic-level race (section 2.2).
- Finding 10 rises from Low to Medium.
- One proposed additional finding is refuted. A reviewer claimed `SO_PEERCRED`
  is Linux-only. `getsockopt.2` documents `SO_PEERCRED` and
  `struct sockpeercred` on OpenBSD, so specification line 106 stands. Base Perl
  reads the struct with `getsockopt` and `unpack`; the field order is
  `{uid, gid, pid}`, unlike Linux.

### 5.2 Refinements folded into the specification

- **Finding 1.** The doas rule for a wrapper must omit the `args` clause, so the
  argument passes to the wrapper and the wrapper holds all validation.
- **Finding 3.** Perl sets close-on-exec on each descriptor above `$^F`. The
  parent must clear `FD_CLOEXEC` on the inherited end, or move it below
  descriptor 3, or the relay breaks at the first `exec`.
- **Finding 4.** The candidate directory must not be `/etc`, which is read-only.
  Use a dedicated directory, mode 0700, owner `_ttx`.
- **Finding 5.** `HTTP::Tiny` opens a socket for each request, so it is unusable
  after `pledge("stdio")`. The model process must speak HTTP/1.1 over one
  persistent connection itself. A pledge violation kills the process with
  `SIGABRT`, so the parent must treat abnormal child death as the respawn
  trigger. The pf `user` match applies to TCP and UDP only.
- **Finding 6.** Single-string `system`/`exec` reach a shell only with a shell
  metacharacter; a plain two-argument `open` does not invoke a shell but stays
  injectable. The list-form and three-argument rules hold regardless.
- **Finding 8.** `Sys::Syslog` must pin `setlogsock('native')`, so it uses
  `sendsyslog(2)` and needs no `unix` promise. The residual risk is forgery of a
  future record; syslog protects only records already delivered.
- **Finding 13.** OpenBSD generates each key two releases ahead and ships it in
  the current release. State the chain, not only “the next key”.

### 5.3 Findings added by review

| #   | Severity | Finding                                                                                                                                                                                    | Correction                                                                                                                        |
| --- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| 14  | Medium   | The privilege-drop procedure has no order. A root daemon that drops the user id before it clears the supplementary groups keeps a residual privilege.                                      | Drop in order: clear supplementary groups, set the group id, set the user id, then verify each id. See harness §Safety design.    |
| 15  | Medium   | The config install is not atomic, and no confirmation timeout exists. A crash mid-install leaves a truncated `/etc` file. One stalled confirmation blocks the single-session daemon.       | Write to a temporary file and rename. Give each pending mutation a timeout that fails closed. See harness §Confirmation protocol. |
| 16  | Medium   | The audit records prompts, diffs, and commands, which can hold secrets (a `pf` diff, a WireGuard key, a sysctl value). The remote syslog forward of finding 8 amplifies the leak off-host. | Keep the local log mode 0600, owner `_ttx`. State the remote-forward leak as an operator trade. See harness §Safety design.       |
| 17  | Medium   | `ttx fetch` verifies the signify signature at fetch time, but `llama-server` loads the GGUF later, by path, as `_ttxllm`. A writable weights directory allows a swap after verification.   | Own the weights directory as `_ttx`, deny write to `_ttxllm`, and re-verify the signature at load time. See harness §Model fetch. |
