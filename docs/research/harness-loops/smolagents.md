# smolagents: harness loop design

Date: 2026-08-07. Status: research note.
This note changes no code and no specification.
Part of the [harness loop research](index.md).

| Field | Value |
| --- | --- |
| Repository | <https://github.com/huggingface/smolagents> |
| Inspected ref | `e3a5b8994b30` (main, 2026-07-11, version 1.27.0.dev0) |
| License | Apache-2.0 |
| Language | Python 3 (>= 3.10) |
| Loop size | `src/smolagents/agents.py`: 1,813 lines; `memory.py`: 316 lines |
| Verification | An independent pass checked 12 load-bearing claims against the source. Reliability: high. |

## 1. What it is

smolagents is an agent library from Hugging Face.
The stated goal is simplicity: the agent logic fits in about a thousand lines.
One base class, `MultiStepAgent`, implements a ReAct loop.
Two subclasses give two action formats.
`CodeAgent` makes the model write Python code as its action, executed by a restricted
AST interpreter (1,768 lines) or a remote sandbox.
`ToolCallingAgent` uses native JSON tool calls.
Memory is a plain list of typed step records, replayed into chat messages before each
model call. The library assumes a capable model, resends the full history each step, and
does no context-window management.

## 2. The loop

`run()` stores the task, renders the system prompt into a `SystemPromptStep`, appends a
`TaskStep`, and drains `_run_stream()`. The loop is one statement:
`while not returned_final_answer and self.step_number <= max_steps`, with `max_steps`
defaulting to 20. Each iteration does four things:

1. Check the interrupt switch; raise if set.
2. If a planning interval is set, run a planning step at step 1 and then every N steps —
   one extra LLM call with its own prompt, stored as a `PlanningStep`.
3. Create an `ActionStep` and run the step: rebuild the full message list from memory
   (`write_memory_to_messages()`), call `model.generate()` with stop sequences
   `["Observation:", "Calling tools:"]`, parse the action, execute it, and write the
   observation into the step.
4. Finalize: stamp timing, fire the registered step callbacks, append the step to
   memory. (The callbacks fire before the append — a subtle ordering that callback
   semantics depend on.)

The loop stops in two ways.
Normal stop: the model calls the `final_answer` tool — an explicit terminal tool,
guaranteed present by a `setdefault` on the tool table.
A final answer mixed with other calls is an error.
Optional final-answer checks run before acceptance; a failed check becomes a step error
and the loop continues.
Budget stop: on exhaustion, one extra LLM call summarizes memory into a best-effort
answer, so a run never ends empty.

Nesting: a managed sub-agent is exposed to the model as one more tool.
Its call wraps the task in a template, runs a full nested `run()`, and returns a
templated report string.
Everything is synchronous; the generator form exists only for streaming UIs.

## 3. Instructions

smolagents reads no project instruction files — no `AGENTS.md`, no `CLAUDE.md`. All
instructions come from three YAML prompt templates packaged with the library, rendered
with Jinja2 under `StrictUndefined` (a missing variable fails loudly).
Template variables: the tool dictionary (each tool rendered as a Python function stub),
the managed agents, the import allowlist, the code-block tags, and one
`custom_instructions` string — the only user hook, inserted after a numbered list of
eleven fixed rules. The system prompt re-renders at each run start, so tool changes
appear at run start, not mid-run.

Inference: the fixed, template-driven assembly matches a 4B model well, because the
model always sees the same prompt skeleton.
ttx can keep one fixed prompt file per role and interpolate only tool stubs and operator
instructions.

## 4. Skills and extension

Capability enters only as tools, callbacks, or sub-agents.
There are no skills, no slash commands, no plugins, and no hook scripts.

- **Tools** declare `name`, `description`, `inputs` (a JSON-schema-like dict), and
  `output_type`. The set is fixed at construction.
- **MCP** tools adapt into `Tool` objects before the run starts; the loop itself never
  speaks MCP.
- **Step callbacks** register per-step-class functions that receive the finished step
  and can mutate memory.
  The documented example deletes screenshots from steps older than two steps to save
  tokens — a clean memory-pruning hook that does not touch the loop.
- **Managed agents** add whole agents as tools.

## 5. LLM interface

The base model class defines
`generate(messages, stop_sequences, response_format, tools_to_call_from)`. The
OpenAI-compatible backend works against llama-server.
Input normalization converts internal roles to API roles and merges consecutive
same-role messages.

Retries: 3 attempts with exponential backoff and jitter, but the retry predicate matches
only rate-limit errors by string.
Any other API failure becomes a fatal generation error.

Context-window management does not exist.
The message list is an append-only replay, so the prompt prefix is stable — llama.cpp
KV-cache prefix reuse works naturally.

Two mechanisms matter for a small model:

- **Stop sequences.** Generation stops at `Observation:` and `Calling tools:`, so the
  model cannot fabricate tool results.
  CodeAgent appends the closing code tag to history to train the stop habit.
- **Constrained decoding.** An option sends a strict JSON response format
  `{thought, code}`; `ToolCallingAgent` passes `tool_choice: "required"` by default.
  Both map directly onto llama-server JSON-schema sampling.
  The verification pass noted the two guards are alternatives in the source: with
  structured outputs on, the stop-tag nudge is disabled.

## 6. Tool calls

Two dispatch paths:

- **CodeAgent.** The action is a Python snippet extracted from `<code>` tags (with
  fallbacks), executed by the restricted interpreter: an 11-module import allowlist,
  dunder bans, 10,000,000 operation cap, 30 s thread-based timeout (the worker thread
  cannot be killed), 50,000-character print cap.
  Its own docstring says it “is not a security sandbox”.
- **ToolCallingAgent.** Native tool calls against generated schemas.
  If the API returns no native calls, a fallback extracts a JSON blob from the text
  (first `{` to last `}`). Arguments validate against the schema; a mismatch raises a
  typed error. Multiple calls in one turn run in a thread pool, and results re-order by
  call id when written to memory.

Malformed-call recovery is uniform: the loop catches parsing, tool-call, and execution
errors, stores them in the step’s `error` field, and replays them next turn as a
tool-response message: “Error: ... Now let’s retry: take care not to repeat previous
errors!”. Each retry consumes one normal step from `max_steps`; no separate re-prompt
budget exists. There are no approval or permission gates anywhere in the loop.

A correction from the verification pass: the 20,000-character middle-cut truncation
applies to CodeAgent output and managed-agent reports, but not to ToolCallingAgent
observations, which replay untruncated.
A harness-level uniform cap is a guarantee smolagents does not give on the JSON path.

## 7. Observability and state

The transcript is the memory.
An `ActionStep` records the step number, timing, the exact prompt sent
(`model_input_messages`), the model output, the tool calls, the observations, the error,
the token usage, and the final-answer flag.
One typed step record serves three consumers: the model (via `to_messages`), the human
(via `replay()`), and export (via `dict()`). A monitor callback accumulates token totals
and prints a per-step usage line.

Memory lives only in RAM. There is no session file, no resume-from-disk, no syslog, and
no audit trail; persistence is the caller’s job.
`run(reset=False)` continues a conversation in the same process.
The executor keeps variables between code blocks, and a small state store lets a tool
result (an image) be referenced by key in later tool arguments.

Two verification-pass warnings for a port: `model_input_messages` stores the entire
prompt at every step, so a full-step export grows quadratically with the step count —
log succinct steps plus a hash of the full prompt, not full prompts per step.
And the interrupt check raises before the error handler, so an interrupt aborts the run
with no final summarization and loses the partial step.

## 8. Errors and limits

The error taxonomy makes one sharp distinction: a generation error (harness or API
failure) re-raises and aborts the run; every other agent error (the model misbehaved) is
stored in the step and fed back as an observation, and the loop iterates.
This “fatal versus feed-back” split is the single most portable rule here.

Budgets: `max_steps` 20; the malformed-output retry shares this budget; 30 s per code
execution; 3 API retry attempts (rate-limit only).
Degenerate-output guards do not exist: a prompt rule tells the model not to repeat a
tool call with the same parameters, but nothing enforces it.
A model that repeats the same failing action burns steps until the budget ends.

## 9. Lessons for ttx

1. Adopt memory-as-typed-steps: one array of step records (task, action, observation,
   error, plan), and derive the model message list from it each turn.
   In Perl this is an array of hashes with JSON::PP; one record feeds the prompt, the
   client replay, and the audit log.
2. Adopt error-as-observation with a shared budget: catch parse and tool errors, store
   them in the step, and replay them with a fixed retry preamble.
   Let retries consume the same step budget so recovery can never loop forever.
3. Adopt an explicit terminal tool plus a budget fallback: end the loop only on a
   designated final tool call, and on budget exhaustion make one last summarize call so
   a run always returns something reportable.
   (The terminal-tool convention also composes with a grammar that requires a tool call
   every turn — see the index.)
4. Adopt stop sequences so the model cannot fabricate tool results — but note that under
   grammar-constrained JSON sampling the fabricated-observation failure mode cannot take
   that textual form; the guard applies to a free-text fallback mode only.
5. Avoid the CodeAgent pattern.
   Model-written code as the action needs a large restricted interpreter that is still
   not a sandbox, and it conflicts with the pledge/unveil/doas policy.
   Follow the ToolCallingAgent path and get reliability from grammar-constrained
   decoding.
6. Avoid unbounded context.
   Copy the middle-cut truncation, apply it uniformly (smolagents does not), and add
   old-observation pruning.
7. Add what smolagents lacks: an exact-duplicate-call detector at parse time and
   permission gates inside tool dispatch.
   A small model repeats itself.
8. Use planning steps sparingly or not at all.
   Each plan costs context and one extra model call — expensive at 4B scale and on CPU
   inference.

## Sources

- Clone at `e3a5b8994b30`. Key files: `src/smolagents/agents.py`,
  `src/smolagents/memory.py`, `src/smolagents/models.py`,
  `src/smolagents/monitoring.py`, `src/smolagents/utils.py`,
  `src/smolagents/local_python_executor.py`, `src/smolagents/tools.py`,
  `src/smolagents/prompts/code_agent.yaml`
- <https://huggingface.co/blog/smolagents>
- <https://huggingface.co/docs/smolagents/conceptual_guides/react>
- <https://huggingface.co/docs/smolagents/tutorials/memory>
