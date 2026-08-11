# Instruction loading and skills conventions

Date: 2026-08-07. Status: research note.
This note changes no code and no specification.
Part of the [harness loop research](index.md).

This note surveys the conventions, not one product: how open-source harnesses load
instruction files, and how skills, commands, and hooks add capability.
Sources are the harness clones cited in the sibling notes plus the documentation sites
listed at the end. Claude Code claims come from documentation, not code reading, because
Claude Code is not open source.

## 1. Instruction files: discovery and layering

All surveyed harnesses converge on one pattern: plain markdown files at known paths,
discovered by a directory walk, delivered broad-to-specific.
Two variants of the walk exist, and they conflict; the index resolves the conflict for
ttx.

**Codex CLI** (`codex-rs/core/src/agents_md.rs`): find the project root by markers
(default `.git`), then collect `AGENTS.md` from root down to cwd and concatenate in that
order. Candidate names per directory: `AGENTS.override.md` first, then `AGENTS.md`, then
configured fallbacks.
One total byte budget applies: 32 KiB default; later files truncate when the budget runs
out. A global file loads first.
The assembled text enters the conversation as a **user message** wrapped in markers, not
as system-prompt text.

**Claude Code** (documentation): four layers load in order: managed policy file →
`~/.claude/CLAUDE.md` → `./CLAUDE.md` → `./CLAUDE.local.md`. Ancestor files load in full
at launch; subdirectory files load on demand when Claude reads files there.
Content is delivered as a user message after the system prompt.
An import syntax `@path` nests up to 4 hops.
Guidance: keep each file under 200 lines.
`.claude/rules/*.md` adds path-scoped rules whose `paths:` frontmatter defers loading
until a matching file is read.
After compaction, only the project-root file is re-injected.

**goose** (`hints/load_hints.rs`): reads `.goosehints` and `AGENTS.md` (names
configurable), global plus local files from the git root down to cwd.
`@file` references expand recursively (depth 3, 128 KB per file).
Hints go into the **system prompt**, re-read on every prompt build.
A subdirectory tracker watches `path` and `command` arguments of tool calls and lazily
loads hints from directories the agent touches.

**opencode** (`session/instruction.ts`): global `AGENTS.md` plus `~/.claude/CLAUDE.md`
for compatibility; the project search tries `AGENTS.md`, then `CLAUDE.md`, then
`CONTEXT.md` — the first name that matches wins, explicitly to avoid stacking
duplicates. Config adds globs and URLs (5 s fetch timeout).
Files re-read every iteration.
The read tool lazily attaches directory-local files, once per message.

**Pi** (`resource-loader.ts`): first-name-match per directory across
`AGENTS.override.md`, `AGENTS.md`, `CLAUDE.md`; global directory first, then ancestors
root-first; wrapped in fixed XML tags inside the system prompt; read once at session
start, re-read only on `/reload`.

**Others.** Cursor: `.cursor/rules/*.mdc` with frontmatter (`description`, `globs`,
`alwaysApply`) and four attachment modes; keep rules under 500 lines.
GitHub Copilot: `.github/copilot-instructions.md` (about two pages maximum) plus
`*.instructions.md` with `applyTo` globs, plus nearest-file `AGENTS.md`. Aider:
`CONVENTIONS.md` is a documentation convention only, loaded by the user as a read-only
file. mini-SWE-agent and smolagents read no project files at all; all instructions live
in configuration templates.

## 2. Skills and progressive disclosure

The Agent Skills convention (agentskills.io; anthropics/skills): a skill is a directory
with `SKILL.md` (YAML frontmatter plus a body) and optional `scripts/`, `references/`,
`assets/`. Frontmatter: `name` (required, max 64 characters, lowercase and hyphens, must
match the directory name), `description` (required, max 1,024 characters, states what
and when), optional license, compatibility, and allowed-tools fields.
Three disclosure levels: metadata (~100 tokens, loaded at startup for every skill), body
(under 5,000 tokens recommended, loaded on activation), resources (loaded on demand).
Keep `SKILL.md` under 500 lines.

Adoption is real and cross-harness: Pi validates the same frontmatter constraints and
lists name/description/path in the prompt; opencode scans `.claude/skills/**` and
`.agents/skills/**` and loads bodies through a permission-gated `skill` tool; goose
exposes skills through a built-in client and as slash commands; Codex injects a skill
body only when the user explicitly names the skill; OpenHands rebrands its
keyword-triggered microagents as skills.
Claude Code caps each skill’s listing entry at 1,536 characters, re-attaches invoked
bodies after compaction under a shared budget, and supports `disable-model-invocation`
to make a skill operator-only.

Three trigger models exist: model-chosen (the model reads the catalog and decides —
Claude Code, Pi), keyword/path-triggered by the harness (OpenHands microagents, Cursor
auto-attach rules), and explicit user invocation (Codex mentions, slash commands).
Only the first requires strong instruction-following.

## 3. Slash commands, MCP prompts, hooks

Slash commands are stored prompts: markdown files whose name becomes the command,
expanded into the user turn with `$ARGUMENTS` / `$1..$n` substitution (Claude Code, Pi,
opencode). opencode unifies config templates, MCP prompts (`prompts/list` /
`prompts/get`), and skills into one command table.
Claude Code additionally executes `` !`command` `` lines before the model sees the
content — an execution channel inside an instruction file.

Hooks are the non-LLM enforcement channel.
Claude Code binds shell commands to lifecycle events (PreToolUse, PostToolUse,
UserPromptSubmit, Stop, SessionStart, ...); a hook receives event JSON on stdin; exit
code 2 blocks the action and feeds stderr back as the reason; stdout JSON can inject
context. Codex has eleven hook events with the same shape; goose has eleven with
Allow/Deny returns. Hooks enforce; instruction files only advise.

## 4. What ttx can implement

Inference. Every mechanism above reduces to base-Perl operations: read files at fixed
paths, concatenate with a byte budget, parse `key: value` frontmatter between `---`
lines, substitute `$ARGUMENTS`, and call a policy function at fixed loop points.
None needs an event loop or CPAN.

The hard constraint is the model, not the harness.
Model-chosen skills and agent-requested rules depend on the model reading a catalog and
deciding — weak instruction-following makes that unreliable at 4B scale.
Deterministic triggers (a user command, a harness-side keyword or path match, a hook)
keep the choice out of the model.
The 32 KiB and 200-line budgets of the large harnesses assume 100k-token contexts; ttx
must derive its budget from the 4K–8K context of the inference plan, which points to a
low single-digit KiB cap for standing instructions.

## Takeaways for ttx

1. Adopt one instruction-file name (`AGENTS.md` style).
   Discover it by a walk from a root marker, enforce one total byte budget with
   truncation, and cap far lower than Codex’s 32 KiB — 2–4 KiB — because a 4B model
   cannot honor more standing rules.
2. Re-read the instruction files once per prompt, and place them in the system prompt
   slot of the chat template.
   One file read per prompt needs no cache invalidation logic.
   (The per-turn rebuild versus static-prompt tension is resolved in the index: re-read
   per prompt, keep bytes stable within a prompt’s turns.)
3. Copy the `SKILL.md` convention exactly: frontmatter name matching the directory,
   description under 1,024 characters, body, optional scripts.
   It is a published convention, several harnesses read the same files, and a Perl line
   parser for `---`-delimited `key: value` frontmatter needs no YAML module.
4. Use progressive disclosure with deterministic triggers: load only
   name-and-description lines at startup, and load a body only on an explicit operator
   command or a harness-side keyword match.
   Do not rely on the 4B model to pick skills from a catalog.
   Inject the body from the harness.
5. Implement slash commands as stored prompt files expanded into the user turn with
   argument substitution.
   This is pure string substitution in Perl and gives operators reusable runbooks.
6. Do not adopt dynamic context injection that executes commands from instruction files
   (the `` !`cmd` `` pattern) unless each command passes the same policy, pledge, and
   dry-run gates as a model-initiated tool call.
   An instruction file must not become an unaudited execution channel.
7. Add hooks as the enforcement channel, not more prose: fixed lifecycle points
   (pre-tool, post-tool, session start) where the parent calls a policy function.
   In ttx the “hook” is a Perl function in the parent, not an external command — the
   policy-in-parent architecture already is the hook.
8. Skip lazy subdirectory instruction loading.
   It exists for large monorepos.
   A sysadmin agent that operates on `/etc` and services gains little from
   directory-scoped rules; one flat instruction file plus skills covers the ttx scope.

## Sources

- Codex CLI clone at `0bdce9f424eb`: `codex-rs/core/src/agents_md.rs`,
  `codex-rs/core/src/config/mod.rs`, `codex-rs/core/src/context/user_instructions.rs`
- goose clone at `66051ec7d2ea`: `crates/goose/src/hints/{load_hints,import_files}.rs`,
  `crates/goose/src/agents/prompt_manager.rs`
- opencode clone at `741244b69d5c`: `packages/opencode/src/session/instruction.ts`,
  `packages/opencode/src/{skill/index,tool/skill,command/index}.ts`
- pi-mono clone at `666d8972ff0b`: `packages/coding-agent/src/core/resource-loader.ts`,
  `packages/agent/src/harness/skills.ts`
- anthropics/skills at `b29e7cf65e5c`; <https://agentskills.io/specification>
- <https://agents.md> (agentsmd/agents.md repository)
- <https://code.claude.com/docs/en/memory>, <https://code.claude.com/docs/en/skills>,
  <https://code.claude.com/docs/en/hooks>
- <https://cursor.com/docs/context/rules>
- <https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions>
- <https://aider.chat/docs/usage/conventions.html>
- <https://modelcontextprotocol.io/specification/2025-06-18/server/prompts>
