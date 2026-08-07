# OpenAI Codex CLI: harness loop design

Date: 2026-08-07. Status: research note. This note changes no code and no
specification. Part of the [harness loop research](index.md).

| Field | Value |
| --- | --- |
| Repository | <https://github.com/openai/codex> |
| Inspected ref | `0bdce9f424eb` (main, 2026-08-07; release v0.147.0 the same day) |
| License | Apache-2.0 |
| Language | Rust (Tokio workspace, `codex-rs`, 100+ crates) |
| Loop size | `codex-rs/core/src/session/turn.rs`: 2,746 lines; codex-core ≈ 189k lines |
| Verification | An independent pass checked 12 load-bearing claims against the source. Zero refutations. Reliability: high. |

## 1. What it is

Codex CLI is OpenAI's open-source terminal coding agent. The design splits a core
engine (codex-core) from all user interfaces. UIs (TUI, headless `codex exec`, MCP
server, app-server) drive the core over an internal protocol: a Submission Queue of
`Op` requests and an Event Queue of `EventMsg` events, correlated by a string id.
This core/UI split is close in spirit to `ttxd`/`ttx`. The core owns policy:
sandbox selection, approval gates, an optional LLM "guardian" reviewer, execpolicy
rules, and JSONL rollout recording. The philosophy: the model proposes, the harness
disposes; every action passes typed policy checks, and every item is persisted for
replay.

## 2. The loop

Control flow has three layers:

1. **`submission_loop`** receives `Submission{id, op}` from the UI and dispatches:
   `Op::UserInput` starts a task, `Op::Interrupt` aborts, `Op::Shutdown` exits.
2. **`Session::spawn_task`** first aborts any active task (one task per session,
   with abort reason "Replaced"), then spawns the task. Task kinds: regular,
   compact, review, user shell command.
3. **`run_turn`** is the agent loop. Its doc comment states the contract: each
   sampling request returns function calls or an assistant message; the harness
   executes the calls and sends outputs back in the next request; a message-only
   response ends the turn.

Each iteration: drain queued user input (mid-turn "steering"); capture a step
context (tools, environment, MCP servers for this request); clone history into the
prompt input; run the sampling request; then compute
`needs_follow_up = tool call seen || pending input`. If the token limit is reached
and follow-up is needed, run inline auto-compaction and continue. If no follow-up
is needed, run the stop hooks. A stop hook can block completion and inject a new
prompt message, which continues the loop. A one-shot flag prevents an infinite
stop-hook loop. A fail-open guard applies: the loop ignores a hook that blocks
without a continuation prompt, and it logs a warning. Exit paths: normal completion (the
turn's product is one string, the last agent message); a non-retryable error
(emit an error event, break, the session stays usable); or cancellation (a token
fires, and an interrupted-turn marker is written into history so the model sees
the abort).

Inference: despite the async runtime, the loop is logically sequential — one
sampling request at a time, tool outputs ordered — so the shape ports to
synchronous Perl directly.

## 3. Instructions

Base instructions are static markdown files chosen per model family (the default
is 275 lines). Project instructions come from `AGENTS.md`: find the project root by
walking up from the working directory to a marker (default `.git`); collect files
from the root down to the working directory, checking `AGENTS.override.md` first,
then `AGENTS.md`, then configured fallback names; concatenate in root-to-cwd order
under one total byte budget (`project_doc_max_bytes`, default 32 KiB); truncate the
file that crosses the budget and log a warning. A user-level file in `$CODEX_HOME`
joins with the separator `--- project-doc ---`.

Codex injects the result as a user-instructions context message, not into the
system prompt. This choice keeps the system prompt stable for prompt caching. A manager caches
the loaded set and re-reads only when the cwd selection changes, not on every
turn. Additional layered context arrives as typed "contextual user fragments":
environment context, permission instructions, current-time reminders, token-budget
warnings, and turn-aborted markers.

## 4. Skills and extension

Four mechanisms add capability without harness changes:

- **Skills.** `SKILL.md` files under `$CODEX_HOME/skills` and plugin roots. Skills
  inject only on explicit mention: the loop scans the user input for skill names
  and injects the matched skill bodies as user-message fragments for that turn.
  A skill can declare MCP dependencies, installed with user consent.
- **Hooks.** Eleven lifecycle events (PreToolUse, PermissionRequest, PostToolUse,
  PreCompact, PostCompact, SessionStart, SessionEnd, UserPromptSubmit,
  SubagentStart, SubagentStop, Stop) that run external commands. A hook can
  reject user input or block turn completion. An admin flag can restrict hook
  sources.
- **MCP client.** Startup timeout 30 s; tool-call timeout 300 s. Servers for
  mentioned plugins load lazily per turn.
- **Plugins, connectors, execpolicy rule files, and TUI slash commands.**

Inference: the explicit-mention gate is the key idea — skill text costs context
only when the user names the skill. That is cheap in Perl: scan input for names,
slurp a file, append a user message.

## 5. LLM interface

At this commit Codex speaks only the OpenAI Responses API. The wire-API enum has a
single variant, and the old `chat` value returns a removed-feature error. Local
models must expose `/v1/responses`; the Ollama integration refuses versions
without it. Consequence for ttx: the wire protocol cannot be copied — llama-server
exposes chat completions, the shape Codex abandoned.

Requests stream over SSE. Retries are bounded: stream retries default 5, request
retries default 4, both with hard caps on user overrides; the stream idle timeout
is 300 s. A stream that closes before completion is an error and retries, with the
prompt input rebuilt from history.

Context management: after every response the loop computes the context-window
token status. When the auto-compact limit or the window is reached, compaction
runs pre-turn or mid-turn. Local compaction sends history plus a static
summarization prompt, then rebuilds history as: initial context, plus the most
recent user messages capped at about 20,000 tokens, plus the summary. Compaction
persists its replacement history, so a resumed session continues with the exact
post-compaction context. Prompt caching relies on an append-only history prefix.

## 6. Tool calls

Tool specs are JSON-Schema function definitions. A per-step tool router supplies
the model-visible specs. When the stream yields a completed call item, the handler
records it, marks follow-up, and pushes an execution future into an ordered queue;
tools run while the stream continues, but results drain in call order after the
response completes. Parallel-safe tools take a shared read lock; serial tools take
the write lock, which serializes them.

The error contract: `RespondToModel(text)` becomes a `function_call_output` sent
back to the model on the next request; `Fatal` ends the turn. Unknown tools return
the string `unsupported call: {name}`. There is no fixed malformed-call counter
and no per-turn tool-call cap; token budgets and the interactive user bound
runaway loops indirectly.

Approval gate: a mapping function takes the approval policy (untrusted /
on-request (default) / granular / never) and the sandbox state, and returns Skip,
NeedsApproval, or Forbidden — before execution. The exec tool schema itself
carries the escalation protocol: `sandbox_permissions` in {use_default,
with_additional_permissions, require_escalated}, plus a `justification` (the
user-facing approval question) and a `prefix_rule` (a reusable approval prefix
such as `["git","pull"]`). A sandboxed failure can escalate and retry unsandboxed
after approval. The UI answers approval requests with a typed decision: Approved,
ApprovedForSession, Denied{rejection}, TimedOut, Abort, and two amendment
variants. An optional guardian LLM reviewer auto-decides on-request approvals from
strict JSON and fails closed on timeout or malformed output.

Exec limits: command timeout 10 s default (exit code 124 on timeout), SIGKILL with
a 50 ms grace period on cancellation, a 2 s I/O drain guard against grandchildren
holding pipes open, output truncated to a default budget of 10,000 tokens per call
(model-tunable downward) plus a 1 MiB hard byte cap.

## 7. Observability and state

Every session writes an append-only JSONL rollout:
`~/.codex/sessions/YYYY/MM/DD/rollout-{timestamp}-{uuid}.jsonl`. Line payloads are
typed: session meta (id, cwd, git info, base instructions, fork origin), response
items (every model-visible item), compacted records (summary plus replacement
history plus a context-window id chain), turn context (cwd, model, permission
profile per user turn), world state, and a persisted subset of events. A policy
function decides durability per event type: turn boundaries and token counts
persist; streaming deltas and approval prompts do not. The recorder buffers writes
and flushes before a turn completes; a flush failure emits a visible warning and
retries. A SQLite database only indexes sessions for listing — the JSONL file is
the session.

Resume reopens the file and rebuilds model-visible history, honoring compacted
replacement histories and turn-context baselines. Forking truncates to the last
sampling boundary and records the parent id. A separate `~/.codex/history.jsonl`
keeps one JSON object per user message across sessions.

The UI sees the full lifecycle as events: turn started, item started/completed,
exec begin/output-delta/end, MCP call begin/end, approval requests, token counts,
a turn diff (a unified diff of all file changes in the turn), errors, and turn
complete/aborted. OpenTelemetry spans wrap the turn, each sampling request, and
each tool call with `gen_ai.usage.*` fields.

## 8. Errors and limits

Budgets: a rollout token budget can end a session, with reminder fragments
injected before that; an auto-compact limit triggers compaction; a context-window
overflow forces compaction or error. Timeouts: exec 10 s, MCP 300 s, stream idle
300 s. Retries are bounded per provider. Cancellation: a cancellation-token tree
spans turn, sampling request, and each tool; aborted tools record synthetic
aborted outputs so history stays consistent. Guardian denials feed a per-turn
rejection circuit breaker.

Inference: Codex bounds runaway loops indirectly (token budgets, compaction, an
interactive user). An unattended 4B model has none of these, so the fixed ttx
budgets are stricter than Codex by design and must stay.

## 9. Lessons for ttx

1. Adopt the two-outcome turn contract: continue the loop only when a tool call
   happened or new user input is queued; a message-only response ends the turn.
   One boolean in synchronous Perl.
2. Adopt id-correlated submission/event framing between `ttxd` and `ttx`: every
   client request carries an id, and every event echoes it. Length-prefixed JSON
   over the control socket reproduces this with JSON::PP alone.
3. Adopt the typed JSONL rollout (session-meta, item, compacted, turn-context
   lines) with a persistence-policy function, flushed before turn completion.
   Resume equals replay of the file, and the same file serves as the ttx audit
   artifact.
4. Adopt error-as-tool-output with fixed strings ("unsupported call: NAME") and a
   fatal/respond split. Keep the hard ttx one-re-prompt counter on top, because
   Codex has no per-turn call cap.
5. Copy the escalation-protocol shape for mutations: the tool schema itself
   carries the permission request and a user-facing justification, and the
   harness maps policy × state to Skip/NeedsApproval/Forbidden before execution.
   This maps one-to-one onto the ttx dry-run plus confirmation digest before the
   doas wrappers.
6. Truncate tool output in the harness with an explicit budget and a hard byte
   cap. Set a far smaller default than 10,000 tokens for a 4B window.
7. Port local compaction as a fixed recipe: summarize with a static prompt, then
   rebuild history as initial context plus the last user messages under a token
   cap plus the summary. Shrink the keep-budget to fit the 4–8K context.
8. Avoid the async machinery: parallel tool futures, streaming delta events, and
   WebSocket reuse presume Tokio and a strong model. Codex drains tool results in
   call order anyway, so a strictly serial execute-then-return loop loses no
   correctness.

## Sources

- Clone at `0bdce9f424eb`. Key files: `codex-rs/core/src/session/turn.rs`,
  `core/src/session/handlers.rs`, `core/src/tasks/{mod,regular}.rs`,
  `core/src/agents_md.rs`, `core/src/agents_md_manager.rs`,
  `core/src/tools/{sandboxing,registry}.rs`,
  `core/src/tools/handlers/shell_spec.rs`, `core/src/compact.rs`,
  `core/src/exec.rs`, `core/src/unified_exec/mod.rs`,
  `core/src/guardian/mod.rs`, `core-skills/src/loader.rs`, `hooks/src/lib.rs`,
  `rollout/src/{recorder,policy,state_db}.rs`, `protocol/src/protocol.rs`,
  `model-provider-info/src/lib.rs`, `codex-rs/docs/protocol_v1.md`
- <https://learn.chatgpt.com/codex/agent-approvals-security>
- <https://learn.chatgpt.com/codex/guides/agents-md>
