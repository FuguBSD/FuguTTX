# goose: harness loop design

Date: 2026-08-07. Status: research note. This note changes no code and no
specification. Part of the [harness loop research](index.md).

| Field | Value |
| --- | --- |
| Repository | <https://github.com/block/goose> |
| Inspected ref | `66051ec7d2ea` (workspace 1.45.0, 2026-08-07) |
| License | Apache-2.0 |
| Language | Rust (tokio, async streams, SQLite through sqlx) |
| Loop size | legacy loop `agents/agent.rs` 5,153 lines + `reply_parts.rs` 1,792 lines; new state machine 4,507 lines in 21 files |
| Verification | An independent pass checked 20 claims against the source. One was refuted; this note carries the corrections. Reliability: high. |

## 1. What it is

goose is an open-source AI agent from Block, now under the Agentic AI Foundation.
The core design is MCP-native: every tool source is an MCP server, called an
"extension", and built-in tools run behind the same interface. The design favors
capability and recoverability: a large default turn budget (1,000), automatic
compaction, mid-session mutation of tools and hints, and 30+ providers behind one
streaming trait. Sessions persist in SQLite. The model never sees raw history; it
sees a projection filtered by per-message visibility flags.

At the inspected commit the team is rewriting the monolithic reply loop into an
ordered, re-entrant operation pipeline (the "state machine", behind the
`GOOSE_STATE_MACHINE` environment gate). This note cites both loops.

## 2. The loop

**The shipped loop** (`Agent::reply` → `reply_impl` → `reply_internal`).
`reply_impl` persists the user message, runs slash commands, and runs a pre-turn
compaction check. `reply_internal` is one async generator that yields agent events.
The outer loop does, in order: check the cancellation token; drain queued "steer"
user messages; check the final-output tool; count the turn; stop when the turn
count passes `max_turns` (default 1,000) with a fixed "may I continue" message;
call the provider; consume the response stream. Tool requests get categorized,
inspected, approved, and executed; tool results become user-role messages. The
loop stops when the model returns text with no tool calls, subject to overrides
(goal nudges, recipe retry logic, a Stop hook that can deny exit up to a cap).
Subagents are tools: a subagent builds a fresh agent from a recipe, runs the same
loop, and returns its final text as the tool result.

**The state-machine loop** (`StateMachine::run`):
`loop { session = get_session(); result = step(); apply(result.effects); break if result.yield_to_client }`.
`step` walks an ordered list of operations; the first applicable operation returns
effects (append message, replace conversation, set message visibility, record
usage, and a few more). Each pass recomputes from persisted state, so the loop is
re-entrant and resumable. The verified operation order is: SlashCommand, Steer,
MaxTurns, BangShell, Compaction, ToolPairCompaction, ToolApproval, Doctor, Project,
Skill, Recipe, ToolExecution, UnknownTool, Retry, StopHook, ExitOnError, and
Inference last. Three design points from the verification pass: every operation can
contribute tools and prompt parts that aggregate into the terminal inference step,
so operations are simultaneously gates and prompt providers; `step()` and `apply()`
are separate public entry points, so an external driver can persist the effects
itself; and retry passes (empty turn, stop-hook denial) do not increment the turn
count.

Inference: the state-machine shape is the portable one for a synchronous Perl
harness. It needs no streams and no concurrency, and it makes every turn resumable
after a crash.

## 3. Instructions

The prompt manager assembles the system prompt each turn: a base template rendered
with the extension catalog, mode, and date; keyed extras appended under a literal
`# Additional Instructions:` heading; hints; and a chat-mode notice when tools are
off. Two cache-friendly details: the extension list sorts by name, and the
timestamp truncates to the hour, with a source comment that names prompt-cache hits
as the reason.

Hint files: global hints from `~/.config/goose/.goosehints` and
`~/.agents/AGENTS.md`; local hints from the git root down to the working directory.
The filenames are configurable (default `.goosehints` and `AGENTS.md`). `@file`
references expand inline with a visited set, a depth cap of 3, and a 128 KB
per-file cap. Hints reload on every prompt build, not once per session. A
subdirectory tracker watches the `path` and `command` arguments of every tool call;
when a call touches a new directory, its hint files become new prompt extras and
the whole system prompt rebuilds mid-session. All extras pass through a Unicode-tag
sanitizer that strips hidden characters (an anti-injection measure).

## 4. Skills and extension

Five doors add capability without harness changes:

- **Extensions (MCP).** The model itself can install one mid-session; the loop
  then rebuilds tools and the system prompt.
- **Skills.** `SKILL.md` files with frontmatter (the agentskills.io convention)
  under `~/.agents/skills` and `<project>/.agents/skills`; a built-in client
  exposes them, and skills also surface as slash commands.
- **Slash commands.** Built-ins (`/compact`, `/clear`, `/skills`, ...) merge with
  recipes and skills; name precedence is builtin, then recipe, then skill.
- **Recipes.** YAML with instructions, prompt, extensions, typed parameters, a
  response JSON schema, sub-recipes, and retry rules (shell success checks,
  maximum retries). A recipe with a response schema registers a synthetic
  `final_output` tool, and the model must call it to end the run.
- **Hooks.** Eleven events (PreToolUse, PostToolUse, Stop, SessionStart, ...).
  A blocking hook returns Allow or Deny with a reason; a PreToolUse deny becomes
  a tool error marked as a policy denial; a Stop deny forces the loop to
  continue, capped.

## 5. LLM interface

Providers implement one streaming trait that yields message/usage pairs. The
default HTTP timeout is 600 s. Before each call the loop projects agent-visible
messages, repairs the conversation, and merges consecutive same-role messages.

Correction from the verification pass: goose does have a generic transport-retry
layer. A blanket `ProviderRetry` implementation wraps the streaming HTTP request of
most providers with 3 retries and exponential backoff from 1 s, plus rate-limit
delay parsing. The retry sits between the loop and HTTP, per request — the correct
place for a ttx retry as well.

Context management: a pre-turn check compares session token totals (or a tokenizer
estimate) against `context_limit × 0.8`. Compaction asks the same model for a
summary, marks old messages agent-invisible, and appends the summary plus a fixed
continuation text. A context-length error mid-loop triggers one recovery
compaction; a second failure aborts with a user message. A background pass replaces
old tool request/response pairs with summaries past a size-derived cutoff.

Small-model support is the "toolshim": it strips the tools from the request,
injects JSON tool instructions into the system prompt, accumulates the full
response, and sends the text to a second interpreter model to extract tool calls.
A name resolver strips `functions.` prefixes and normalizes sloppy names, and an
argument coercer converts string arguments to schema types. Inference:
grammar-constrained sampling in llama-server replaces the toolshim's second model
at zero cost; the small repairs (name normalization, argument coercion) are the
part worth study — though silent coercion interacts badly with a confirmation
digest that binds the exact argument vector (see the index).

## 6. Tool calls

Tools are MCP tools with JSON schemas, namespaced `extension__tool`, normalized and
sorted by name. An unparseable tool call is stored in history as a placeholder
valid call named `unparseable_tool_call`, and the parse error rides on the paired
tool response, so the model can correct its arguments and every provider formatter
sees a well-formed pair.

An inspection pipeline runs before execution: a permission inspector splits
requests into approved, needs-approval, and denied using persisted per-tool levels;
a security inspector can attach a prompt-injection warning; a repetition inspector
denies an identical consecutive call (same name and arguments) past a cap. The
approval flow yields an action-required message and blocks on a confirmation
channel. A decline injects a fixed text ("DO NOT attempt to call this tool
again...") as the tool result. The default mode is Auto (auto-approve) — a
permissive default ttx must not copy.

All approved calls start at once and their result streams merge; results attach to
per-request response messages as they land. Result truncation: any text block over
200,000 characters spills to a temp file, and a pointer message tells the model to
search the file.

## 7. Observability and state

Tracing uses the OpenTelemetry GenAI semantic conventions: an `invoke_agent` span
per reply with session, model, and provider fields, and a `chat` span per provider
call recording `gen_ai.usage.input_tokens`, output tokens, and cache tokens.
Message content is recorded only behind an explicit opt-in. The stream wrapper
measures time-to-first-token and elapsed time per call.

All state lives in one SQLite database (WAL mode): sessions, messages (content
JSON, metadata JSON, token counts), and a usage ledger. The pivotal mechanism is
per-message visibility metadata: `user_visible` and `agent_visible` booleans. The
UI renders the user projection; the provider request uses the agent projection.
Compaction never deletes: it sets `agent_visible = false` on old messages and
appends an agent-only summary. History stays complete for the human while the
model context shrinks. Mid-turn user input goes into a steer queue and drains at
the next loop top. There is no signed or append-only audit log.

## 8. Errors and limits

Budgets and guards: `max_turns` 1,000 per reply; a `<turn-budget>N/M used</turn-budget>`
tag injected once half the budget is spent (state machine); an empty provider
response is never persisted and retries at most 3 times, then a fixed message ends
the turn; the repetition inspector caps identical consecutive calls; compaction
recovery caps at 2 per failure; Stop-hook denials cap.

The error taxonomy maps provider error types to distinct loop behavior:
context-length-exceeded compacts and continues; rate-limit carries a parsed retry
delay with sanity guards; credits-exhausted stops with a message; a refusal is
terminal and skips all retry paths ("resending this conversation is likely to be
refused again"); a network error asks the user to resend. Malformed tool calls do
not consume a retry budget; only `max_turns` bounds the error feedback loop.

Cancellation: a cancellation token is checked at the loop top, inside stream
consumption, and in the tool-result loop (polled every 100 ms); it also aborts
background summarization.

## 9. Lessons for ttx

1. Adopt the state-machine loop shape: an ordered list of step functions runs over
   the persisted transcript; the first applicable step returns effects; the driver
   applies the effects, persists, and repeats until a step yields to the client.
   Synchronous, no event loop, resumable after a crash.
2. Store visibility flags on transcript records instead of deleting or rewriting
   history: the model sees a projection, and the operator keeps everything. In an
   append-only file this becomes a superseding record, not a mutated row (see the
   index for the reconciliation).
3. Spill oversized tool output to a file and hand the model a pointer message —
   but note the spec obligation: the parent unveil table is a complete
   enumeration, so a spool directory needs a specification change in the same
   commit.
4. Repair malformed tool calls the goose way: keep a placeholder valid call in
   history and put the parse error in the paired tool result. Unlike goose, keep
   the retry bounded by the one-re-prompt budget.
5. Add the two cheap degenerate-output guards: retry an empty model response at
   most N times (goose: 3) and then stop with a fixed message; refuse an identical
   consecutive tool call past a small cap. Both cost a dozen lines of Perl.
6. Copy the prompt-cache discipline: sort the tool list, truncate the timestamp to
   the hour, keep the system prefix byte-stable across turns. llama.cpp prefix
   caching on CPU makes this a direct latency win.
7. Place transport retry between the loop and llama-server, per request, with a
   small bounded backoff — where goose actually has it.
8. Avoid the dynamic capability surface: mid-session extension installs,
   subdirectory hint reloads, per-turn prompt rebuilds, the 1,000-turn budget, and
   the Auto approval default. A 4B model needs a fixed tool table, a stable
   prompt, and the small fixed budgets the ttx spec already mandates.

## Sources

- Clone at `66051ec7d2ea`. Key files: `crates/goose/src/agents/agent.rs`,
  `agents/reply_parts.rs`, `agents/state_machine/{machine,operation}.rs`,
  `agents/state_machine/ops_maxturns.rs`, `agents/prompt_manager.rs`,
  `agents/tool_execution.rs`, `agents/large_response_handler.rs`,
  `agents/extension_manager.rs`, `hints/{load_hints,import_files}.rs`,
  `context_mgmt/mod.rs`, `tool_monitor.rs`, `providers/toolshim.rs`,
  `session/session_manager.rs`, `hooks/mod.rs`,
  `crates/goose-provider-types/src/{goose_mode,retry,base}.rs`,
  `crates/goose-provider-types/src/formats/anthropic.rs`,
  `crates/goose-providers/src/api_client.rs`
- <https://goose-docs.ai/docs/guides/context-engineering/using-goosehints>
- <https://goose-docs.ai/docs/guides/sessions/smart-context-management>
