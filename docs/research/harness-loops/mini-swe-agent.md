# mini-SWE-agent and SWE-agent: harness loop design

Date: 2026-08-07. Status: research note.
This note changes no code and no specification.
Part of the [harness loop research](index.md).

| Field | Value |
| --- | --- |
| Repositories | <https://github.com/SWE-agent/mini-swe-agent>; <https://github.com/SWE-agent/SWE-agent> |
| Inspected refs | mini v2.4.6 (`a83fcae8`); SWE-agent main (`3ea751c0`) |
| License | MIT (both) |
| Language | Python 3 |
| Loop size | mini `agents/default.py`: 190 lines; SWE-agent `agent/agents.py`: 1,294 lines |
| Verification | An independent pass checked 12 load-bearing claims against the source. Reliability: high. |

## 1. What they are

mini-SWE-agent is the minimal coding agent from the Princeton/Stanford SWE-bench team.
The parent, SWE-agent, introduced the agent-computer interface (ACI) idea at NeurIPS
2024 (arXiv:2405.15793). mini inverts the parent’s philosophy.
It gives the model one capability: run a bash command.
Three deliberate choices define it (documented in the README and FAQ):

- No tools other than bash.
- A completely linear history.
  Every step only appends messages, so the trajectory equals the prompt.
- Stateless execution.
  Each action runs in a fresh subprocess with no persistent shell session.

Version 1 parsed one action per turn from a fenced markdown block.
Version 2 made OpenAI-style tool calls the default and keeps the text protocol as a
supported configuration.
The README claims more than 74 percent on SWE-bench Verified.

## 2. The loop

`DefaultAgent.run(task)` resets the message list, renders two Jinja2 templates (a system
template, then an instance template with the task), and enters `while True`. Each
iteration calls `step()`, which is one line: `self.execute_actions(self.query())`.
`query()` checks the step, cost, and wall-time budgets before each model call, then
calls the model and appends the reply.
`execute_actions()` runs each parsed action, renders observation messages, and appends
them. The loop is fully synchronous.
No nesting and no subagents exist.

Flow control uses exceptions that carry messages: `Submitted`, `LimitsExceeded`,
`TimeExceeded`, `UserInterruption`, `FormatError`. `run()` catches them, appends the
carried messages, and saves the trajectory in a `finally` clause on every iteration.
The loop stops when the last message has `role == "exit"`.

Termination is detected in the environment, not in the model layer.
The local environment raises `Submitted` when the first output line equals
`COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` and the return code is 0. The rest of the output
becomes the submission.

Every action runs in a fresh subprocess (`shell=True`, stderr merged into stdout,
process group killed on timeout, default timeout 30 s). The FAQ gives three reasons:
command termination is hard to detect in a live session, a bad command can kill the
session, and interrupts corrupt later output.
The system prompt tells the model that `cd` and environment variables do not persist,
and it teaches the `VAR=x cd /dir && cmd` prefix idiom.

Parent SWE-agent loops `while not step_output.done`. Its `forward_with_handling()` wraps
each step in a requery loop for recoverable errors.
The requery attempts enter the trajectory but not the history — the model context stays
clean while the audit record stays complete.

The verification pass added two loop facts.
First, `handle_uncaught_exception` appends an exit message with the exception class and
full traceback, then re-raises, so the trajectory records the crash before the process
dies. Second, in mini’s batch execution a mid-batch exception discards the outputs of
earlier actions in the same turn; the interactive subclass was rewritten with
`try/finally` to preserve partial outputs.
A port must use the `try/finally` form.

## 3. Instructions

Neither harness reads `AGENTS.md`, `CLAUDE.md`, or any project instruction file.
All instructions live in YAML configuration files with Jinja2 templates.
`run()` renders the system and instance templates once, at session start, with
`StrictUndefined`, so a missing variable fails loudly.
Template variables merge from the config dump, environment and platform facts, live
counters, and per-run extras such as the task.

SWE-agent adds per-step templates: `next_step_template` wraps each observation, and a
fixed sentence covers empty output ("Your command ran successfully and did not produce
any output."). A `state_command` executes after each action and reports facts such as
the open file and the working directory into the next template.
The harness re-asserts environment facts instead of trusting the model’s memory.

Inference: one upfront render of one system prompt and one task prompt fits a 4B model
and Perl. Per-step re-assertion of small facts (host, working directory, dry-run state)
costs little and prevents drift.

## 4. Skills and extension

mini has no plugin system, no MCP, no hooks, and no skills.
Extension is subclassing plus configuration.
The interactive subclass (209 lines) adds a confirmation gate, three modes (`human`,
`confirm`, `yolo`), an action whitelist of regexes, and five hard-coded slash commands.
A rejected action becomes a user message that carries the reject reason, so the model
sees why.

SWE-agent has a real extension mechanism: tool bundles.
A bundle is a directory with a `config.yaml` that describes each command (signature,
docstring, typed arguments) and a `bin/` directory of plain executables.
The harness generates the model-facing tool documentation from the metadata.
This is the portable idea: the ttx fixed-function wrappers are exactly bundle `bin/`
programs. A small static metadata table per wrapper can generate the tool section of the
system prompt, so the harness and the prompt cannot drift.

## 5. LLM interface

mini calls models through litellm’s OpenAI-compatible chat-completions API. The default
sends exactly one tool schema: a function named `bash` with one required string
parameter `command`. The text-based variant sends no tools and parses the reply text.
Neither agent streams.
Requests are synchronous and blocking.

Retries: tenacity wraps queries, up to 10 attempts with exponential 4–60 s waits.
Auth errors, not-found, unsupported parameters, permission errors, and context-window
overflow never retry.

Context-window management in mini: none.
History grows without bound, and overflow aborts the run.
SWE-agent manages context in history processors, not in the model layer.
`LastNObservations` keeps the last N observations verbatim (N=5 in the paper) and
replaces older ones with “Old environment output: (n lines omitted)”. The docstring
warns that this breaks prompt-cache prefixes and offers a `polling` parameter that
re-elides only every k steps to keep prefixes stable.
SWE-agent also holds hard token guards (`max_input_tokens`, `max_output_tokens`) and
defaults temperature to 0.0.

## 6. Tool calls

Two protocols exist, and the contrast matters for a small model.

- **Text protocol.** The model must emit exactly one fenced block tagged
  `mswea_bash_command`. The parser applies one regex; any count other than one raises
  `FormatError`. The error template receives `finish_reason`, so a `max_tokens`
  truncation gets “respond more concisely” instead of a format lecture.
  The distinctive fence tag prevents collisions with ordinary code blocks.
- **Tool-call protocol.** Zero calls, an unknown tool name, or a JSON argument error
  raises `FormatError`. Multiple calls in one reply execute sequentially, in order.
  The text protocol requires exactly one action per reply; the tool-call protocol
  accepts several.

Parsed actions travel to the loop inside the message record, so the agent class is
protocol-agnostic: text versus tool-call is a model-class swap, and the loop code does
not change. This is a clean seam for a Perl port.

Observation truncation: output over 10,000 characters becomes a 5,000-character head, an
`<elided_chars>N</elided_chars>` marker, and a 5,000-character tail, plus remediation
advice (use head/tail/sed/grep, or redirect to a file).
The return code renders explicitly as `<returncode>N</returncode>`.

SWE-agent prevents trouble at the interface (the ACI lessons): it blocklists interactive
commands (`vim`, `less`, standalone `python`, `su`), validates syntax with `bash -n`
before execution and requeries with the output on failure, caps search output at the
tool (`search_dir` refuses more than 100 matched files), and shows files through
100-line windows. Each check that fires returns a template that tells the model what to
do instead.

## 7. Observability and state

mini saves the full trajectory to a JSON file after every step, inside the `finally`
clause, so a crash still leaves a complete record.
The file holds an `info` block (cost, API call count, config dumps, exit status,
submission) and the complete message list.
Because history is linear, the saved messages are the exact prompt the model saw.
There is no separate transcript.
Assistant and observation messages carry an `extra` dict: timestamps, the raw
untruncated command output, the return code, the per-call cost, and the full API
response dump. The code marks “persist the raw response even when parsing fails” as a
contract. mini has no resume path; the inspector TUI only browses trajectory files.

SWE-agent separates history from trajectory.
Each trajectory step stores the action, observation, thought, execution time, state, and
`query` — a deep copy of the entire message list sent to the model at that step.
Every model call is exactly reproducible even though history processors mutate the
prompt between steps.
Saved trajectories replay through a `ReplayModel` and convert to few-shot
demonstrations. Neither project integrates syslog or any audit daemon.

## 8. Errors and limits

mini defaults: `step_limit` 0 (off), `cost_limit` $3.00, `wall_time_limit_seconds` 0
(off), `max_consecutive_format_errors` 3. Budgets are checked before each model call, so
a run can overshoot the cost limit by exactly one call.
The format-error counter resets on any clean step.
Three consecutive failures exit with status `RepeatedFormatError`. The cost of a failed
parse is still billed.
A command timeout kills the POSIX process group with SIGKILL and returns the partial
output to the model with return code -1. Ctrl-C in the interactive agent becomes a user
message, not a crash.

SWE-agent adds: `max_requeries` 3 shared across format errors, blocked actions, and
syntax errors; a total execution timeout of 1,800 s; a cap of 3 consecutive command
timeouts; and per-instance cost and call limits.
Its distinctive move is graceful degradation: almost every terminal error routes through
an auto-submission path that extracts a `git diff` even when the runtime has died.
A crashed run still yields a typed exit status and a candidate patch.

Neither project detects a repeated identical action or degenerate output beyond the
consecutive-format-error counter.
Inference: a 4B model repeats actions more than the frontier models these harnesses
target, so ttx needs the guard they lack.

## 9. Lessons for ttx

1. Adopt the exit-as-message loop shape.
   Append every event (result, limit hit, error, finish) to one linear message array,
   and stop when the last record carries an exit status.
   This is a while-loop over an array of hashes in Perl, and the transcript equals the
   prompt, so the audit log is the replay format.
2. Copy the typed re-prompt for malformed output.
   Render a fixed error template that restates the exact expected format and branches on
   `finish_reason`, so a truncation gets “be more concise”.
   The ttx budget of one re-prompt is stricter than mini’s three; the branch makes the
   single retry count.
3. Truncate observations head-plus-tail with an explicit elided-count marker and
   remediation advice. Always include the return code as a tagged field.
   Send a fixed sentence for empty output.
4. Use deterministic observation elision (`LastNObservations`) as the primary
   context-management device: keep the last N observations verbatim and replace older
   ones with a one-line stub.
   It is deterministic, needs no second model call, and never touches assistant
   messages. Use the polling variant to keep the prompt prefix stable for llama.cpp
   prefix caching.
5. Keep rejected model output out of the model context but in the audit trail.
   Write the malformed reply to the audit log; send only the short error template to the
   model.
6. Prevent trouble at the interface, not in the parser: validate before execution (the
   ttx wrapper argument checks are this), cap search-style output at the tool, and
   return a template that tells the model what to do instead.
   The ttx tool table is fixed, so the shell-blocklist idea transfers only as an
   analogy.
7. Record the crash before the process dies: an eval or `$SIG{__DIE__}` wrapper that
   appends an exit record with the error, then re-raises.
8. Add the guard these harnesses lack: hash the last few actions and stop or re-prompt
   on a repeated identical action.

## Sources

- Clones at the cited refs.
  mini key files: `src/minisweagent/agents/{default,interactive}.py`,
  `src/minisweagent/models/litellm_model.py`,
  `src/minisweagent/models/utils/{actions_text,actions_toolcall,retry}.py`,
  `src/minisweagent/environments/local.py`, `src/minisweagent/exceptions.py`,
  `src/minisweagent/config/{mini,mini_textbased}.yaml`. SWE-agent key files:
  `sweagent/agent/agents.py`, `sweagent/agent/models.py`,
  `sweagent/agent/history_processors.py`, `sweagent/tools/tools.py`,
  `config/default.yaml`, `tools/search/bin/search_dir`.
- <https://mini-swe-agent.com/latest/advanced/control_flow/> and
  <https://mini-swe-agent.com/latest/faq/>
- <https://swe-agent.com/0.7/background/aci/>
- arXiv:2405.15793 — SWE-agent: Agent-Computer Interfaces Enable Automated Software
  Engineering (NeurIPS 2024)
