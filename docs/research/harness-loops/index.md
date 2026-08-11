# Harness loop designs: research report

Date: 2026-08-07. Status: research report.
**This report changes no code and no specification.** Scope: the agent-loop design of
`ttxd` as `spec/harness.md` defines it — instruction loading, skills, LLM invocation,
tool-call handling, observability, error handling, and state.
The privilege-separation architecture (two programs, three processes, pledge/unveil,
doas wrappers, the confirmation protocol) is fixed by the specification and is not under
review here.

Method: eight open-source harnesses, one research pass per harness against a shallow
clone of the exact cited commit, then one independent adversarial verification pass per
harness against the same source.
Two cross-cutting surveys (instruction conventions, observability) and one completeness
critique complete the set.
The per-harness notes correct refuted and imprecise claims.

## 1. The research set

| Note | Harness | Language | Loop core | One-line design | Verified |
| --- | --- | --- | --- | --- | --- |
| [pi.md](pi.md) | Pi (pi.dev) | TypeScript | 121-line `runLoop()` | Minimal transparent loop; four tools; ~1k-token prompt; append-only JSONL sessions | high |
| [mini-swe-agent.md](mini-swe-agent.md) | mini-SWE-agent + SWE-agent | Python | 190-line agent class | One bash action per turn; linear history equals the prompt; exceptions carry messages | high |
| [openhands.md](openhands.md) | OpenHands 0.62.0 | Python | 1,361-line controller | Everything is an event; one append-only stream feeds history, resume, replay, audit | high |
| [aider.md](aider.md) | Aider | Python | 2,485-line coder | Text edit formats instead of tool calls; reflection loop; git as the safety net | high |
| [goose.md](goose.md) | goose | Rust | state machine, 21 files | MCP-native; re-entrant operation pipeline over persisted state; visibility projections | high |
| [smolagents.md](smolagents.md) | smolagents | Python | 1,813-line agent | Memory as typed steps replayed into messages; explicit terminal tool | high |
| [codex-cli.md](codex-cli.md) | OpenAI Codex CLI | Rust | 2,746-line turn module | Core/UI split over an id-correlated protocol; typed JSONL rollout; escalation protocol | high |
| [opencode.md](opencode.md) | opencode | TypeScript | ~260-line `runLoop` | Client/server; loop re-derives its next action from persisted state each iteration | high |

Cross-cutting notes: [instructions-and-skills.md](instructions-and-skills.md) and
[observability.md](observability.md).

Provenance cautions.
Claude Code appears in the cross-cutting notes through its documentation only; it is not
open source, and those claims are not code-verified.
The OpenHands note describes the deprecated Python 0.62.0 line; main is now a different
codebase. The goose state-machine loop is an in-progress rewrite behind an environment
gate. Date-stamp all three when citing them.

## 2. Vocabulary map

The harnesses share a loop shape under different names.
One mapping onto the spec’s perceive → plan → act → observe loop:

| Spec stage | Common harness vocabulary | Meaning |
| --- | --- | --- |
| perceive | prompt assembly, `write_memory_to_messages`, projection | Build the model input from instructions plus history |
| plan | sampling request, step, model call | One LLM call that returns text and tool calls |
| act | tool execution, dispatch, action | Validate, gate, and execute each call |
| observe | observation, tool result, function call output | Append the result to history |
| one full cycle | turn (Pi, Codex, goose), step (mini, smolagents), iteration | One model call plus its tool executions |
| operator request | task (Codex), run (smolagents), prompt, user message | One operator prompt and all its turns |
| error re-prompt | reflection (aider), requery (SWE-agent), repair (opencode) | The error goes back to the model as input |

## 3. Cross-harness consensus

These mechanisms appear independently in most or all of the set.
They are the strongest evidence this research produces.

1. **Append-only JSONL is the session.** Pi, Codex, Claude Code, and OpenHands derive
   model context, resume, replay, and audit from one append-only record stream.
   The two harnesses that chose mutable SQLite (goose, opencode) still never delete:
   they mark records invisible and derive the model window at read time.
   For ttx: one JSONL transcript per session can serve as the audit log, the resume
   store, and the context source, with `JSON::PP` alone (a candidate spec change; see
   section 7).
2. **Errors return as tool results.** Every harness feeds a malformed or failed call
   back to the model as a normal result with precise text ("Missing required argument
   \"command\""; “unsupported call: NAME”; “The arguments provided to the tool are
   invalid: ...”). None crashes the loop on model misbehavior.
   The differences are only in the budget (see section 5).
3. **Truncation keeps the head and the tail, with an explicit marker.** mini (5,000 +
   marker + 5,000 characters), OpenHands (middle marker), Pi (dual line/byte limits),
   Codex (token budget plus byte cap), opencode (line/byte caps plus spool file).
   The exit status always survives.
4. **The exit test is structural, not trust-based.** The loop ends when the last
   assistant message contains no tool calls (Pi, Codex, goose, opencode), or when an
   explicit terminal tool fires (smolagents `final_answer`, goose recipe `final_output`,
   mini’s magic output line).
   opencode adds the check that no tool part awaits a reply, because providers return
   “stop” alongside tool calls.
   A 4B model needs the structural check even more.
5. **Budgets are checked before each model call.** mini checks step, cost, and time
   budgets at the top of `query()`; OpenHands runs control flags at the top of every
   step; smolagents bounds the loop condition itself.
6. **Tool execution is sequential in effect.** OpenHands queues parsed calls and returns
   one per step. Codex drains parallel futures in call order.
   Pi runs its policy preflight sequentially even in parallel mode.
   mini and smolagents execute in list order.
   Nothing is lost when ttxd executes strictly serially.

## 4. Findings by dimension

### 4.1 Loop shape

The portable shape is: a while-loop over an append-only record list, with the structural
exit test of section 3.4, fixed budgets checked before each model call, and errors fed
back as results. Pi shows the minimal version (121 lines, four stop conditions).
goose’s state machine and opencode’s `runLoop` add the strongest property for ttx:
**re-derive the next action from persisted state at the top of every iteration.** Crash
resume then costs nothing: reload the transcript, re-enter the loop.
mini shows the simplest termination signaling: every event appends a message, and the
loop stops when the last record carries an exit status.

Subagents: the set gives little evidence (Pi omits them; opencode bounds depth at 1;
Codex runs reviews in child sessions).
No finding here supports adding nesting to ttx.

### 4.2 Instructions

All harnesses converge on markdown files at known paths, a small parse, and injection
either into the system prompt (goose, Pi, opencode) or as an early user message (Codex,
Claude Code). Two discovery variants conflict — root-down concatenation with one byte
budget (Codex) versus first-match-wins (opencode, Pi per directory).
For ttx the conflict dissolves by scope: a sysadmin agent has no repository tree to
walk. One global operator instruction file with a fixed small byte budget (2–4 KiB)
suffices, re-read once per operator prompt.
See [instructions-and-skills.md](instructions-and-skills.md).

### 4.3 Skills

The `SKILL.md` convention (frontmatter name and description, body on demand) is
published, cross-harness, and parseable in base Perl.
The load-bearing choice is the trigger.
Model-chosen skills need strong instruction-following; ttx must use deterministic
triggers instead: an operator command or a harness-side keyword match, with the body
injected by the harness.
Hooks across the set (Claude Code, Codex, goose) reduce, for ttx, to policy functions
the parent already owns.

### 4.4 LLM invocation

One blocking request per turn with no streaming is exactly mini’s shape, and it fits the
model process’s one persistent HTTP/1.1 connection (`HTTP::Tiny` serves setup only; the
model process speaks HTTP/1.1 itself after the pledge, per `spec/harness.md`). Transport
retry belongs between the loop and the server, per request, small and bounded (goose: 3
with backoff; Pi app layer: 3; opencode’s uncapped retry is the anti-pattern).
Temperature 0 is the common default for tool-driven turns.
Prompt-cache discipline matters more for ttx than for any surveyed harness, because CPU
prompt reprocessing is the slow axis.
Sort the tool list. Avoid timestamps finer than the hour.
Keep the prompt prefix byte-stable.
Append rather than rewrite (goose, opencode, aider’s fixed chunk order).

Codex is a negative result: it speaks only the OpenAI Responses API now, so its wire
protocol cannot serve llama-server.
ttx keeps the chat-completions shape.

### 4.5 Tool calls

The set splits into native tool calls (Pi, goose, Codex, opencode, smolagents
ToolCallingAgent, mini v2) and text protocols (aider edit blocks, mini v1, OpenHands’
in-context converter for weak models, goose’s toolshim).
The text protocols exist because weak models fail native calling — and every one of them
is a workaround that grammar-constrained sampling at llama-server supersedes.
The corollary from the critique: **do not keep a free-text fallback parser.** A second
parser in the pledged model process is exactly the attack surface the three-process
design minimizes. If the grammar works, the fallback must not exist; if the grammar
fails, that is a defect to fix, not to parse around.

Malformed-call recovery converges on: precise error text, echoed arguments, returned as
a tool result (Pi, OpenHands, opencode’s `invalid` tool).
Pi’s length-stop guard is the one non-obvious rule: when the response hit the output
token limit, execute nothing from it, because salvage-parsed arguments can validate and
still be incomplete.

Approval gates: Codex has the richest model — the tool schema itself carries the
escalation request and a user-facing justification, and a pure function maps policy ×
sandbox state to Skip/NeedsApproval/Forbidden before execution.
This maps one-to-one onto the ttx dry-run and confirmation-digest protocol.

### 4.6 Observability

See [observability.md](observability.md).
The consensus artifact is the typed JSONL rollout with a persistence-policy function
(Codex), per-record usage (all), side-effect-free replay (all), and a raw wire log for
forensics (goose). The OTel `gen_ai.*` vocabulary maps onto syslog key=value pairs
without OTLP.

### 4.7 Errors, limits, and guards

The set’s budgets vary by three orders of magnitude (mini: 0-off defaults with a 3-error
counter; smolagents: 20 steps; goose: 1,000 turns; Pi and Codex: none).
The pattern behind the variance: harnesses with an interactive human afford weak guards;
harnesses meant for unattended runs need hard ones.
The TTX agent runs autonomously between confirmations with a small model, so it sits at
the strict end — the spec’s fixed budgets are correct and stricter than most of the set
by design.

Three guards recur, and the ttx spec omits them today (candidate spec additions, flagged
in section 7). The first is the empty-response retry cap (goose: 3). The second is the
identical-consecutive-call guard (opencode threshold 3; goose repetition inspector;
OpenHands stuck detector).
This guard is absent from mini, smolagents, aider, and Pi, and a small model needs it
most. The third is the length-stop guard (Pi).

The “fatal versus feed-back” split (smolagents) is the cleanest error taxonomy: a
harness or transport failure aborts the step; model misbehavior becomes an observation
and spends budget.

### 4.8 State

The strongest shared idea: the model window is a **projection derived at read time from
an append-only record** (opencode `filterCompacted`, goose visibility flags, OpenHands
condensation events, Codex compacted checkpoints).
History is never rewritten.
For ttx this reconciles compaction with the append-only audit log: compaction appends a
record that names the superseded record ids, and the projection function skips them.
No mutation, no second store.

## 5. Contradictions and resolutions

The verification and critique passes surfaced conflicts inside the takeaway set.
This section resolves each one for the ttx context.
These are research recommendations, not decisions.

1. **Compaction scheme.** Four schemes are recommended across the notes (deterministic
   elision; model-written summary; visibility projection; fixed summary recipe).
   Resolution: the primary mechanism is deterministic elision of old tool outputs — keep
   the last N observations verbatim, replace older ones with a one-line stub (SWE-agent
   `LastNObservations`) — because it is honest about a 4B model’s abilities,
   deterministic, and auditable.
   A model-written summary (the aider/Codex/opencode recipe) is the secondary mechanism,
   for whole-session overflow only, recorded as an explicit transcript record.
   Both express as superseding records over the append-only log (section 4.8).
2. **Prefix stability versus rewriting.** The prompt must stay byte-stable and
   append-only *within* an operator prompt, where the tool loop iterates and CPU latency
   compounds. Elision and compaction run *between* operator prompts, at a prompt
   boundary, where one full re-process is acceptable.
   Within-loop elision, if ever needed, uses the polling trick: re-elide only every k
   steps.
3. **Strict rejection versus silent coercion.** Reject.
   Coercion ("5" → 5, sloppy-name normalization) muddies the confirmation digest, which
   binds the exact argument vector.
   The grammar constraint prevents type errors at sample time, so coercion also loses
   its purpose. A failed validation spends the one re-prompt with precise error text.
4. **Instruction discovery.** No directory walk.
   One global operator instruction file, fixed byte budget, first-match semantics
   trivially satisfied (section 4.2).
5. **Prompt rebuild cadence.** Re-read instruction files once per operator prompt; keep
   the assembled prompt byte-stable across the turns of that prompt.
   This satisfies both goose’s cache discipline and the freshness argument.
6. **Response to a detected repetition loop.** One rule: stop the step, report to the
   operator, fail closed.
   No automatic recovery menu (OpenHands CLI) and no silent per-call refusal that lets
   the loop continue (goose).
   The operator decides whether to continue.
7. **Visibility flags versus append-only audit.** Resolved by superseding records
   (section 4.8). Never mutate a written record.
8. **Text-protocol fallback.** Rejected (section 4.5). No second free-text parser in the
   model process.
9. **Bash-tool framing.** Pi, mini, and the ACI advice presume a general shell tool.
   The ttx tool table is a finite list of diagnostics plus gated mutations through fixed
   C wrappers (decision D7). Those takeaways transfer as analogies only — “validate at
   the interface, blocklist interactive commands” becomes “the wrapper validates its one
   argument”; a literal bash tool is excluded.
10. **Spill-to-file truncation.** Adoptable only with a specification change: the parent
    unveil table is normative and complete, and it contains no spool directory today
    (section 7).
11. **Stop sequences.** smolagents’ “Observation:” stop strings guard a free-text mode
    ttx does not have. Under grammar-constrained JSON they are moot.
    Record them only as evidence that a model fabricates tool results when sampling is
    unconstrained.

## 6. Parameter table

The caps quoted in the notes assume 100k-token contexts.
TTX 1 has a 4K–8K context budget on the target (`spec/inference.md`). Derived starting
points, to be validated against the fine-tuned model in evaluation:

| Dimension | Mechanism | Source | Surveyed value | ttx starting point |
| --- | --- | --- | --- | --- |
| System prompt | Fixed template, one line per tool | Pi | ~1,000 tokens | ≤ 700 tokens |
| Operator instruction file | One file, byte budget, truncate | Codex | 32 KiB | 2–4 KiB |
| Skill list entry | name + description in prompt | skills spec | ≤ 1,024 chars | same |
| Tool output cap | head + tail + elision marker + exit status | mini, Pi | 10,000 chars / 2,000 lines–50 KB | ~100 lines / 4 KB |
| Observation elision | keep last N observations verbatim | SWE-agent | N = 5 | N = 3–5 |
| Summary keep-tail | verbatim recent tail beside summary | opencode, aider | 2,000–8,000 tokens | ~1,000 tokens |
| Tool calls per prompt | budget checked before each model call | spec; smolagents 20, goose 1,000 | 20–1,000 | low tens |
| Malformed call | error-as-result, then stop | spec; mini 3, aider 3 | 1–3 | 1 (spec) |
| Empty response | retry then fixed message | goose | 3 | 1–2 (spec addition) |
| Repetition guard | identical consecutive call cap | opencode | 3 (goose: configurable, value not surveyed) | 2–3 (spec addition) |
| Transport retry | bounded backoff between loop and server | goose, Pi | 3 × exponential | 2–3, bounded |
| HTTP timeout | fixed, must exceed worst-case generation | spec | 600 s common | size from measured tokens/s × max output tokens, plus prompt processing |

## 7. Specification obligations

The living-specification rule requires that an adopted mechanism that touches a
normative table changes the specification in the same commit.
This research flags, and does not make, these changes:

1. **Spool directory.** Spill-to-file truncation (goose, opencode) needs a new path in
   the parent’s unveil enumeration and a statement of its mode and owner.
2. **Termination contract under the grammar.** The spec does not yet state when the loop
   ends. The natural contract — the loop ends when the model stops calling tools —
   becomes unreachable under a grammar that forces a tool call every turn.
   The project must design the grammar and the stop condition jointly — for example, a
   terminal `report` tool in the schema (the smolagents `final_answer` pattern), or a
   grammar that permits a no-call reply.
   This is a design decision the spec must record.
3. **Failure-budget table.** The spec fixes one re-prompt for a malformed call.
   It does not yet state budgets for empty responses, length-stop truncation, or
   repetition. One table should define every recovery path so budgets cannot multiply
   (the critique’s strongest process point).
4. **Raw wire log.** The forensic request log (section 4.6) holds everything the model
   saw and needs the audit-confidentiality treatment the spec already defines for the
   audit log.
5. **Per-session transcript.** The spec fixes the audit log as one file,
   `/var/log/ttx/audit.log`, in the parent’s unveil enumeration.
   A JSONL transcript file per session (sections 3.1 and 4.6) replaces or extends that
   layout, so it changes the audit section and the unveil enumeration, and the change
   must state the directory’s mode and owner.

## 8. Gaps: what this research cannot answer

The completeness critique identified questions the surveyed set does not answer.
They are the next research or design tasks.

1. **llama.cpp specifics.** All eight harnesses target frontier cloud APIs.
   None exercises llama-server’s grammar/JSON-schema constraint, `--jinja` tool
   templating, slot reuse, `cache_prompt`, or context-shift behavior.
   The ttx model-process HTTP code cannot be written from this evidence alone; it needs
   a llama-server-specific investigation.
2. **Input-side token budgeting.** Base Perl has no tokenizer.
   The research did not establish how to measure prompt size before sending
   (llama-server’s `/tokenize` endpoint is the obvious candidate) or what llama-server
   does on window overflow — silent context shift would break the
   transcript-equals-context invariant the audit design depends on.
3. **Cancellation.** How the operator aborts a long CPU generation or a hung tool in a
   synchronous, no-event-loop harness: signal routing across the four processes,
   `alarm()` around a blocked read, killing a tool’s process group, and whether an
   in-flight llama-server request can be cancelled.
   The set only documents async machinery ttx avoids.
4. **Harness/fine-tune co-design.** TTX 1 trains with CPT, then SFT (decision D4), and
   the SFT traces teach tool use.
   The system prompt, tool schemas, error templates, and re-prompt wording are
   training-time artifacts that must match the synthetic trace generator.
   All surveyed harnesses treat the model as fixed and external.
   Keeping harness format and training format in lockstep dominates every
   prompt-engineering takeaway here, and no surveyed harness gives evidence on it.
5. **Sampler configuration.** Temperature, top-p, min-p, repeat penalty, and llama.cpp’s
   DRY sampler are the generation-side complement to the loop guards.
   No takeaway covers sampler settings for agentic decoding on a 4B model, where
   degenerate repetition is best prevented before it reaches the harness.
6. **Prompt injection through observations.** A sysadmin agent feeds logs, configs, and
   dmesg — attacker-influenceable text — back into the model context.
   The spec covers sanitization toward the operator display; no surveyed harness fences
   tool output toward the model.
   Open design question.
7. **Operator liveness.** The spec’s frontend relays streamed output, but with one
   blocking request on the model leg (section 4.4) the harness has nothing to relay
   during a long generation.
   Generation runs at or below the bandwidth ceilings of 23.6–31.2 tokens/s on M1/M2
   (`spec/inference.md`; no measured OpenBSD figure exists).
   The observability research covers logs and replay, not progress signaling.
   A coarse per-turn event ("model thinking", “running pfctl”) over the control socket
   is the likely answer; the fixed HTTP timeout must exceed worst-case generation time
   either way.
8. **Audit-file mechanics.** Append atomicity (torn JSONL lines on crash), fsync policy,
   and `newsyslog` rotation interplay with any `prev_sha256` chaining are not covered by
   prior art; no surveyed harness chains its log.

## 9. Absent harnesses

Four open-source designs would add signal that this set lacks; none was researched here.

- **Letta (MemGPT):** the only fundamentally different answer to a small context window
  — an OS-style memory hierarchy where the agent pages data between in-context and
  archival storage.
- **Cline / Roo Code:** a loop built around per-action human approval, a plan/act mode
  split, and checkpoint/rollback — the closest analogue to the ttx confirmation gate as
  the loop’s centerpiece.
- **k8sgpt:** an ops-domain loop where deterministic analyzers perceive and diagnose and
  the model only explains — an inverted perceive/plan split that suits a weak model.
- **Home Assistant Assist:** the largest production deployment of small local models
  (3B–8B via llama.cpp-class runtimes) calling a fixed tool table — direct evidence for
  what a 4B model can reliably do per turn.

## 10. Reading order

For a first pass: this index, then [pi.md](pi.md) (the minimal loop), then
[opencode.md](opencode.md) (the client/server analogue), then
[codex-cli.md](codex-cli.md) (the policy and rollout machinery), then the two
cross-cutting notes.
The remaining notes supply the small-model evidence (aider, mini-SWE-agent, OpenHands,
smolagents) and the state-machine pattern (goose).
