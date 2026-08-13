# Harness

<a id="hrn-split"></a>

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

<a id="hrn-lang"></a>

## Language constraint

The harness body is Perl 5 from OpenBSD base.
The doas target wrappers are C, against libc alone (see
[Safety design](#safety-design)). Decision [D7](decisions.md) sets the rule: Perl on the
unprivileged side of doas, C on the privileged side.
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

<a id="hrn-perl"></a>

### Perl execution discipline

Perl can reach a shell through some call forms.
One such call with model-influenced data defeats the architecture.
These rules are normative, and the CI check enforces them:

- Use the list form of `system` and `exec`. Do not use the single-string form.
- Use three-argument `open`. Do not use two-argument `open`, and do not use backticks.
- Run every program under taint mode (`perl -T`).
- Reduce `%ENV` to a fixed safe set before any `exec`.
- Load and exercise every module before the process pledges.
  A lazy `require` after `pledge(2)` needs `rpath`. Its absence kills the process with
  `SIGABRT`.

<a id="hrn-arch"></a>

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
Each step has a fixed budget of turns.
A malformed call gets one re-prompt.
Then the step stops.
The [agent loop](#the-agent-loop) section defines the loop, and the
[failure budgets](#failure-budgets) table defines every recovery path.
The loop design follows the
[harness-loop research](../docs/research/harness-loops/index.md).

Three system users divide the components:

| User | Runs | Holds |
| --- | --- | --- |
| `_ttx` | `ttxd` | The doas rules, the session transcripts, the control socket. |
| `_ttxllm` | `llama-server` | Nothing: no doas rules, no socket, no log. |
| The operator account | `ttx` | Control-socket access, through the `ttxop` group. |

`llama-server` is the largest compiled program in the system, so it must not run as
`_ttx`. A compromised `llama-server` holds no rights.
It can only lie in its HTTP responses, and the model process parses those under a
minimal pledge.

The daemon serves one interactive session at a time, synchronously.
Base Perl has no event library, and this design does not need one.

<a id="hrn-proc"></a>

## The three processes of ttxd

`ttxd` follows the OpenBSD daemon pattern: a parent and unprivileged children, connected
by socket pairs. One rule controls the design: **the process that parses untrusted input
must not hold `exec`**. Model output is untrusted input.

| Process | Role | pledge, after setup | unveil |
| --- | --- | --- | --- |
| Parent (engine) | Policy, tool execution, audit | `stdio rpath wpath cpath proc exec` | the diagnostic binaries (x), the doas wrappers (x), `/usr/bin/doas` (x), the candidate directory (rwc), the `ttxd` binary (x), `/var/log/ttx` (rwc), `/etc` (r), `/usr/share/man` (r) |
| Model process | HTTP to llama-server, JSON parsing | `stdio` | nothing |
| Frontend process | Control socket, session, confirmations | `stdio unix` | the socket path |

- **The parent** holds the tool policy, executes each command, and writes the session
  transcript (see [session transcript](#session-transcript)). It never sees raw model
  output. It parses only the fixed internal record format, which the harness itself
  defines. The unveil row is a complete enumeration: it names each diagnostic binary the
  parent can run without doas, the doas wrappers, the candidate directory it writes, the
  log directory, and the `ttxd` binary it re-executes to respawn a child.
  The candidate directory is not `/etc`, because `/etc` is read-only to the parent.
- **The model process** speaks HTTP to `llama-server` and parses model output with
  `JSON::PP`. It reduces each valid tool call to a fixed internal record for the parent.
  It opens one persistent HTTP/1.1 connection to `127.0.0.1` during setup, and it then
  pledges `stdio` only.
  It holds no `inet` promise after setup, because `pledge(2)` cannot restrict a
  destination address, and the one process that parses hostile model output must not
  reach the network. `HTTP::Tiny` opens a socket for each request, so the model process
  must not use it after the pledge; it speaks HTTP/1.1 over the one persistent
  connection itself. When the connection ends, the model process exits, and the parent
  respawns it. The parent treats an abnormal child exit as the respawn trigger.
  The model process has no file system view and no `exec`. An exploited parser bug lands
  in a process that can do nothing and can reach nothing.
  The model process appends each raw request and each raw response to the wire log,
  through a descriptor that it inherits from the parent (see
  [session transcript](#session-transcript)).
- **The frontend process** owns the control socket and the operator session.
  It relays prompts, output, liveness events, and confirmations between the client and
  the parent (see [Liveness](#liveness)).

The parent starts each child with fork and exec of its own program, with a role flag.
Each child thus gets a fresh address-space layout.

Base Perl cannot pass a file descriptor over a socket.
The core `Socket` module wraps neither `sendmsg(2)` nor `recvmsg(2)`, so `SCM_RIGHTS` is
not expressible in base Perl.
The harness therefore does not pass descriptors.
The parent creates each `socketpair(2)` before the fork, and the child inherits its end
across `exec`. Perl sets close-on-exec on each descriptor above `$^F`, so the parent
must clear `FD_CLOEXEC` on the child end before `exec`, or move the descriptor below
file descriptor 3. No pledge set holds `sendfd` or `recvfd`. The frontend relays bytes,
not descriptors.

The table gives the pledge sets for the agent loop.
`ttx fetch` is a standalone mode with its own, separate pledge set.

The client `ttx` pledges `stdio tty unix` and unveils only the socket path.
A defect in the client is worth nothing.

<a id="hrn-socket"></a>

## Control socket

`ttxd` listens on `/var/run/ttxd.sock`. The socket has owner `_ttx`, group `ttxop`, and
mode `0660`. Membership in the `ttxop` group is the operator grant.
For each connection, the frontend reads the peer credentials with `getsockopt(2)` and
`SO_PEERCRED`. On OpenBSD this option returns a `struct sockpeercred`, which holds the
user id, then the group id, then the process id.
Base Perl reads it with `getsockopt` and `unpack`, so no compiled module is necessary.
The field order differs from the Linux `struct ucred`, so do not copy a Linux example.
The session transcript attributes each session and each confirmation to that user id.

<a id="hrn-confirm"></a>

## Confirmation protocol

The dry-run gate is a protocol, not a prompt.
These rules define it:

- **HRN-CONFIRM-1.** The parent gives each pending mutation an action identifier.
- **HRN-CONFIRM-2.** The parent computes a SHA-256 digest with `Digest::SHA`. The digest
  covers the action identifier, the exact argument vector, the candidate file content,
  and the dry-run output.
- **HRN-CONFIRM-3.** The client shows the dry-run output and the diff to the operator.
- **HRN-CONFIRM-4.** A confirmation message must carry the action identifier and the
  digest.
- **HRN-CONFIRM-5.** A confirmation with a stale identifier or a wrong digest fails
  closed.
- **HRN-CONFIRM-6.** A confirmation must come from the same peer user id that saw the
  dry run. This rule depends on the control socket ([HRN-SOCKET](#hrn-socket)).
- **HRN-CONFIRM-7.** A pending mutation has a timeout.
  After the timeout, it fails closed.
- **HRN-CONFIRM-8.** When a session disconnects, its pending mutations die.
- **HRN-CONFIRM-9.** The parent holds the candidate content in memory.
  Before it installs the file, it verifies the content against the digest.
  It writes the held bytes to a temporary file, and it then renames the file into place.
  The rename is atomic, so a crash cannot leave a truncated target.
- **HRN-CONFIRM-10.** The candidate directory has mode 0700 and owner `_ttx`. Only the
  parent holds an unveil of the candidate directory, so no other process can rewrite a
  candidate between the confirmation and the install.

The digest binds the confirmation to what the system will do, not only to what the
operator saw.
A confirmation therefore applies only to the exact action that the operator
saw. No pending action outlives its session.
The daemon serves one session at a time, so a stalled confirmation must not block the
daemon. The timeout of HRN-CONFIRM-7 releases it.

## Tools

Each tool is a function with a JSON schema.

<a id="hrn-tool-ro"></a>**Read-only tools:**

- **HRN-TOOL-RO-1.** Read configuration files under unveiled paths: `/etc/pf.conf`,
  `/etc/sysctl.conf`, `/etc/rc.conf.local`.
- **HRN-TOOL-RO-2.** Run diagnostics: `pfctl -s rules|states|info`, `ifconfig`,
  `netstat`, `sysctl` (read), `pkg_info`, `rcctl get|check`, `dmesg`.
- **HRN-TOOL-RO-3.** Render one man page, by section and name: `man -T ascii`. The
  arguments validate against a strict name pattern.
  The retrieval rows of the [baseline grid](evaluation.md#baselines-and-ablations) use
  this tool.
- **HRN-TOOL-RO-4.** The parent runs most read-only tools directly as `_ttx`, with no
  doas. `pfctl` is the exception.
  `pfctl -s` reads `/dev/pf`, which is mode 0600 and owner root.
  The `pfctl -s rules|states|info` reads therefore get exact-argument doas rules.
  The argument set is finite, so an exact rule is safe here.
  This rule depends on the system users ([HRN-ARCH](#hrn-arch)).

<a id="hrn-tool-gate"></a>**Gated mutations — dry run first, always:**

- **HRN-TOOL-GATE-1.** Configuration edits: write a candidate file, show the diff, and
  validate (`pfctl -nf pf.conf.candidate`). Install the file only after an explicit
  confirmation.
- **HRN-TOOL-GATE-2.** `pkg_add` and `pkg_delete`: run with `-n` first.
  Do the real invocation only after a confirmation.
- **HRN-TOOL-GATE-3.** `sysctl -w`: record the previous value.
  Apply only after a confirmation.
  Give a rollback option.
- **HRN-TOOL-GATE-4.** `rcctl enable|start|restart`: apply only after a confirmation.
- **HRN-TOOL-GATE-5.** Each gated mutation records its rollback path before it applies:
  the previous file content, the previous sysctl value, or the previous service state.
  The rollback record enters the session transcript.
  This rule depends on the session transcript ([HRN-TRANSCRIPT](#hrn-transcript)).

<a id="hrn-pf-commit"></a>**The pf commit-confirm rule.** A bad ruleset can cut the
connection that carries the confirmation, and `pfctl` has no built-in revert.
A confirmed mistake is not an attack, so no gate stops it.
A `pf.conf` install is therefore a two-step commit:

1. Before the install, the parent copies the live `/etc/pf.conf` into the candidate
   directory.
2. After the confirmation, the parent installs the candidate and loads it through the
   `pf-load` wrapper.
3. A revert timer starts.
   The default window is 120 seconds.
4. The operator confirms connectivity through the client, inside the window.
5. Without the second confirmation, the parent restores the saved file, and it loads the
   file through the same wrapper.
   A lockout thus heals itself.
6. A session disconnect before the second confirmation triggers the same revert.

The revert is the one mutation that runs without a fresh confirmation.
It only restores the ruleset that was live before the install.

<a id="hrn-tool-report"></a>**The terminal tool:**

- `report` ends the step, and it carries the answer of the model to the operator.
  It executes no command.
  It is always in the tool table, because the grammar forces a tool call on each turn
  (see [the agent loop](#the-agent-loop)).

<a id="hrn-tool-table"></a>Each tool has one row in a static metadata table.
The table generates both the tool line of the system prompt and the JSON schema.
Thus the prompt and the policy cannot drift.

<a id="hrn-loop"></a>

## The agent loop

The parent operates the perceive → plan → act → observe loop as one synchronous
while-loop. Two terms are fixed:

- A **turn** is one model call plus the execution of its tool call.
- A **step** is one operator prompt and all of its turns.

Five rules control the loop:

- **HRN-LOOP-1 — The transcript drives the loop.** The parent appends each event to the
  session transcript before it acts on the event.
  At the top of each turn, the parent derives its next action from the transcript.
  It keeps no loop state outside the transcript.
  A restarted daemon can therefore resume a session from the transcript alone.
- **HRN-LOOP-2 — Budgets are checked before each model call.** The
  [failure budgets](#failure-budgets) table defines each budget.
- **HRN-LOOP-3 — A turn has exactly one tool call.** The llama-server grammar enforces
  the count. The parent executes tool calls strictly serially.
  The loop has no subagents, no nesting, and no parallel execution.
- **HRN-LOOP-4 — The terminal tool ends the step.** The model ends a step with one
  `report` call that carries its answer.
  The grammar forces a tool call on each turn, so a reply without a call cannot end the
  step. The grammar and the stop condition are therefore one joint design.
  When the turn budget is exhausted, the harness makes one final model call that permits
  only the `report` tool.
  Thus each step ends with a report.
- **HRN-LOOP-5 — Errors divide into two classes.** A harness or transport failure is
  fatal: the step stops, and the operator sees the error.
  Model misbehavior — a malformed call, an unknown tool, invalid arguments, an empty
  response, a repeated call — becomes a tool result with precise error text, and it
  spends budget from the failure table.
  Model misbehavior must not crash the loop.

<a id="hrn-cancel"></a>

### Cancellation

The operator can cancel a step through the client at any time.
On a cancel, the parent must not start a new model call.
The parent kills the process group of a running tool.
The parent appends a synthesized error result for each unanswered tool call.
Thus no tool call in the transcript lacks a result.
This specification does not fix the abort mechanism for an in-flight model generation.

<a id="hrn-live"></a>

### Liveness

CPU generation is slow, and the harness does not stream tokens.
The frontend therefore relays one coarse event per loop stage to the client: model call
started, tool started (with the tool name), and confirmation pending.
These events are transient.
They do not enter the transcript.

<a id="hrn-invoke"></a>

## Model invocation

Each turn makes one blocking chat-completions request.
The harness does not stream.

- **HRN-INVOKE-1 — Sampling.** Temperature 0 for tool-driven turns.
  This value is a starting point.
  The evaluation suite validates the sampler settings ([evaluation](evaluation.md)).
- **HRN-INVOKE-2 — Transport retry.** At most 3 retries per request, with exponential
  backoff (2 s, 4 s, 8 s), between the loop and llama-server.
  Every retry budget must have a cap.
- **HRN-INVOKE-3 — Timeout.** The HTTP timeout is fixed.
  Its value derives from measurement: the maximum output tokens divided by the measured
  tokens/s, plus the prompt-processing time, with margin.
  Until the measurement exists, the value is 600 s.
- **HRN-INVOKE-4 — Prompt-cache discipline.** CPU prompt processing is the slow axis,
  and llama-server reuses the KV cache for a byte-stable prefix.
  The tool list sorts by name.
  No timestamp in the prompt is finer than the hour.
  Within a step, the prompt only appends.
  It never rewrites.
- **HRN-INVOKE-5 — Token budgeting.** The harness must know the prompt size before each
  send. Base Perl has no tokenizer.
  The llama-server `/tokenize` endpoint is the candidate mechanism.
- **HRN-INVOKE-6 — No context shift.** llama-server must run with context shift off.
  A silent context shift breaks the invariant that the transcript equals the model
  context, and the audit design depends on that invariant.
  On overflow, the harness compacts, or it stops with an error (see
  [context management](#context-management)).

<a id="hrn-prompt"></a>

## Prompt assembly

The harness assembles the prompt from a fixed chunk order: the system prompt, the
operator instruction file, the skill list, and the messages that derive from the
transcript. A fixed order maximizes prefix-cache reuse.
The skill list comes from the skills mechanism ([HRN-SKILLS](#hrn-skills)).

- **HRN-PROMPT-1 — System prompt.** At most 700 tokens: the agent identity, one line per
  tool from the tool metadata table, and the loop rules.
- **HRN-PROMPT-2 — Operator instruction file.** One file, `/etc/ttx/instructions.md`,
  with a budget of 4,096 bytes.
  The harness truncates the file at the budget, and it logs a warning.
  There is no directory walk and no file stacking.
- **HRN-PROMPT-3 — Cadence.** The harness reads the instruction file once per step.
  The assembled prompt stays byte-stable across the turns of one step.
- **HRN-PROMPT-4 — Lockstep with training.** The system prompt, the tool schemas, the
  error templates, and the re-prompt texts are training-time artifacts.
  The SFT trace generator must use the same artifacts ([training](training.md)). A
  change to one of them is a training-data change, not only a harness change.

<a id="hrn-skills"></a>

## Skills

A skill is a stored procedure for one task, in the published `SKILL.md` convention.

- A skill lives in `/etc/ttx/skills/<name>/SKILL.md`: frontmatter between `---` lines,
  then a markdown body.
  The `name` field must match the directory name: lowercase `[a-z0-9-]`, at most 64
  characters. The `description` field is required, at most 1,024 characters.
  A base-Perl line parser reads the `key: value` frontmatter.
  No YAML module is necessary.
- The system prompt lists only the name and the description of each skill.
- The trigger is deterministic.
  The operator invokes a skill by name, or the harness matches an optional frontmatter
  `triggers` keyword list against the operator prompt.
  The model must not select skills from a catalog.
  A 4B model follows a “read the file yourself” instruction weakly.
- An invocation can carry arguments.
  The harness substitutes `$ARGUMENTS` and `$1` to `$n` in the body before injection.
  A skill is thus a reusable runbook.
- The harness injects the skill body into the step as a context message.
  The body budget is 4,096 bytes.
  The harness truncates above it, and it logs a warning.

The instruction file and each skill body are prompt text only.
The harness must not execute a command that this text names.
Only a model-proposed tool call, through every gate, reaches execution.
An instruction file must not become an execution channel.

<a id="hrn-calls"></a>

## Tool-call handling

The grammar constrains model output at sample time.
Validation still runs in full, because a lying `llama-server` can bypass the grammar
(see [safety design](#safety-design)).

- **Strict rejection.** The harness must not coerce argument types, and it must not
  normalize tool names.
  A coerced argument muddies the confirmation digest, which binds the exact argument
  vector. The grammar prevents type errors at sample time, so coercion also has no
  purpose.
- **Precise error results.** A failed validation returns a tool result that names each
  bad field and echoes the received arguments.
  An unknown tool name returns the fixed result `unknown tool: <name>`. Empty tool
  output returns a fixed sentence plus the exit status.
- **The length-stop guard.** When a response reports that the output hit the token
  limit, the parent executes nothing from that response.
  A truncated call can validate and still be incomplete.
  The re-prompt states that the call can be truncated, and it spends the malformed-call
  budget. The internal record therefore carries the finish reason and the usage counts of
  each response.
- **No fallback parser.** The model process parses tool calls with `JSON::PP` alone.
  A free-text fallback parser must not exist.
  If the grammar fails, that is a defect to fix, not to parse around.

<a id="hrn-trunc"></a>

## Tool output truncation

Two limits cap each tool output toward the model: 100 lines and 4,096 bytes, whichever
comes first. Truncation keeps the head and the tail, and it inserts an explicit marker
with the count of elided lines and bytes.
The exit status always survives.
The session transcript keeps the full output ([HRN-TRANSCRIPT](#hrn-transcript)).

<a id="hrn-budgets"></a>

## Failure budgets

One table defines every recovery path and its budget.
No retry path exists outside this table.
The values are starting points.
The evaluation suite validates them ([evaluation](evaluation.md)).

| Recovery path | Budget | At the budget |
| --- | --- | --- |
| Malformed or invalid tool call | 1 re-prompt per step | The step stops. |
| Length-stop response | Shares the malformed-call re-prompt; nothing executes | The step stops. |
| Empty model response | 2 retries per step | The step stops with a fixed message. |
| Identical consecutive tool call | 2 repeats; the third identical call does not execute | The step stops and fails closed. |
| Transport failure | 3 retries per request, exponential backoff | The step stops with the transport error. |
| Turns per step | 20 | One final call permits only `report`. The step ends. |
| Context overflow inside a step | 1 compaction | The step stops with an error. |

Two calls are identical when they have the same tool name and byte-identical canonical
arguments.
A detected repetition has one response: stop the step, report to the operator,
and fail closed. The harness must not recover automatically, and it must not refuse one
call and continue. The operator decides whether to continue.

<a id="hrn-context"></a>

## Context management

The model window is a projection, derived at read time from the append-only transcript.
History is never rewritten.
An elision or a summary appends a superseding record that names the ordinals it
supersedes, and the projection skips the superseded records.

- **Primary mechanism: deterministic elision.** Keep the last four tool results
  verbatim. Replace each older tool result with a one-line stub that names the tool and
  the count of omitted lines.
  This mechanism is deterministic, needs no model call, and stays auditable.
- **Secondary mechanism: a model-written summary.** For whole-session overflow only.
  The harness summarizes with the same model and all tools disabled.
  It keeps a verbatim tail of approximately 1,000 tokens, and it appends the summary as
  an explicit transcript record.
- **Cadence.** Elision and summary run between steps, at a prompt boundary, where one
  full prompt re-process is acceptable.
  Within a step, the prompt only appends (see [model invocation](#model-invocation)).
  The one exception is the mid-step overflow compaction in the failure table.

<a id="hrn-transcript"></a>

## Session transcript

One append-only JSONL file per session is the session record:
`/var/log/ttx/session-<id>.jsonl`. The directory `/var/log/ttx` has owner `_ttx` and
mode 0700. Each file has mode 0600. The transcript is the audit log.
A session file never changes after the session ends, so a retention job can remove old
files safely. This specification does not fix the append discipline.

- **Envelope.** Each record is one JSON object on one line, with a timestamp, a
  monotonic ordinal, a type, and a payload.
  Ordinals are strictly consecutive.
  A gap or a malformed line fails the load, loudly.
- **Record types.** Session meta (format version, peer user id), operator prompt, model
  response (with usage counts and finish reason), tool call, tool result (with exit
  status and output), confirmation (peer user id and digest), elision, summary, error,
  and session end.
- **Persistence policy.** Turn boundaries, model-visible content, tool calls, executed
  commands, exit statuses, confirmations, and usage counts persist.
  Transient progress events go to the client only.
- **Record size cap.** A tool-result record keeps the full tool output, up to a hard cap
  of 65,536 bytes per record.
  Above the hard cap, the record keeps the head and the tail, with a marker.
  No spool directory exists.
  Thus the parent unveil table stays a complete enumeration.
- **Three consumers, one file.** The model context, client replay, and the audit all
  derive from the transcript.
  Replay is side-effect-free.
  It never re-executes a tool.
  A replayed event carries a replay mark, so the client cannot confuse it with a live
  event.
- **Crash record.** On a fatal error, the parent appends an error record before it
  exits. Thus the transcript records the crash.
- **Usage accounting.** Each model-response record embeds the usage counts that
  llama-server returns.
  Totals derive from the transcript.
  No second store exists.
- **Syslog duplicate.** The parent writes each record to `syslog(3)` as a redacted
  summary. The key=value field names reuse the OpenTelemetry `gen_ai.*` vocabulary (for
  example `gen_ai.usage.input_tokens`), without the OTLP transport.
  The audit rules of [HRN-SAFE-AUDIT](#hrn-safe-audit) govern this duplicate.
- <a id="hrn-wirelog"></a>**Raw wire log.** The model process appends each raw request
  body and each raw response to a per-session wire log, `/var/log/ttx/wire-<id>.jsonl`.
  The parent opens the file in append mode before the fork, and the model process
  inherits the descriptor.
  The parent starts a fresh model process for each session.
  Thus each session has its own wire-log descriptor, its own connection, and a fresh
  address-space layout.
  A write to an open descriptor sits inside the `stdio` promise, so the model-process
  pledge does not widen.
  The wire log holds everything the model saw.
  Forensics for a malformed call needs the exact prompt bytes, not a paraphrase.
  The wire log has the same confidentiality as the transcript: owner `_ttx`, mode 0600
  ([HRN-SAFE-CONFID](#hrn-safe-confid)).

## Safety design

Safety is first-class, not optional.

- <a id="hrn-safe-pledge"></a>**pledge/unveil, per process.** Each process pledges only
  the promises of its role, and unveils only its own paths.
  The process table of [HRN-PROC](#hrn-proc) is normative.
  No post-setup pledge holds `inet`. The model process uses `inet` only during setup, to
  open its one connection, and it then drops to `stdio`. `proc exec` exists only in the
  parent. A study of these mitigations across 19 OpenBSD releases shows they are
  practical (Ruohonen, Sierszecki & Tiwari, arXiv:2607.03056).

- <a id="hrn-safe-wrap"></a>**doas through fixed-function C wrappers.** A privileged
  mutation has a dynamic argument: an arbitrary package name, a sysctl value, or a
  service name. `doas.conf(5)` has no argument wildcard.
  An exact-argument rule covers one value only.
  A rule with no `args` clause permits every argument, so `pkg_add` would accept any
  URL, and `pfctl -f` would load any file.
  Neither form is safe for a dynamic argument.
  This is where a privilege escalation lives.

  Each privileged mutation therefore has a fixed-function C wrapper, for example
  `/usr/local/libexec/ttx/pkg-add`. The wrapper validates its one argument against a
  strict pattern, rejects flags and URLs, pledges, and calls `execv(3)` on the real tool
  with a fixed argument template.
  The doas rule permits the wrapper and omits the `args` clause, so the argument passes
  through to the wrapper, and the wrapper holds the policy.

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

- <a id="hrn-safe-dryrun"></a>**Dry run by default.** A destructive action occurs only
  after a successful dry run and an explicit confirmation through the confirmation
  protocol. No flag can turn this off.

- <a id="hrn-safe-audit"></a>**Audit.** The session transcript is the audit record (see
  [session transcript](#session-transcript)). The parent appends each prompt, tool call,
  executed command, exit status, and confirmation to the transcript of the session.
  Each confirmation record holds the peer user id and the digest.
  The parent also writes each record to `syslog(3)`. `sendsyslog(2)` is in the `stdio`
  promise, so this needs no wider pledge.
  The harness pins the native log method (`setlogsock('native')`), so `Sys::Syslog` does
  not need the `unix` promise.
  A record that reaches `syslogd(8)` sits in a different privilege domain, and `syslogd`
  can forward it to a remote host.
  A compromised `_ttx` parent can still forge a future record, and it can stop logging,
  but it cannot rewrite a record that already left the host.

- <a id="hrn-safe-confid"></a>**Audit confidentiality.** The audit content can hold a
  secret: a `pf` diff, a WireGuard key, or a sysctl value.
  The transcript files and the wire logs have mode 0600 and owner `_ttx`. The wire log
  holds everything the model saw, so it needs the same protection as the transcript.
  A remote forward crosses the network, so the operator must weigh that leak before the
  operator enables it.

- <a id="hrn-safe-drop"></a>**Correct privilege drop.** `rc.d` starts `ttxd` as root.
  The parent binds the control socket, and it verifies the log directory (owner `_ttx`,
  mode 0700). It then drops privilege in order: it clears the supplementary groups, it
  sets the group id, and it sets the user id to `_ttx`. It verifies each id after the
  drop. The parent creates each session file after the drop, as `_ttx`, because `_ttx`
  owns the log directory.
  A wrong order leaves a residual privilege.
  After the drop, no `ttxd` process runs as root.

- <a id="hrn-safe-display"></a>**Untrusted display.** The client shows dry-run output
  and diffs that derive from model-influenced bytes.
  A terminal escape sequence in that data can rewrite the operator’s view, and it can
  hide the real change.
  The client must replace each byte outside a strict printable set before display.
  The strict set is printable ASCII, plus newline and tab.
  The client must remove `DEL` (0x7F) and the C1 range (0x80–0x9F), and it must not
  break a UTF-8 sequence when it filters.
  The client must cap the diff size, and it must guard against a scroll that hides a
  hunk. The displayed diff comes from the parent, never from model text.

- <a id="hrn-safe-record"></a>**The internal record channel is a trust boundary.** A
  parser bug can compromise the model process, or a lying `llama-server` can feed it.
  The parent must treat every internal record as hostile.
  The parent validates each record against the tool schema and the policy, and it
  applies each gate, whatever the record claims.

<a id="hrn-fetch"></a>

## Model fetch

`ttx fetch` downloads GGUF artifacts with base `ftp(1)`, which speaks HTTPS. It
validates the `signify(1)` signature against the pinned FuguTTX public key before the
model loads. No TLS library dependency enters the harness.

The signify key is per generation, in the OpenBSD practice.
The project generates a key two releases ahead, and each release ships the public key of
the next release. A release thus validates the next key without a new out-of-band step.

`llama-server` loads the GGUF later, as `_ttxllm`, by path.
A verified artifact must not change between the fetch and the load.
The weights directory therefore has owner `_ttx`, and its mode denies write to `_ttxllm`
and to other users. `ttx fetch` re-checks the signature at load time.

<a id="hrn-pkg"></a>

## Package

The harness ships as an OpenBSD port, `sysutils/ttx`. The port skeleton lives in the
repository. The port installs `ttxd`, `ttx`, and the doas target wrappers under
`/usr/local/libexec/ttx`. It creates the `_ttx` user, the `_ttxllm` user, and the
`ttxop` group. It creates the log directory `/var/log/ttx` (owner `_ttx`, mode 0700) and
the configuration directory `/etc/ttx`. It includes two `rc.d` scripts: one runs
`llama-server` with the TTX model, and one runs `ttxd`. Weights do not ship in the
package. `ttx fetch` downloads the models separately.
