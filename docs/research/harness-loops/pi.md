# Pi: harness loop design

Date: 2026-08-07. Status: research note. This note changes no code and no
specification. Part of the [harness loop research](index.md).

| Field | Value |
| --- | --- |
| Repository | <https://github.com/badlogic/pi-mono> (site: <https://pi.dev>) |
| Inspected ref | `666d8972ff0b6da5067e05973249760964194769` (v0.84.0, 2026-08-07) |
| License | MIT |
| Language | TypeScript (Node.js and Bun) |
| Loop size | `packages/agent/src/agent-loop.ts`, 796 lines; the loop function itself is 121 lines |
| Verification | An independent pass checked 12 load-bearing claims against the source. Reliability: high. |

## 1. What Pi is

Pi is a minimal, self-extensible coding agent by Mario Zechner, maintained under
Earendil Inc. The monorepo holds the packages `agent` (loop, sessions, compaction,
four base tools), `ai` (multi-provider LLM API), `coding-agent` (CLI and TUI), and
`client`, `protocol`, `server`, `session-backends`, `telemetry`, `tui`, and `evals`.
The design principle is "primitives over features". The default system prompt with
the four base tools (read, bash, edit, write) fits in about 1,000 tokens.
Pi omits MCP, subagents, plan mode, permission popups, and background shells by
design. Users add capability through TypeScript extensions, markdown skills, and
prompt templates. Sessions are append-only JSONL files.
Inference from the design: Pi treats a transparent context window as the primary
requirement. Every byte that reaches the model is inspectable.

## 2. The loop

One function, `runLoop()`, implements the whole control flow
(`agent-loop.ts:155-275`). Two entry points share it: `agentLoop()` starts from a
new prompt, and `agentLoopContinue()` resumes after tool results.

The structure is an outer `while (true)` and an inner
`while (hasMoreToolCalls || pendingMessages.length > 0)`. One inner iteration is
one turn. A turn does six steps:

1. Inject queued "steering" messages from the operator.
2. Call the LLM once (`streamAssistantResponse()`).
3. Filter the `toolCall` content blocks from the assistant message.
4. Execute the calls (`executeToolCalls()`).
5. Emit `turn_end`.
6. Run the optional hooks `prepareNextTurn` (this hook can swap the context or the
   model between turns) and `shouldStopAfterTurn`.

The loop stops on four conditions:

- The assistant message contains no tool call.
- The stop reason is `error` or `aborted`.
- The `shouldStopAfterTurn` hook returns true.
- Every tool result in a batch sets `terminate: true`.

Before the final stop, the outer loop drains a follow-up queue. A queued user
message restarts the inner loop. The loop polls steering input once per turn, so
operator input lands between turns, never inside one.

The loop emits typed events (`agent_start`, `turn_start`, `message_start/update/end`,
`tool_execution_start/update/end`, `turn_end`, `agent_end`) through an event stream.
The `Agent` class folds these events into observable state and holds the transcript.

The core loop has no maximum-turn counter, no tool-call cap, and no wall-clock
timeout. The verification pass confirmed this by search. Termination is
model-driven, plus the hooks, plus an abort signal that threads through every layer.
The loop checks the signal before and after hooks, inside tool execution, and inside
retry backoff sleeps. An abort inside a tool batch breaks out after the current
tool. The resume path must then repair a transcript tail that ends in an assistant
message with unanswered tool calls; `agentLoopContinue()` refuses such a tail.

The loop is synchronous in shape. The async code only wraps streaming. A Perl
while-loop with the same four stop conditions reproduces the control flow exactly.

## 3. Instructions

`loadContextFileFromDir()` tries, in order: `AGENTS.override.md`, `AGENTS.md`,
`AGENTS.MD`, `CLAUDE.md`, `CLAUDE.MD`. The first hit wins per directory.
`loadProjectContextFiles()` loads the global agent directory (`~/.pi/agent`) first.
It then walks from the working directory up to the filesystem root and prepends each
ancestor file. The root-most file comes first, and the working-directory file comes
last. It deduplicates paths and skips a git-worktree copy that shadows the main
repository file.

`buildSystemPrompt()` assembles, in order: the base prompt (identity, one line per
tool, guidelines), an optional append text, all context files wrapped in
`<project_context>` and `<project_instructions path="...">` tags, the
`<available_skills>` list, and `Current working directory: <cwd>` as the final line.
A project `SYSTEM.md` replaces the default prompt. An `APPEND_SYSTEM.md` appends to
it. Pi reads the files once at session start. The `/reload` command re-reads them.
Nothing re-reads per turn. Project-local resources load only after the user trusts
the project.

## 4. Skills and extension

Three mechanisms add capability. None changes the harness.

- **Skills.** `SKILL.md` files with YAML frontmatter. The loader validates: the name
  must match the parent directory, lowercase `[a-z0-9-]`, maximum 64 characters; the
  description is required, maximum 1,024 characters. An invalid skill produces a
  warning, not a failure. The system prompt holds only name, description, and file
  path per skill. The prompt tells the model to read the full skill file with its
  own read tool when the task matches. Skill bodies never load until needed.
- **Prompt templates.** Markdown files in `~/.pi/agent/prompts/` or `.pi/prompts/`.
  The filename becomes a `/name` command. Bodies expand `$1`, `$@`, and
  `${1:-default}` arguments.
- **Extensions.** TypeScript modules, hot-reloadable. An extension can register
  tools and commands, and it can subscribe to events. The `tool_call` event can veto
  a call (`{block: true, reason}`). The `tool_result` event can rewrite a result.
  Permission gates are not built in; the documentation shows them as a five-line
  `tool_call` handler. Pi has no MCP support by design.

The verification pass added a third hook point: a tool can declare
`prepareArguments`, which rewrites arguments before validation.

## 5. LLM interface

The loop depends on one function type: `StreamFn(model, context, options)` returns
an event stream. The loop never imports a provider. The context is
`{systemPrompt, messages, tools}`. The stream yields typed deltas and a growing
partial assistant message. The final message carries a stop reason in
`{stop, length, toolUse, error, aborted}` and usage counts (input, output, cache
read, cache write, cost). Two per-call hooks, `transformContext` and `convertToLlm`,
run once per LLM call, so the in-memory transcript is not the wire format.

The provider relevant to FuguTTX is `api/openai-completions.ts`, which serves
llama.cpp: it reads the llama.cpp `reasoning_content` field and supports
`chat_template_kwargs`. The module `constrained-sampling.ts` supports
grammar-constrained tool input (a lark or regex grammar over one string property).
This is sample-time constraint of tool calls, the same idea as the ttx plan.
`docs/llama-cpp.md` documents the llama-server setup, with `--jinja` for tool calls.

Retries: `retryAssistantCall()` classifies errors with two regex lists. Overloaded,
429, 5xx, timeout, and socket errors retry. Quota and billing errors are terminal.
The coding-agent app layer defaults to 3 retries with 2 s, 4 s, 8 s backoff. The
bare library layer defaults retries off. An abort never retries.

Compaction: auto-compaction triggers when the context tokens exceed the context
window minus a reserve (default 16,384 tokens). It keeps the newest ~20,000 tokens.
It cuts only at a user, assistant, bash-execution, or summary message, never at a
tool result; a cut can split a turn. The summary is structured markdown (Goal, Progress, Next Steps,
file lists). Tool results truncate to 2,000 characters inside the summarization
prompt. Compaction calls opt out of the prompt cache.

## 6. Tool calls

Tools carry TypeBox JSON schemas. Streamed argument JSON finalizes through a salvage
parser (`partial-json` plus a repair pass), so slightly malformed JSON still parses
when possible. `validateToolArguments()` first coerces types (`"5"` becomes 5), then
validates with a compiled checker. On failure it throws an error that names each bad
path and echoes the received arguments. The loop converts every failure into an
error tool result and continues. The model sees the message and re-issues the call.
An unknown tool name yields the error result `Tool X not found`.

Dispatch runs three phases: `prepareArguments`, validation, and the `beforeToolCall`
gate. The verification pass confirmed that this preflight runs sequentially in
source order even in parallel mode; only `tool.execute()` runs concurrently.
Parallel execution is the default. The whole batch runs sequentially when the
configuration or any called tool declares `executionMode: "sequential"`.
A tool result can add new tools mid-run (`addedToolNames`), so the tool set can grow
during a session. No per-tool timeout exists; a timeout is each tool's own job.

Critical guard: when the assistant message has stop reason `length`, the loop fails
every tool call in it with "arguments may be truncated. Re-issue the tool call", and
nothing executes. Salvage-parsed arguments can validate and still be incomplete.

Result truncation applies two independent limits: 2,000 lines and 50 KB, whichever
hits first. Truncation does not emit partial lines, with one documented exception
for bash tail truncation. Grep matches cap at 500 characters per line.

## 7. Observability and state

Sessions persist as append-only JSONL under `~/.pi/agent/sessions/`, one typed JSON
object per line. Entries form a tree through `id` and `parentId` fields. A header
line carries a format version, and old files migrate on load. Entry types:
`message`, `model_change`, `thinking_level_change`, `active_tools_change`,
`compaction`, `branch_summary`, `custom`.

The newer harness session layer adds a second record stream beside the entries:
`operation_started/finished` (with outcome `completed|aborted|failed|declined`),
`step_attempt`, `tool_started` (with effective arguments and a
`replay: "never" | "safe"` marker), `queue_enqueued/cancelled`, and `usage` records
attributed to a cause (assistant, tool, compaction, hook). The state loader
validates strictly consecutive sequence numbers and parent links, so a corrupt line
fails loudly. Crash recovery counts open operations: zero means idle, one means
suspended, two means corruption.

Every assistant message stores its own usage and stop reason. Totals derive from the
records. Context rebuild on resume starts from the newest compaction entry and
replays messages from `firstKeptEntryId` onward. Compaction is itself a persisted
entry, so a resumed session reproduces exactly what the model saw. Model changes are
entries too, so the history is a complete replay log of configuration and
conversation. The entry/record split separates "what the model saw" from "what the
harness did".

## 8. Errors and limits

Budgets do not exist in the core loop (see section 2). Malformed tool calls are
unbounded in principle: each validation failure returns an error result, and the
loop continues. Pi relies on a frontier model to self-correct.

Context overflow: on stop reason `length` or a context-overflow error, the app layer
removes the failed assistant message from agent state (it stays in history),
compacts, and retries once. A flag makes a second consecutive overflow a hard error.

Inference: the missing caps are the main place where Pi assumes a strong model. A 4B
model can ping-pong on validation errors without progress. The fixed ttx budgets
must stay.

## 9. Lessons for ttx

1. Write the loop as one function with explicit stop conditions: repeat turns while
   the assistant message contains tool calls; stop on a no-tool-call reply, on
   error or abort, or on a policy hook. Pi shows the whole control flow in 121
   lines, and it ports to a synchronous Perl while-loop with no event machinery.
2. Adopt the length-stop guard. When llama-server reports that the output hit the
   token limit, fail every tool call in that message with "arguments may be
   truncated, re-issue the call", and execute nothing.
3. Return validation failures to the model as tool results that name each bad field
   and echo the received arguments. Pi sets no cap on this; ttx must keep its fixed
   one-re-prompt budget.
4. Keep the system prompt near 1,000 tokens: identity, one line per tool, project
   instruction files in fixed tags, working directory last. Pi proves that a
   minimal prompt with four tools is a workable harness contract.
5. List skills in the prompt as name, description, and path only. Load a skill body
   only on invocation. A 4B model follows "read the file yourself" weakly, so ttx
   should inject the skill body from the harness on invocation.
6. Truncate tool output with two independent limits — lines and bytes, whichever
   hits first — and state in the result what was cut. Tune the numbers down for a
   small context.
7. Persist the session as append-only JSONL with strictly consecutive sequence
   numbers, per-call usage records, and a replay-safety marker on each executed
   tool. The entry/record split matches the ttx audit requirements.
8. Do not copy the parallel tool execution or the absence of budgets. The ttx
   gates are order-dependent, and a small model needs fixed caps.

## Sources

- <https://pi.dev> and <https://pi.dev/docs/latest>
- Shallow clone of <https://github.com/badlogic/pi-mono> at
  `666d8972ff0b6da5067e05973249760964194769`; files cited in the text, in
  particular `packages/agent/src/agent-loop.ts`,
  `packages/agent/src/harness/skills.ts`,
  `packages/coding-agent/src/core/resource-loader.ts`,
  `packages/coding-agent/src/core/system-prompt.ts`,
  `packages/ai/src/utils/validation.ts`, `packages/ai/src/utils/retry.ts`,
  `packages/agent/src/harness/utils/truncate.ts`,
  `packages/agent/src/harness/compaction/compaction.ts`,
  `packages/agent/src/harness/session/{types,state}.ts`
- Package documentation: `docs/skills.md`, `docs/extensions.md`,
  `docs/prompt-templates.md`, `docs/session-format.md`, `docs/compaction.md`,
  `docs/llama-cpp.md`, `docs/rpc.md`
- Armin Ronacher, "Pi" (design write-up): <https://lucumr.pocoo.org/2026/1/31/pi/>
