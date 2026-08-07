# opencode: harness loop design

Date: 2026-08-07. Status: research note. This note changes no code and no
specification. Part of the [harness loop research](index.md).

| Field | Value |
| --- | --- |
| Repository | <https://github.com/sst/opencode> |
| Inspected ref | `741244b69d5c` (dev branch, 2026-08-07) |
| License | MIT |
| Language | TypeScript (Bun/Node, Effect library, Vercel AI SDK) |
| Loop size | `packages/opencode/src/session/`: 7,172 lines; `runLoop` in `prompt.ts` is ~260 lines |
| Verification | An independent pass checked 12 load-bearing claims against the source. One exit-condition claim was corrected; this note carries the correction. Reliability: high. |

## 1. What it is

opencode is an open-source coding agent from the SST team. It is a client/server
system: `opencode serve` starts a headless HTTP server on 127.0.0.1:4096, with an
OpenAPI spec at `/doc` and a server-sent-event stream at `/event`. The TUI, desktop
app, IDE plugins, and SDK clients all attach to this server. This makes opencode
the closest open-source analogue to the `ttxd`/`ttx` split.

The design philosophy is state-driven: every message and part persists to SQLite
as it streams, and the agent loop re-derives its next action from stored state on
every iteration. Sessions, subagents, compaction, and queued prompts are rows and
parts in the database, not in-memory control flow.

## 2. The loop

`prompt()` writes the user message to the store, then starts the loop through a
per-session runner: one active run per session id. A second prompt during a run
joins the running fiber, and the loop picks the new message up on its next
iteration — the parent-id linkage between user and assistant messages is the
queuing mechanism.

`runLoop` is a `while (true)`. Each iteration:

1. Set the session status to busy.
2. Re-read the full message history from the database, through a filter that
   derives the compacted view.
3. Compute the latest user message, the latest assistant message, and pending
   "task" parts.
4. Test the exit condition. The verification pass corrected this rule. The loop
   breaks only when three conditions hold: the last assistant message contains
   zero client-executed tool parts (provider-executed and orphaned-interrupted
   parts excluded); its finish reason is not "tool-calls"; and it answers the
   last user message.
   A completed tool part still keeps the loop running, because the results must
   go back to the model on the next iteration. A source comment notes some
   providers return "stop" while tool calls are present, so the structural check
   overrides the finish reason.
5. Branch on pending task parts: a `subtask` part runs a child session; a
   `compaction` part runs the compactor.
6. An overflow check on the last finished message can insert a compaction part
   and continue.
7. Otherwise: create an assistant message row, resolve tools, build the system
   prompt, apply per-iteration "reminder" injections, convert history to model
   messages, and drain the LLM event stream through the processor, which returns
   continue, stop, or compact.

A step counter enforces a per-agent step cap (default unbounded). On the last step
the loop appends a request-only assistant message that forbids tool calls and
demands a text summary — prompt-level enforcement, not a tool lockout.

Nesting: the `task` tool creates a child session with a parent id; a depth limit
(default 1) walks the parent chain and fails past the limit. Cancellation
interrupts the session fiber; finalizers stamp the assistant message with an
aborted error and mark running tool parts interrupted.

## 3. Instructions

Assembly happens on every loop iteration.

opencode selects the base prompt from a per-model prompt table by model-id
substring: one static prompt file per model family (anthropic, gpt, codex,
gemini, kimi, and so on, else a default). An agent-level prompt replaces the base prompt entirely.
This per-model prompt table is a direct precedent for tuning one prompt to one
small model. An environment block emits the model id, working directory, git
state, platform, and date inside `<env>` tags.

Project instruction files: global `~/.config/opencode/AGENTS.md` and
`~/.claude/CLAUDE.md`; project `AGENTS.md`, then `CLAUDE.md`, then `CONTEXT.md`
(deprecated). A find-up walk from the working directory to the worktree root
returns the first name that matches — ancestor files do not stack, by an explicit
source comment. Config can add glob paths and URLs (5 s fetch timeout). Each item
becomes a block `Instructions from: <path>`. Because the loop re-reads the files
every iteration, an edit to `AGENTS.md` applies on the next turn without restart.
Nested instructions: the read tool walks upward from any file it reads and
attaches directory-local `AGENTS.md` files once per message, with a claims map for
deduplication.

## 4. Skills and extension

- **Skills.** `SKILL.md` files with frontmatter, discovered under
  `.opencode/skills/**` and external `.claude/skills` and `.agents/skills` trees.
  The system prompt holds names and descriptions only; the model loads a body on
  demand through a `skill` tool, behind a permission gate, and the tool returns
  the body in `<skill_content>` tags plus a sampled file list.
- **Commands.** Markdown templates with `$ARGUMENTS` and `$1..$n` placeholders
  and `` !`shell` `` interpolation executed before prompting. A command can bind
  an agent and a model.
- **Agents.** Markdown or JSON definitions with mode (primary/subagent), step
  cap, permission ruleset, model, and prompt. An agent is a permission ruleset
  plus a prompt — not new code.
- **Plugins.** Hooks: `chat.message`, `chat.params`, `tool.execute.before/after`,
  `tool.definition`, plus experimental system-prompt and compaction transforms.
  Custom tools load from `.opencode/tool/*.ts`.
- **MCP.** MCP tools join the same tool table and the same permission gate; MCP
  server instructions join the system prompt.

## 5. LLM interface

A wrapper around the AI SDK emits a normalized event stream, so the processor is
provider-independent. Retries: the inner call has zero retries; an outer policy
re-runs the whole stream on retryable errors (a regex classifier for 429/5xx and
network strings), honors retry-after headers, and backs off exponentially from 2 s
to a 30 s cap — with no attempt cap. Retries run until the error stops matching or
the user cancels. ttx must not copy the uncapped retry.

Context management: usable context is the input limit minus a reserve
(`min(20000, maxOutputTokens)`). Overflow marks the stream for compaction.
Compaction runs as a hidden agent with zero tools. The compactor serializes the
history to plain text (`[User]: ...`, `[Assistant tool call]: name(json)`,
`[Tool result]: ...`) and caps tool outputs at 2,000 characters. A previous
summary threads in. The compactor preserves a tail of the last 2 turns, within a
budget of 25 percent of usable context, clamped to 2,000–8,000 tokens. The summary is stored
as a normal assistant message flagged as a summary, and the visible window is
derived at read time — full history stays auditable. A prune pass marks old tool
outputs compacted instead of deleting them, protects the newest 40,000 tokens, and
runs only when it can clear more than 20,000.

Prompt caching: ephemeral cache markers on the first two system messages and the
last two non-system messages. For llama.cpp the portable idea is the "static head,
moving tail" split: keep the prefix byte-stable so the server KV cache reuses it.

## 6. Tool calls

Built-in tools declare Effect schemas, converted to JSON Schema per provider. The
tool table is model-conditional (some model families get `apply_patch` instead of
edit/write). The AI SDK validates arguments before execute.

Malformed-call recovery: a repair hook first fixes a lowercased tool name if the
tool exists; otherwise it rewrites the call to a reserved `invalid` tool whose
output is "The arguments provided to the tool are invalid: <error>". The loop then
continues normally — the model receives exactly one corrective tool result per
malformed call, with no special control flow. The `invalid` tool is filtered from
the model-visible tool list, so the model cannot call it directly.

Dispatch: tools execute during the stream, in parallel when the model emits
several calls; a per-part state machine (pending → running → completed | error)
persists with streamed progress.

Truncation: 2,000 lines / 50 KiB caps; overflow writes the full text to a spool
file with 7-day retention, and the result names the file for ranged re-reads.

Permission gate: rules are (permission, pattern, action) triples with wildcard
match; the last matching rule wins; a deny rule fails immediately (deny beats
ask); the default action is ask. An ask suspends the tool until a client replies
once, always, or reject over HTTP. A reject can carry a correction message that
becomes model-visible feedback. The rejection cascades to all pending asks in the
session.

Doom-loop guard: three consecutive tool calls with the same name and
byte-identical JSON arguments trigger a `doom_loop` permission ask.

## 7. Observability and state

Persistence is the observability backbone. Every message and part row is written
as it streams; the same writes publish events on an internal bus, exposed as the
`/event` SSE stream. Any client renders live state by replaying the store and then
following the stream; reconnection is trivial because the store is authoritative.

Message and part ids are generated ascending, so replay order is id order. Parts
are a typed union: text, reasoning, tool (with state machine and timings), file,
step-start, step-finish (tokens, cost, snapshot id), patch, compaction, subtask.
Synthetic parts mark harness-injected text, so user text and harness text stay
distinguishable in the record. One read-time detail matters for a port: the
compaction filter reorders messages for model consumption (compaction marker,
summary, retained tail, continue message) — the model window is synthesized at
read time, not replayed in log order.

Audit of file effects: at step start the processor captures a git-based snapshot;
at step finish it computes a patch and stores a patch part with a hash and the
changed-file list. This powers revert and fork. Accounting: step-finish events
carry usage; message rows accumulate tokens and cost; session rows aggregate.

Because the loop re-reads everything from the store at the top of each iteration,
resume is simply prompting an existing session id, and a crash mid-turn loses only
the in-flight assistant message, which finalizers stamp with an error. Queued work
(subtask, compaction) survives as parts and executes on the next iteration.

## 8. Errors and limits

Numeric budgets: per-agent step cap (default unbounded); subagent depth 1;
doom-loop threshold 3; tool output 2,000 lines / 50 KiB; compaction serializer
2,000 characters per tool output; instruction URL fetch 5 s; retry backoff 2 s ×
2 up to 30 s (uncapped attempts). Cancellation: abort interrupts the fiber; the
processor waits up to 250 ms for in-flight tools, then marks the rest aborted,
closes open parts, and records a final patch part.

The error taxonomy routes each type distinctly: context overflow goes to
compaction (or halts when auto-compaction is off); a content-filter error surfaces
instead of a silent idle; a permission rejection stops the loop unless a
continue-on-deny flag is set. Every halt path writes the error onto the assistant
message row, so failures are part of the transcript.

## 9. Lessons for ttx

1. Drive the loop from persisted state. Write each message and tool result to the
   session log first, and re-read the log at the top of each iteration. Crash
   resume and client attach come free. This works in synchronous Perl with an
   append-only JSON-lines file.
2. Make the exit test structural, not trust-based — with the corrected rule:
   break only when the last assistant message contains zero pending-or-completed
   tool parts awaiting a reply, its finish reason is not "tool-calls", and it
   answers the last user message. A fine-tuned 4B model will also return "stop"
   alongside tool calls.
3. Recover a malformed tool call by routing it to a reserved `invalid` tool whose
   result is the parse-error text. This implements the ttx one-re-prompt budget
   with zero special control flow: the error is just another tool result in the
   transcript.
4. Adopt the doom-loop guard: N identical consecutive calls (same name,
   byte-identical canonical arguments) stop the loop and require operator
   approval. One string comparison per call.
5. Adopt fixed tool-output caps with a spool file for the full output — noting
   the spec obligation: the spool directory must enter the parent's unveil table
   through a specification change in the same commit.
6. Adopt compaction as a plain-text serialized transcript summarized by the same
   model with all tools disabled, keeping a small verbatim tail; store the
   summary as a normal message and derive the window at read time so the audit
   log stays complete.
7. Keep the system prompt byte-stable per session, and load instruction files
   with a first-match-wins walk-up rather than stacking, to protect the 4B
   context budget and the llama.cpp KV-prefix cache.
8. Avoid the uncapped provider retry and the in-stream parallel tool execution.
   Keep fixed retry budgets, and execute tool calls sequentially after the full
   HTTP response is parsed — with one local llama-server, mid-stream dispatch
   buys nothing.

## Sources

- Shallow clone at `741244b69d5c`. Key files:
  `packages/opencode/src/session/{prompt,processor,llm,system,instruction,compaction,overflow,retry,run-state,reminders}.ts`,
  `packages/opencode/src/session/llm/request.ts`,
  `packages/opencode/src/{permission/index,tool/truncate,tool/registry,tool/invalid,tool/skill,skill/index,agent/agent}.ts`,
  `packages/opencode/src/provider/transform.ts`,
  `packages/core/src/session/{sql,runner/max-steps}.ts`
- <https://opencode.ai/docs/agents/>, <https://opencode.ai/docs/server/>,
  <https://opencode.ai/docs/rules/>, <https://opencode.ai/docs/share/>
