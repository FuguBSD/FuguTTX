# Aider: harness loop design

Date: 2026-08-07. Status: research note. This note changes no code and no
specification. Part of the [harness loop research](index.md).

| Field         | Value                                                                                                                                          |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Repository    | <https://github.com/Aider-AI/aider>                                                                                                            |
| Inspected ref | `5dc9490bb35f` (main, version 0.86.3.dev, 2026-05-22)                                                                                          |
| License       | Apache-2.0                                                                                                                                     |
| Language      | Python 3 (litellm, prompt_toolkit, tree-sitter, networkx)                                                                                      |
| Loop size     | `aider/coders/base_coder.py`: 2,485 lines                                                                                                      |
| Verification  | An independent pass checked 12 load-bearing claims against the source. Two were refuted; this note carries the corrections. Reliability: high. |

## 1. What it is

Aider is an open-source pair-programming CLI, started by Paul Gauthier. It is a
chat REPL, not an autonomous agent. The human supplies each task. The model
answers with file edits in a strict textual format. The harness parses the text,
applies it to the git work tree, and commits.

The design philosophy: do not trust native tool calls for edits. Aider defines
“edit formats” (whole, diff/editblock, diff-fenced, udiff, patch) and selects
one per model. Weak models get simpler formats. A benchmark suite scores each
model-format pair. Git is the safety net: automatic commits, a dirty-commit
before each edit, and `/undo`.

## 2. The loop

`Coder.run()` is the outer REPL: `while True: get_input(); run_one()`. It stops
on EOF. A double Ctrl-C inside two seconds exits.

`run_one()` is the per-message loop. `init_before_message()` resets per-message
state (`num_reflections = 0`, lint and test outcomes, pending shell commands)
and records the git HEAD. Then it loops: send the message; if the harness set a
“reflection” (an error text), that text becomes the next message. The loop stops
when no reflection is set or when `num_reflections >= max_reflections`
(hard-coded 3). One user message therefore causes at most four model calls, plus
transport retries.

`send_message()` is one turn. It appends the user message, rebuilds the full
prompt from scratch, pre-checks tokens, calls the model with a retry loop, then
post-processes in a fixed order: detect file mentions (confirm, add files,
reflect so the model retries with the new context); parse and apply edits (a
failure sets the reflection); auto-commit; archive the exchange; lint the edited
files and reflect failures after confirmation; run model-proposed shell commands
after confirmation; run tests and reflect failures after confirmation. A pending
edit reflection short-circuits the lint, shell, and test stages for that turn.

Nesting: architect mode is a two-model chain, not a subagent tree. The architect
coder builds a second coder with the editor model, empties its history, and runs
it synchronously on the architect’s reply text alone. Cost and commit hashes
merge back. On an edit-format switch, the old history is summarized first,
because old-format assistant messages teach the model the wrong format.

The whole loop is synchronous. It maps directly to a Perl 5 harness with no
event loop.

## 3. Instructions

Aider has no `AGENTS.md` or `CLAUDE.md` convention. Project instructions enter
as read-only files: `aider --read CONVENTIONS.md`, `/read-only`, or a `read:`
list in `.aider.conf.yml`. The config file is searched in the working directory,
then the git root, then home.

Prompt assembly is per-call and total. `format_chat_chunks()` rebuilds every
message list from scratch on every send. There is no staleness problem because
file bodies are re-read each turn. A dataclass fixes the chunk order: system,
examples, read-only files, repo map, done history, chat files, current exchange,
reminder.

Three model flags shape delivery for weak models:

- `use_system_prompt = false` sends the system text as a user message paired
  with an assistant “Ok.”.
- `examples_as_sys_msg` folds the few-shot examples into the system message.
- `reminder` selects where the closing reminder goes: a final system message, or
  stuffed into the last user message; it is dropped when the token budget has no
  room.

Read-only files and the repo map each arrive as a user message paired with a
canned assistant acknowledgment ("Ok, I will use these files as references.").
Inference: these pairs train the model in-context to treat the material as
settled fact, and they keep the message list role-alternating for strict chat
templates. Both properties help a 4B model behind llama.cpp templating.

## 4. Skills and extension

Aider has no plugin API, no MCP client, and no hook system. Capability enters by
four routes:

- **Slash commands.** About 45 `cmd_*` methods (`/add`, `/run`, `/test`,
  `/undo`, `/tokens`, ...). `/load` executes a file of commands line by line;
  `/save` writes the commands that rebuild the current file set. This is a
  session-recipe mechanism, not a skill system.
- **Edit formats as classes.** Each format is a coder subclass with a prompts
  object. A new format is one parser class plus one prompts class; the loop does
  not change.
- **Chat modes** (code, ask, architect, context, help) are also coder classes; a
  mode switch carries files, history, and costs into the new coder.
- **External command hooks.** `--lint-cmd` and `--test-cmd` are user-supplied
  commands. The loop runs them after each edit and feeds failures back as
  reflections. This is the only extension point that changes loop behavior, and
  it is data, not code.

Inference: the lint/test hook is the most portable idea. A fixed-purpose harness
needs a small table of post-action verification commands whose output re-enters
the loop as text, not a plugin system.

## 5. LLM interface

All traffic goes through litellm as OpenAI chat completions. Temperature
defaults to 0. The HTTP timeout is 600 s. Streaming is the default. Retry
backoff starts at 0.125 s and doubles; when the delay exceeds 60 s, it stops.
Context-window overflow never retries; it takes a diagnostic path that itemizes
system, history, repo-map, and file tokens and suggests `/drop` or `/clear`.

Context management has three layers:

1. **Pre-flight.** `check_tokens()` counts tokens against the input limit and
   asks the user before an oversized send.
2. **History compaction.** `ChatSummary` triggers when done messages pass a
   budget (between 1,024 and 8,192 tokens, derived from the model’s window). It
   keeps a verbatim tail of about half the budget, cuts the head at an
   assistant-message boundary, summarizes the head with the weak model, and
   recurses at most three times deep.
3. **Output overflow.** On `finish_reason == "length"`, aider re-sends with the
   partial reply as an assistant prefill message and continues, when the model
   supports prefill; otherwise the turn ends with an error note in history.

Prompt caching: up to three Anthropic cache-control breakpoints, plus an
optional thread that pings the provider every ~295 s to keep the cache warm. For
ttx this layer is unnecessary: llama.cpp reuses the KV cache for a stable prompt
prefix automatically, which rewards aider’s fixed chunk order even more.

## 6. Tool calls

Aider does not use native tool calls for edits. The model writes edits as text
in a fixed format, and the harness parses them. This is the central design fact
for small models.

The editblock parser reads `<<<<<<< SEARCH / ======= / >>>>>>> REPLACE` blocks
line by line and resolves the filename against in-chat files. Matching tries an
exact match, then a leading-whitespace-flexible match, then drops a spurious
leading blank line, then handles `...` elision. A fuzzy edit-distance matcher
exists in the source but sits behind an early return — the maintainers disabled
silent fuzzy application.

Application order (corrected by the verification pass): the pipeline is
`get_edits` → dry run → per-path permission gate → apply, but the unit of
atomicity is the individual block, not the reply. The dry run catches malformed
formats and re-maps paths; it does not detect match failures. The real apply
writes each matching block as it iterates, auto-commits the passing blocks, and
only afterward raises an error for the failures. The reflection text says which
blocks were applied and tells the model not to re-send them. Git undo is the
recovery mechanism. A design that requires action-level atomicity — as the ttx
confirmation protocol does: each mutation gates individually behind its own dry
run, digest, and confirmation, and a confirmed action installs whole or not at
all — is stricter than aider. The specification must present this rule as a
deliberate divergence, not as a copy.

The per-path gate is real: creating a new file, or editing a file not in the
chat, needs explicit user confirmation, and dirty files get a pre-commit so
`/undo` stays safe.

Malformed-call recovery: the parser error text becomes the reflection. The
failed-edit report quotes each failed block, shows near-miss lines from the real
file (similarity threshold 0.6), and notes when the REPLACE lines already exist
in the file. The reflection budget (3) covers all causes together: malformed
edits, failed matches, lint failures, test failures, and file-mention retries.

## 7. Observability and state

Aider keeps three plain-text logs plus git:

1. **Chat transcript**: `.aider.chat.history.md`, append-only markdown with role
   prefixes. `--restore-chat-history` parses it back into messages, so the human
   transcript doubles as a lossy resume store.
2. **Input history**: the typed commands; executed shell commands are injected
   as `/run ...` entries.
3. **Raw wire log** (`--llm-history-file`, off by default): the full formatted
   message list before each call and the reply after, with timestamps. This is
   the audit-grade record.

Token and cost accounting reads provider usage fields (with cache tokens) and
prints per-message and cumulative totals, which survive mode switches.

Integrity trail, with a correction from the verification pass: aider hashes
every request and response with SHA-1, but it computes the request hash before
it adds the messages to the request, so the hash covers only the parameters, not
the prompt content. Do not copy it as a confirmation-digest primitive; the ttx
digest must cover the full content, as the spec already requires.

In-memory state splits into the active exchange and the done history. After a
successful edit-and-commit, the exchange moves into history, and aider can
replace it with a two-line stub ("I committed hash x", “Ok.”). History keeps no
full file bodies, because the files chunk re-sends fresh content every turn.
Durable state lives in git. There is no JSON session file, no message ids, and
no exact replay.

## 8. Errors and limits

Budgets are few, small, and hard-coded: 3 reflections per user message, retry
backoff capped at 60 s, one 600 s HTTP timeout, a pre-send token check behind a
confirmation, and a warning at 4+ files or 20k+ tokens of chat files. There is
no repetition detector and no per-session call budget. Inference: the
human-in-the-loop REPL is the real loop guard; aider can afford weak guards only
because a human reads every reply. The harness executes actions autonomously
between confirmations, so it must keep its own fixed budgets.

Cancellation: Ctrl-C during a stream annotates the history — the user message
gets “^C KeyboardInterrupt” and an assistant line “I see that you interrupted my
previous reply.” — so the model does not treat the truncated reply as accepted.

## 9. Lessons for ttx

1. Adopt the reflection pattern with one shared budget. Cap all retry causes
   (malformed call, failed validation, failed verification) with one counter per
   user prompt, and return control to the operator at the cap.
2. Make the reflection message rich, not an error code. Quote the failed
   payload, show near-miss candidates, and say what already succeeded. A 4B
   model needs concrete correction text.
3. Rebuild the whole prompt from an ordered chunk table every turn, and re-read
   live state fresh. A fixed order maximizes llama.cpp prefix-cache reuse with
   no cache API at all.
4. Pair every injected context block with a canned assistant acknowledgment, and
   keep the option to deliver the system text as a user/assistant pair. Weak
   models follow demonstrated dialogue better than system-prompt prose. Bench
   the variants against the one TTX model and hardcode the winner.
5. Reject imperfect payloads; do not fuzzy-match model output into mutations.
   Aider wrote the fuzzy fallback and then disabled it. ttx must spend its one
   re-prompt instead of silently repairing arguments.
6. Note the corrected atomicity fact: aider applies passing blocks and reflects
   the failures, with git as the undo layer. ttx requires action-level atomicity
   through its confirmation digest. Keep that stricter rule; it is a divergence
   from aider, chosen because a sysadmin mutation has no `git undo`.
7. Compact history with the model against a small budget: verbatim tail of about
   half the budget, cut at an assistant boundary, summarize the head. This runs
   inline and synchronously between turns; no thread is needed.
8. Keep the three-log split: human transcript, input history, raw wire log. It
   ports to Perl file appends plus syslog. Hash full content, not parameters.

## Sources

- Shallow clone at `5dc9490bb35f`. Key files: `aider/coders/base_coder.py`,
  `aider/coders/editblock_coder.py`, `aider/coders/architect_coder.py`,
  `aider/coders/chat_chunks.py`, `aider/models.py`, `aider/history.py`,
  `aider/io.py`, `aider/commands.py`, `aider/repomap.py`, `aider/main.py`
- <https://aider.chat/docs/more/edit-formats.html>
- <https://aider.chat/docs/repomap.html>
- <https://aider.chat/docs/usage/conventions.html>
- <https://aider.chat/docs/usage/caching.html>
