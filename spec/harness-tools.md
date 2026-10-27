# Harness tools

This document is a part of the [harness](harness.md) specification.

## Tools

Each tool is a function with a JSON schema.

<a id="hrn-tool-ro"></a>**Read-only tools:**

- **HRN-TOOL-RO-1** — Read configuration files under unveiled paths:
  `/etc/pf.conf`, `/etc/sysctl.conf`, `/etc/rc.conf.local`.
- **HRN-TOOL-RO-2** — Run diagnostics: `pfctl -s rules|states|info`, `ifconfig`,
  `netstat`, `sysctl` (read), `pkg_info`, `rcctl get|check`, `dmesg`.
- **HRN-TOOL-RO-3** — Render one man page, by section and name: `man -T ascii`.
  The arguments validate against a strict name pattern. The retrieval rows of
  the [baseline grid](evaluation.md#baselines-and-ablations) use this tool.
- **HRN-TOOL-RO-4** — The parent runs most read-only tools directly as `_ttx`,
  with no doas. `pfctl` is the exception. `pfctl -s` reads `/dev/pf`, which is
  mode 0600 and owner root. The `pfctl -s rules|states|info` reads therefore get
  exact-argument doas rules. The argument set is finite, so an exact rule is
  safe here. This rule depends on the system users
  ([HRN-ARCH](harness.md#hrn-arch)).

The parent runs each tool with `Fugu::Process`. The module never runs a shell:
the command is a list, so no argument can become a shell operator. The list form
of [HRN-PERL](harness.md#hrn-perl) therefore holds for each tool. `run` gives
the captured output, the exit code and the timeout of the call. `exit_code`
decodes the raw wait status.

<a id="hrn-tool-gate"></a>**Gated mutations — dry run first, always:**

- **HRN-TOOL-GATE-1** — Configuration edits: write a candidate file, show the
  diff, and validate (`pfctl -nf pf.conf.candidate`). Install the file only
  after an explicit confirmation.
- **HRN-TOOL-GATE-2** — `pkg_add` and `pkg_delete`: run with `-n` first. Do the
  real invocation only after a confirmation.
- **HRN-TOOL-GATE-3** — `sysctl -w`: record the previous value. Apply only after
  a confirmation. Give a rollback option.
- **HRN-TOOL-GATE-4** — `rcctl enable|start|restart`: apply only after a
  confirmation.
- **HRN-TOOL-GATE-5** — Each gated mutation records its rollback path before it
  applies: the previous file content, the previous sysctl value, or the previous
  service state. The rollback record enters the session transcript. This rule
  depends on the session transcript
  ([HRN-TRANSCRIPT](harness-loop.md#hrn-transcript)).

The parent runs each dry run and each real call with `Fugu::Process`
([HRN-TOOL-RO](#hrn-tool-ro)).

<a id="hrn-pf-commit"></a>**The pf commit-confirm rule.** A bad ruleset can cut
the connection that carries the confirmation, and `pfctl` has no built-in
revert. A confirmed mistake is not an attack, so no gate stops it. A `pf.conf`
install is therefore a two-step commit:

1. Before the install, the parent copies the live `/etc/pf.conf` into the
   candidate directory.
2. After the confirmation, the parent installs the candidate and loads it
   through the `pf-load` wrapper.
3. A revert timer starts. The default window is 120 seconds.
4. The operator confirms connectivity through the client, inside the window.
5. Without the second confirmation, the parent restores the saved file, and it
   loads the file through the same wrapper. A lockout therefore heals itself.
6. A session disconnect before the second confirmation triggers the same revert.

The revert is the one mutation that runs without a fresh confirmation. It only
restores the ruleset that was live before the install.

<a id="hrn-tool-report"></a>**The terminal tool:**

- `report` ends the step, and it carries the answer of the model to the
  operator. It executes no command. It is always in the tool table, because the
  grammar forces a tool call on each turn (see
  [the agent loop](harness-loop.md#the-agent-loop)).

<a id="hrn-tool-table"></a>Each tool has one row in a static metadata table. The
table generates both the tool line of the system prompt and the JSON schema. So
the prompt and the policy cannot drift.

<a id="hrn-calls"></a>

## Tool-call handling

The grammar constrains model output at sample time. Validation still runs in
full, because a lying `llama-server` can bypass the grammar (see
[safety design](harness-safety.md#safety-design)).

- **Strict rejection.** The harness must not coerce argument types, and it must
  not normalize tool names. A coerced argument muddies the confirmation digest,
  which binds the exact argument vector. The grammar prevents type errors at
  sample time, so coercion also has no purpose.
- **Precise error results.** A failed validation returns a tool result that
  names each bad field and echoes the received arguments. An unknown tool name
  returns the fixed result `unknown tool: <name>`. Empty tool output returns a
  fixed sentence plus the exit status.
- **The length-stop guard.** When a response reports that the output hit the
  token limit, the parent executes nothing from that response. A truncated call
  can validate and still be incomplete. The re-prompt states that the call can
  be truncated, and it spends the malformed-call budget. The internal record
  therefore carries the finish reason and the usage counts of each response.
- **No fallback parser.** The model process parses tool calls with `JSON::PP`
  alone. A free-text fallback parser must not exist. If the grammar fails, that
  is a defect to fix, not to parse around.

<a id="hrn-trunc"></a>

## Tool output truncation

Two limits cap each tool output toward the model: 100 lines and 4,096 bytes,
whichever comes first. Truncation keeps the head and the tail, and it inserts an
explicit marker with the count of elided lines and bytes. The exit status always
survives. The session transcript keeps the full output
([HRN-TRANSCRIPT](harness-loop.md#hrn-transcript)).
