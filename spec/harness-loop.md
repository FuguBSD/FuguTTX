# Harness loop

This document is a part of the [harness](harness.md) specification.

<a id="hrn-loop"></a>

## The agent loop

The parent operates the perceive → plan → act → observe loop as one synchronous
while-loop. Two terms are fixed:

- A **turn** is one model call plus the execution of its tool call.
- A **step** is one operator prompt and all of its turns.

Five rules control the loop:

- **HRN-LOOP-1 — The transcript drives the loop.** The parent appends each event
  to the session transcript before it acts on the event. At the top of each
  turn, the parent derives its next action from the transcript. It keeps no loop
  state outside the transcript. A restarted daemon can therefore resume a
  session from the transcript alone.
- **HRN-LOOP-2 — Budgets are checked before each model call.** The
  [failure budgets](#failure-budgets) table defines each budget.
- **HRN-LOOP-3 — A turn has exactly one tool call.** The llama-server grammar
  enforces the count. The parent executes tool calls strictly serially. The loop
  has no subagents, no nesting, and no parallel execution.
- **HRN-LOOP-4 — The terminal tool ends the step.** The model ends a step with
  one `report` call that carries its answer. The grammar forces a tool call on
  each turn, so a reply without a call cannot end the step. The grammar and the
  stop condition are therefore one joint design. When the turn budget is
  exhausted, the harness makes one final model call that permits only the
  `report` tool. So each step ends with a report.
- **HRN-LOOP-5 — Errors divide into two classes.** A harness or transport
  failure is fatal: the step stops, and the operator sees the error. Model
  misbehavior becomes a tool result with precise error text, and it spends
  budget from the failure table. Such misbehavior is a malformed call, an
  unknown tool, invalid arguments, an empty response, or a repeated call. Model
  misbehavior must not crash the loop.

<a id="hrn-cancel"></a>

### Cancellation

The operator can cancel a step through the client at any time. On a cancel, the
parent must not start a new model call. The parent starts each tool in its own
session, so the tool leads a process group. It kills that group with
`Fugu::Process->terminate`, in the process-group form: a `SIGTERM`, a grace
period, then a `SIGKILL`. The parent appends a synthesized error result for each
unanswered tool call. So no tool call in the transcript lacks a result. The
process-group form must exist in the installed distribution, and the minimum
version of [HRN-PKG](harness-safety.md#hrn-pkg) covers it. This specification
does not fix the abort mechanism for an in-flight model generation.

<a id="hrn-live"></a>

### Liveness

CPU generation is slow, and the harness does not stream tokens. The frontend
therefore relays one coarse event per loop stage to the client. The events are
model call started, tool started (with the tool name), and confirmation pending.
These events are transient. They do not enter the transcript. The client shows
each event through the `Fugu::REPL` module
([HRN-REPL](harness-repl.md#hrn-repl)). The module writes a transient status
line, and it then restores the prompt line and the cursor. An event text must
not enter the input history.

<a id="hrn-invoke"></a>

## Model invocation

Each turn makes one blocking chat-completions request. The harness does not
stream.

- **HRN-INVOKE-1 — Sampling.** Temperature 0 for tool-driven turns. This value
  is a starting point. The evaluation suite validates the sampler settings
  ([evaluation](evaluation.md)).
- **HRN-INVOKE-2 — Transport retry.** At most 3 retries per request, with
  exponential backoff (2 s, 4 s, 8 s), between the loop and llama-server. Every
  retry budget must have a cap.
- **HRN-INVOKE-3 — Timeout.** The HTTP timeout is fixed. Its value derives from
  measurement: the maximum output tokens divided by the measured tokens/s, plus
  the prompt-processing time, with margin. Until the measurement exists, the
  value is 600 s.
- **HRN-INVOKE-4 — Prompt-cache discipline.** CPU prompt processing is the slow
  axis, and llama-server reuses the KV cache for a byte-stable prefix. The tool
  list sorts by name. No timestamp in the prompt is finer than the hour. Within
  a step, the prompt only appends. It never rewrites.
- **HRN-INVOKE-5 — Token budgeting.** The harness must know the prompt size
  before each send. Base Perl has no tokenizer. The llama-server `/tokenize`
  endpoint is the candidate mechanism.
- **HRN-INVOKE-6 — No context shift.** llama-server must run with context shift
  off. A silent context shift breaks the invariant that the transcript equals
  the model context, and the audit design depends on that invariant. On
  overflow, the harness compacts, or it stops with an error (see
  [context management](#context-management)).

<a id="hrn-prompt"></a>

## Prompt assembly

The harness assembles the prompt from a fixed chunk order. The order is the
system prompt, the operator instruction file, the skill list, and the messages
that derive from the transcript. A fixed order maximizes prefix-cache reuse. The
skill list comes from the skills mechanism ([HRN-SKILLS](#hrn-skills)).

- **HRN-PROMPT-1 — System prompt.** At most 700 tokens: the agent identity, one
  line per tool from the tool metadata table, and the loop rules.
- **HRN-PROMPT-2 — Operator instruction file.** One file,
  `/etc/ttx/instructions.md`, with a budget of 4,096 bytes. The harness
  truncates the file at the budget, and it logs a warning. There is no directory
  walk and no file stacking.
- **HRN-PROMPT-3 — Cadence.** The harness reads the instruction file once per
  step. The assembled prompt stays byte-stable across the turns of one step.
- **HRN-PROMPT-4 — Lockstep with training.** The system prompt, the tool
  schemas, the error templates, and the re-prompt texts are training-time
  artifacts. The SFT trace generator must use the same artifacts
  ([training](training.md)). A change to one of them is a training-data change,
  not only a harness change.

<a id="hrn-skills"></a>

## Skills

A skill is a stored procedure for one task, in the published `SKILL.md`
convention.

- A skill lives in `/etc/ttx/skills/<name>/SKILL.md`: frontmatter between `---`
  lines, then a markdown body. The `name` field must match the directory name:
  lowercase `[a-z0-9-]`, at most 64 characters. The `description` field is
  required, at most 1,024 characters. `Fugu::File->valid_name` refuses a name
  that is not one safe path component, and `Fugu::File->read` reads the file.
  The harness checks the character set and the length itself, because the rule
  above is narrower than one path component. A base-Perl line parser reads the
  `key: value` frontmatter. No YAML module is necessary. The parser stays in the
  harness, because the `key: value` frontmatter is not the OpenBSD configuration
  grammar of `Fugu::Config`.
- The system prompt lists only the name and the description of each skill.
- The trigger is deterministic. The operator invokes a skill by name, or the
  harness matches an optional frontmatter `triggers` keyword list against the
  operator prompt. The model must not select skills from a catalog. A 4B model
  follows a "read the file yourself" instruction weakly.
- An invocation can carry arguments. The harness substitutes `$ARGUMENTS` and
  `$1` to `$n` in the body before injection. So a skill is a reusable runbook.
- The harness injects the skill body into the step as a context message. The
  body budget is 4,096 bytes. The harness truncates above it, and it logs a
  warning.

The instruction file and each skill body are prompt text only. The harness must
not execute a command that this text names. Only a model-proposed tool call,
through every gate, reaches execution. An instruction file must not become an
execution channel.

<a id="hrn-budgets"></a>

## Failure budgets

One table defines every recovery path and its budget. No retry path exists
outside this table. The values are starting points. The evaluation suite
validates them ([evaluation](evaluation.md)).

| Recovery path                   | Budget                                                | At the budget                                        |
| ------------------------------- | ----------------------------------------------------- | ---------------------------------------------------- |
| Malformed or invalid tool call  | 1 re-prompt per step                                  | The step stops.                                      |
| Length-stop response            | Shares the malformed-call re-prompt; nothing executes | The step stops.                                      |
| Empty model response            | 2 retries per step                                    | The step stops with a fixed message.                 |
| Identical consecutive tool call | 2 repeats; the third identical call does not execute  | The step stops and fails closed.                     |
| Transport failure               | 3 retries per request, exponential backoff            | The step stops with the transport error.             |
| Turns per step                  | 20                                                    | One final call permits only `report`. The step ends. |
| Context overflow inside a step  | 1 compaction                                          | The step stops with an error.                        |

Two calls are identical when they have the same tool name and byte-identical
canonical arguments. A detected repetition has one response: stop the step,
report to the operator, and fail closed. The harness must not recover
automatically, and it must not refuse one call and continue. The operator
decides whether to continue.

<a id="hrn-context"></a>

## Context management

The model window is a projection, derived at read time from the append-only
transcript. History is never rewritten. An elision or a summary appends a
superseding record that names the ordinals it supersedes, and the projection
skips the superseded records.

- **Primary mechanism: deterministic elision.** Keep the last four tool results
  verbatim. Replace each older tool result with a one-line stub that names the
  tool and the count of omitted lines. This mechanism is deterministic, needs no
  model call, and stays auditable.
- **Secondary mechanism: a model-written summary.** For whole-session overflow
  only. The harness summarizes with the same model and all tools disabled. It
  keeps a verbatim tail of approximately 1,000 tokens, and it appends the
  summary as an explicit transcript record.
- **Cadence.** Elision and summary run between steps, at a prompt boundary,
  where one full prompt re-process is acceptable. Within a step, the prompt only
  appends (see [model invocation](#model-invocation)). The one exception is the
  mid-step overflow compaction in the failure table.

<a id="hrn-transcript"></a>

## Session transcript

One append-only JSONL file per session is the session record:
`/var/log/ttx/session-<id>.jsonl`. The directory `/var/log/ttx` has owner `_ttx`
and mode 0700. Each file has mode 0600. The transcript is the audit log. A
session file never changes after the session ends, so a retention job can remove
old files safely. This specification does not fix the append discipline.

- **Envelope.** Each record is one JSON object on one line, with a timestamp, a
  monotonic ordinal, a type, and a payload. Ordinals are strictly consecutive. A
  gap or a malformed line fails the load, loudly.
- **Record types.** Session meta (format version, peer user id), operator
  prompt, and model response (with usage counts and finish reason). Tool call,
  tool result (with exit status and output), and confirmation (peer user id and
  digest). Elision, summary, error, and session end.
- **Persistence policy.** Turn boundaries, model-visible content, tool calls,
  executed commands, exit statuses, confirmations, and usage counts persist.
  Transient progress events go to the client only.
- **Record size cap.** A tool-result record keeps the full tool output, up to a
  hard cap of 65,536 bytes per record. Above the hard cap, the record keeps the
  head and the tail, with a marker. No spool directory exists. So the parent
  unveil table stays a complete enumeration.
- **Three consumers, one file.** The model context, client replay, and the audit
  all derive from the transcript. Replay is side-effect-free. It never
  re-executes a tool. A replayed event carries a replay mark, so the client
  cannot confuse it with a live event.
- **Crash record.** On a fatal error, the parent appends an error record before
  it exits. So the transcript records the crash.
- **Usage accounting.** Each model-response record embeds the usage counts that
  llama-server returns. Totals derive from the transcript. No second store
  exists.
- **Syslog duplicate.** The parent writes each record to `syslog(3)` as a
  redacted summary. The key=value field names reuse the OpenTelemetry `gen_ai.*`
  vocabulary (for example `gen_ai.usage.input_tokens`), without the OTLP
  transport. The audit rules of
  [HRN-SAFE-AUDIT](harness-safety.md#hrn-safe-audit) govern this duplicate.
- <a id="hrn-wirelog"></a>**Raw wire log.** The model process appends each raw
  request body and each raw response to a per-session wire log,
  `/var/log/ttx/wire-<id>.jsonl`. The parent opens the file in append mode
  before the fork, and the model process inherits the descriptor. The parent
  starts a fresh model process for each session. So each session has its own
  wire-log descriptor, its own connection, and a fresh address-space layout. A
  write to an open descriptor sits inside the `stdio` promise, so the
  model-process pledge does not widen. The wire log holds everything the model
  saw. Forensics for a malformed call needs the exact prompt bytes, not a
  paraphrase. The wire log has the same confidentiality as the transcript: owner
  `_ttx`, mode 0600 ([HRN-SAFE-CONFID](harness-safety.md#hrn-safe-confid)).
