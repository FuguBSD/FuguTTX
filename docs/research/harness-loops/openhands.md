# OpenHands: harness loop design

Date: 2026-08-07. Status: research note. This note changes no code and no
specification. Part of the [harness loop research](index.md).

| Field | Value |
| --- | --- |
| Repository | <https://github.com/All-Hands-AI/OpenHands> |
| Inspected ref | tag 0.62.0 = `7fbb48c40679` (2025-11-11) |
| License | MIT (the `enterprise/` directory carries a separate license) |
| Language | Python 3 (asyncio and threads; litellm, pydantic, tenacity, Jinja2) |
| Loop size | `openhands/controller/agent_controller.py`: 1,361 lines |
| Verification | An independent pass checked 14 load-bearing claims against the source. Reliability: high. |

Version note: the classic Python harness ends at tag 0.62.0. The 2026 main branch
is a TypeScript control-plane application, and the agent core moved to the separate
OpenHands agent-sdk. This note describes 0.62.0. Do not read it as current main.

## 1. What it is

OpenHands (formerly OpenDevin) is an open platform for software-engineering agents,
by All Hands AI and a large community (design paper: arXiv:2407.16741, ICLR 2025).
The design philosophy is: everything is an event. The agent emits typed `Action`
events. The runtime answers with typed `Observation` events. One append-only
`EventStream` holds all events. The controller, the memory component, the runtime,
and the UI all subscribe to this one stream. History, persistence, resume, replay,
audit, and telemetry are all derivatives of the stream.

## 2. The loop

The core loop is event-driven, not a for-loop. `AgentController` subscribes to the
stream. Each new event flows through `_on_event`: append the event to history, then
`should_step(event)` decides if the agent takes a step. A user message, an
observation, or a condensation event permits a step. A state-change observation
does not. (Precision from the verification pass: a `NullObservation` permits a step
when it answers a recall action; otherwise it does not.)

`_step()` runs one iteration in a fixed order: check that the agent state is
RUNNING; check the `_pending_action` gate (the controller does not step while an
action still waits for its observation); sync the budget flag; run the stuck
detector; run the iteration and budget control flags; then call
`agent.step(state)`, which makes one LLM call. The controller publishes the
returned action to the stream. The runtime executes runnable actions and publishes
an observation with `cause = action.id`. That observation triggers the next step.
The turn structure is therefore: event → step → action → observation → step. The
pending-action gate makes the loop strictly synchronous per action.

The loop stops on an explicit finish action (FINISHED), a reject action (REJECTED),
user stop (STOPPED), control-flag limits or exceptions (ERROR), or a stuck verdict.
The headless driver only polls the agent state each second until a terminal state.

Nesting: a delegate action builds a child controller on the same stream, with
`start_id` set past the latest event, and with shared iteration flag, budget flag,
and metrics. Parent and child histories stay separate by slicing one stream, not by
separate files.

The verification pass confirmed that event handling is effectively synchronous
despite the pub/sub machinery (`run_until_complete` per event). For one synchronous
session the whole controller reduces to: append event, decide step, call model,
validate, gate, execute, append observation.

## 3. Instructions

The system prompt is a Jinja2 template per agent. The controller emits the rendered
system prompt as a `SystemMessageAction` event at startup. The system prompt is
therefore part of the persisted event stream, and a resumed session reuses the
recorded one.

Project instructions do not enter the system prompt. They enter as events. On the
first user message the controller emits a recall action. The `Memory` component
answers with a `RecallObservation` that contains repository info, runtime info, the
date, secret descriptions, and the content of all repo microagents. Repo
microagents include `.openhands/microagents/repo.md` and mapped third-party files:
`AGENTS.md`, `agent.md`, `.cursorrules`. On every later user message the controller
emits a knowledge recall, and Memory returns instruction snippets whose trigger
keywords match the message. Files are read once at session setup, not per turn.
`ConversationMemory.process_events` rebuilds the prompt from events each step and
filters duplicate snippets.

Inference: "instructions as replayable events" gives an exact audit of what the
model saw. The cost is staleness when files change mid-session.

## 4. Skills and extension

Four doors add capability.

- **Microagents.** One markdown file with YAML frontmatter (`name`, `triggers`,
  `inputs`, `mcp_tools`). A repo microagent is always injected. A knowledge
  microagent is injected only when a trigger keyword matches the user message,
  with a case-insensitive substring test. The snippet arrives as an observation
  event, not as a system-prompt edit. Current documentation rebrands microagents
  as "skills" with `.agents/skills/` directories and progressive disclosure.
- **Tools.** The agent assembles its tool list from config flags (`enable_cmd`,
  `enable_editor`, `enable_browsing`, ...). Each tool is a static JSON-schema
  definition in its own file. New capability is a new tool file plus a flag; the
  loop code does not change.
- **MCP.** A first-class action type; microagent frontmatter can declare stdio
  MCP servers.
- **Delegation.** Agents register in a class registry, and a delegate action swaps
  in a different agent class for a subtask.

The classic harness has no hook system and no slash commands.

## 5. LLM interface

All calls go through one `LLM` class that wraps `litellm.completion`. The agent
path is synchronous and non-streaming. Defaults: temperature 0.0; retries 5 with
exponential wait 8–64 s. On an empty-response error the retry hook raises the
temperature to 1.0 for the next attempt, to break deterministic empty outputs.

Context management has two layers:

1. **Per-event truncation.** `max_message_chars` (default 30,000) truncates each
   observation in the middle and inserts the marker
   `[... Observation truncated due to length ...]`, so the head and the tail
   (command echo, exit status) survive.
2. **Condensation.** An LLM-summarizing condenser (class defaults: `max_size` 100
   events, `keep_first` 1) emits a `CondensationAction` event that lists the
   forgotten event ids and holds a model-written summary. History files are never
   rewritten; the prompt view is recomputed from events. The verification pass
   noted that the effective default condenser depends on the entry path, and that
   the condenser runs inside `agent.step` on every step, so condensation is
   itself a step that produces an event. The invariant holds: every prompt is a
   pure function of the events.

On a context-window error the controller string-matches the provider message (a
marked FIXME hack) and emits a condensation request.

Small-model support: when a model lacks native tool calling, a 976-line converter
rewrites tools into an in-context prompt with `<function=name><parameter=...>`
syntax, sets the stop word `</function`, and parses the text back into tool-call
form. Inference: this confirms that a small model needs either a grammar or a fixed
textual calling convention with stop words. The ttx llama-server grammar constraint
is the stronger version of the same idea.

## 6. Tool calls

Tool definitions are static OpenAI JSON-schema dicts, one file per tool. Parsing
and validation happen in `response_to_actions`: a JSON parse failure, a missing
required argument, or a bad value raises a validation error with exact text, for
example: `Missing required argument "command" in tool call`. An unknown tool name
raises its own error. The controller catches these and posts an `ErrorObservation`
with the exact error text into the stream; the observation returns to the model on
the next step. No dedicated counter bounds the re-prompt count; only the iteration
limit and the stuck detector bound it.

One LLM response can contain several tool calls. All parse into a list, and the
agent queues them and returns one per step, so execution stays serial. Each action
carries tool-call metadata; the observation copies it, so prompts rebuild valid
call/result pairs.

Approval gate: in confirmation mode, runnable actions pass a security analyzer.
With no analyzer configured, risk defaults to UNKNOWN and confirmation is required
— a fail-safe default. In CLI mode every runnable action requires confirmation
regardless of risk. The action state becomes AWAITING_CONFIRMATION, and the loop
halts until the user confirms or rejects.

## 7. Observability and state

The event stream is the audit trail. `EventStream.add_event` serializes every event
to JSON and writes one file per event id, plus 25-event cache pages for fast reads.
The serialized form has fixed top keys: `id`, `timestamp`, `source`
(user/agent/environment), `cause`, the action or observation name, the arguments or
content, tool-call metadata, and LLM metrics. `EventStream.add_event` masks known
secret values with `<secret_hidden>` before it writes. An event over 1 MB logs a
warning.

Token accounting: a metrics object records per-call cost, latency, and token usage
with accumulated totals, and a trimmed copy attaches to every action event, so cost
is visible in the transcript itself. Optional full LLM I/O logging writes one JSON
file per call. Every controller log line carries the session id and a message-type
tag (STEP, ACTION, OBSERVATION, METRICS).

State has two layers. The authoritative layer is the event store. A convenience
`State` object (agent state, control flags, ids, metrics) pickles to base64 on
every state change — but it excludes history, and restore always rebuilds history
by replaying the event stream and pairing actions with observations through
tool-call metadata. A `ReplayManager` replays a recorded action list instead of
calling the LLM, which turns any saved trajectory into a deterministic test.

## 8. Errors and limits

Budgets are explicit objects that run at the top of every step: an iteration flag
(default `max_iterations` 500) and a cost budget flag. A raised flag drives the
agent to ERROR. Interactive resume extends the allotment; headless mode never
extends.

The `StuckDetector` (481 lines) checks five scenarios over recent filtered history:
four identical action-observation pairs; three identical actions with error
observations (with exact-line SyntaxError matching); repeated agent messages with
no observation between them (monologue); an a-b-a-b alternation over the last six
steps; and ten condensation events in a row (context-window thrash). Equality
ignores process ids. Headless mode turns a stuck verdict into an error; the CLI
offers recovery options (truncate history to before the loop, restart from the last
user message, or exit).

Cancellation: user stop sets STOPPED, and the controller then synthesizes an
`ErrorObservation` ("Stop button pressed. The action has not been executed.") for
any unanswered tool call, so the persisted history stays consistent and a resumed
prompt stays valid under strict chat templates.

## 9. Lessons for ttx

1. Adopt the event log as the single source of truth. One JSON record per event
   with `id`, `cause`, `source`, and masked secrets; derive history, resume,
   replay, and audit from it. This merges with the audit log ttx must keep anyway.
2. Adopt middle truncation with an explicit marker, so the head (command echo) and
   the tail (exit status) survive. Use a much smaller cap than 30,000 characters
   for a 4B context.
3. Adopt precise, named malformed-call errors ("Missing required argument
   \"command\""). Keep the stricter ttx one-re-prompt budget; make that single
   re-prompt message this specific.
4. Adopt a cheap stuck detector: identical action-observation repeats, an a-b-a-b
   alternation, and repeated no-tool messages are plain string comparisons over
   the last few history entries. A 4B model repeats itself more, not less.
5. Adopt the synthesized terminal observation. On stop or error with an unanswered
   tool call, write an error result that carries the pending call's identity, so
   no tool call in the history lacks a result.
6. Avoid the pub/sub machinery. For one synchronous session the controller reduces
   to a plain loop; the delegate forwarding and step gating exist to serialize
   what ttx already runs serially.
7. Avoid pickled state blobs. Persist nothing that cannot be rebuilt from the
   event log. Opaque blobs defeat audit and break across versions.
8. Consider keyword-triggered instruction snippets. Markdown files with a
   frontmatter trigger list, injected as observations on a substring match, fit
   base Perl and spend 4B-model context only when relevant.

## Sources

- Clone at tag 0.62.0 (`7fbb48c40679`). Key files:
  `openhands/controller/agent_controller.py`, `openhands/controller/stuck.py`,
  `openhands/controller/state/{state,control_flags}.py`,
  `openhands/events/{stream,event_store}.py`,
  `openhands/events/serialization/event.py`,
  `openhands/agenthub/codeact_agent/{codeact_agent,function_calling}.py`,
  `openhands/llm/{llm,retry_mixin,fn_call_converter}.py`,
  `openhands/memory/{memory,conversation_memory}.py`,
  `openhands/memory/condenser/impl/llm_summarizing_condenser.py`,
  `openhands/microagent/microagent.py`, `openhands/core/loop.py`
- <https://docs.openhands.dev/usage/prompting/microagents-overview>
- arXiv:2407.16741 — OpenHands: An Open Platform for AI Software Developers as
  Generalist Agents (ICLR 2025)
