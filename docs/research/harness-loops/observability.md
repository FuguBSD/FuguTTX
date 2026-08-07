# Observability and session recording

Date: 2026-08-07. Status: research note. This note changes no code and no
specification. Part of the [harness loop research](index.md).

This note surveys practices across harnesses: transcript formats, resume and
replay, token accounting, telemetry conventions, engine-to-client event streams,
and failure forensics. Sources are the harness clones cited in the sibling notes
(Codex CLI at `0bdce9f424eb`, opencode at `741244b69d5c`, goose at `66051ec7d2ea`,
OpenHands agent-sdk at `e8daeed9cb`, pi-mono at `666d8972ff0b`) plus the
documentation listed at the end. Claude Code claims come from documentation and
community format references, not code reading.

## 1. Transcript formats

**Codex CLI.** The rollout crate writes
`~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`. Each line is
`{timestamp, ordinal, type, payload}`. The payload union holds session meta,
response items (the exact model-visible items), compacted records (summary plus
replacement history), per-turn context (model and policy settings), and a subset
of events. A policy module decides durability per event type: token counts and
turn boundaries persist; streaming deltas and approval prompts do not. A
background task appends lines with explicit flush acknowledgments.

**Pi.** One append-only JSONL per session. Line 1 is a header with a format
version. Every later entry has `{type, id, parentId, timestamp}`; the `parentId`
makes the file a tree, and context is the leaf-to-root path. Compaction is itself
a persisted entry with `firstKeptEntryId`. File creation defers until the first
assistant message, so empty sessions leave no file.

**Claude Code** (documentation). Append-only JSONL at
`~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`. Each line carries type,
uuid, parent uuid, session id, timestamp, cwd, git branch, and a message in API
shape; assistant lines embed usage with input, output, and cache token counts.
Resume follows the parent-uuid chain.

**OpenHands agent-sdk.** One immutable JSON file per event
(`events/event-{idx}-{id}.json`) plus a base-state file. Events are frozen typed
models with id, timestamp, source, and parent id. A conversion function rebuilds
the model context from the event list.

**opencode and goose** chose mutable stores. opencode migrated from per-record
JSON files to SQLite tables (session, message, part) with JSON data columns.
goose uses a SQLite database (WAL mode) with sessions, messages (role, content
JSON, tokens), and a usage ledger per LLM call; its old format was JSONL.

## 2. Resume and replay

Codex rebuilds model context from the rollout file; a compacted item with a
replacement history is a complete checkpoint, and the newest one wins. Replay into
the UI marks replayed events so no live side effect fires. Pi walks leaf to root
and honors the newest compaction. OpenHands replays the event files. Replay never
re-executes tools in any harness.

## 3. Token and cost accounting

The common pattern embeds usage in the transcript record and derives totals.
Codex persists a token-count record per turn. Pi stores usage and cost on each
assistant message. goose keeps a per-call usage-ledger row plus session counters.
opencode stores counters and cost as columns on the session row.

## 4. OpenTelemetry GenAI conventions

The semantic conventions define spans (`invoke_agent`, `chat`, `execute_tool`),
attributes (`gen_ai.request.model`, `gen_ai.usage.input_tokens`,
`gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`), and metrics
(`gen_ai.client.token.usage`, `gen_ai.client.operation.duration`). Codex records
`gen_ai.usage.*` on spans. goose records the same and gates message content
behind an explicit capture switch. Claude Code exports metrics
(`claude_code.token.usage`, `claude_code.cost.usage`) and events with content
redacted by default.

Inference: the `gen_ai.*` names map cleanly to syslog `key=value` pairs. The
value for ttx is the shared vocabulary, not the OTLP transport.

## 5. Engine-to-client event streams

Codex uses a submission-queue/event-queue protocol: `Event{id, msg}` with ~90
variants covering turn lifecycle, per-chunk deltas, tool begin/end, approval
requests, token counts, and errors; the id echoes the submission that caused the
event. opencode streams server-sent events (`session.updated`,
`message.part.delta`, `session.error`) — state replication, not a step log.
OpenHands sends the persisted events themselves to clients; transcript and stream
are one type system.

## 6. Failure forensics

goose writes every raw provider request and response to rotated
`logs/llm_request.N.jsonl` files and bundles them into diagnostics reports. Codex
persists the per-turn context (model, effort, sandbox policy), so one can say
which settings produced an action. Pi records model-change entries and exports
sessions to HTML. OpenHands runs a stuck detector over history. Inference: the
harnesses that answer "why did the agent do X" best are the ones that persist the
model-visible input, not only the output.

## 7. Mapping to ttx

Inference. One append-only JSONL per session under `/var/log/ttx` matches the
Codex/Pi/Claude Code pattern and works with a Perl append plus `JSON::PP`. This
layout is a candidate spec change: the spec fixes the audit log as one file,
`/var/log/ttx/audit.log`, in the parent's unveil enumeration, so a per-session
file layout changes the audit section and the unveil table (see the index,
section 7).
Length-prefixed JSON events to the client match the Codex `Event{id, msg}` shape
at a coarser granularity; a synchronous CPU model needs no streaming deltas.
Syslog duplication mirrors the Claude Code split: the transcript holds full
fidelity, and syslog holds a redacted audit summary. No surveyed harness
hash-chains its transcript; a `prev_sha256` field per line would exceed prior art
and costs one `Digest::SHA` call per record.

## Takeaways for ttx

1. One append-only JSONL file per session can serve as the single source for
   model-context rebuild, client replay, and audit. Codex, Pi, and Claude Code
   all prove one file can serve all three consumers. The per-session layout is
   a candidate spec change (see section 7 above and the index).
2. Give every record a fixed envelope: timestamp, monotonic ordinal, type,
   payload. For a synchronous one-session harness, an integer ordinal is simpler
   than Pi's id/parent tree and still supports resume.
3. Add an explicit persistence-policy function (the Codex pattern): persist turn
   boundaries, model-visible items, confirmations, and token counts; send
   transient events (progress, approval prompts) to the client only. This keeps
   `/var/log/ttx` bounded.
4. Embed token usage in each model-response record — llama-server returns usage
   per completion — and persist a per-turn token-count record, so totals derive
   from the transcript with no extra store.
5. Make replay side-effect-free: rebuild context by re-reading records, never
   re-execute tools, and mark replayed events so client code cannot confuse them
   with live ones.
6. Log the exact request body sent to llama-server to a small rotated side file
   (the goose pattern). With a 4B model that emits malformed calls, forensics
   needs the exact prompt bytes, not a paraphrase. Note the audit-confidentiality
   rule in the harness spec: this file holds everything the model saw, so it
   needs the same 0600 protection as the audit log.
7. Reuse the OTel `gen_ai.*` attribute vocabulary as syslog `key=value` pairs
   instead of adopting OTLP. Redact content by default and gate content logging
   behind an explicit switch.
8. Avoid the mutable-database pattern (opencode and goose SQLite): it adds
   dependencies and breaks append-only audit semantics. SHA-256 chaining of
   transcript lines has no precedent in the surveyed harnesses; ttx can add a
   `prev_sha256` field cheaply with `Digest::SHA` — but see the index for the
   open questions on append atomicity and log rotation that chaining depends on.

## Sources

- Codex CLI clone: `codex-rs/rollout/src/{recorder,policy,list}.rs`,
  `codex-rs/protocol/src/protocol.rs`,
  `codex-rs/core/src/session/rollout_reconstruction.rs`,
  `codex-rs/otel/src/events/session_telemetry.rs`
- opencode clone: `packages/opencode/src/storage/storage.ts`,
  `packages/core/src/session/sql.ts`, `packages/schema/src/v1/session.ts`
- goose clone: `crates/goose/src/session/session_manager.rs`,
  `crates/goose/src/providers/utils.rs`, `crates/goose/src/agents/gen_ai_telemetry.rs`
- OpenHands software-agent-sdk at `e8daeed9cb`:
  `openhands/sdk/conversation/{event_store,persistence_const,stuck_detector}.py`,
  `openhands/sdk/event/base.py`
- pi-mono clone: `packages/coding-agent/src/core/session-manager.ts`,
  `packages/ai/src/types.ts`
- <https://code.claude.com/docs/en/monitoring-usage>,
  <https://code.claude.com/docs/en/sessions>
- <https://opentelemetry.io/docs/specs/semconv/gen-ai/> and the 2026 GenAI
  observability blog post
