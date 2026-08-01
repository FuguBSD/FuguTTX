# Harness

The harness `ttx` is the Perl program that operates the tool loop of the TTX agent on
OpenBSD. Only the harness executes commands.
The model only proposes.

## Language constraint

The language is Perl 5 from OpenBSD base, and nothing else.
The harness uses only modules from base: `OpenBSD::Pledge(3p)` and `OpenBSD::Unveil(3p)`
for the sandbox, `HTTP::Tiny` for the local llama-server API, and `JSON::PP` for
tool-call parsing.

**Zero CPAN dependencies is a hard constraint.
A CI check enforces it.** The OpenBSD package tools are Perl, written against base
alone. The harness follows the same discipline.
No compilation is necessary.
No port dependency exists, other than llama.cpp.

## Architecture

`llama-server` (from the `misc/llama.cpp` port) serves the TTX model over an
OpenAI-compatible HTTP API on `127.0.0.1`. `ttx` operates a perceive → plan → act →
observe loop against it.
Together they make the TTX agent: the model proposes, the harness decides and executes.

`llama-server` constrains tool calls at sample time with its JSON-schema/grammar
support. Thus model output is parseable by construction.
`JSON::PP` validates it again.
A malformed call gets one re-prompt.
Then the step stops.
The harness runs as the dedicated unprivileged user `_ttx`.

## Tools

Each tool is a function with a JSON schema.

**Read-only tools:**

- Read configuration files under unveiled paths: `/etc/pf.conf`, `/etc/sysctl.conf`,
  `/etc/rc.conf.local`.
- Run diagnostics: `pfctl -s rules|states|info`, `ifconfig`, `netstat`, `sysctl` (read),
  `pkg_info`, `rcctl get|check`, `dmesg`.

**Gated mutations — dry run first, always:**

- Configuration edits: write a candidate file, show the diff, and validate
  (`pfctl -nf pf.conf.candidate`). Install the file only after an explicit confirmation.
- `pkg_add` and `pkg_delete`: run with `-n` first.
  Do the real invocation only after a confirmation.
- `sysctl -w`: record the previous value.
  Apply only after a confirmation.
  Give a rollback option.
- `rcctl enable|start|restart`: apply only after a confirmation.

## Safety design

Safety is first-class, not optional.

- **pledge/unveil.** The harness pledges a minimal promise set, for example
  `stdio rpath wpath cpath inet proc exec`. `inet` is only for the localhost API.
  `proc exec` is only for the doas-gated tools.
  The harness unveils only necessary paths: `/etc` read-only, `/usr/bin/doas`
  execute-only, its audit log write-only.
  A study of these mitigations across 19 OpenBSD releases shows they are practical
  (Ruohonen, Sierszecki & Tiwari, arXiv:2607.03056).

- **doas, narrow scope.** Privileged actions go through `doas` with per-command rules
  for the `_ttx` user.
  Do not run the harness as root.
  Example rules:

  ```
  permit nopass _ttx as root cmd /sbin/pfctl args -nf /etc/pf.conf.candidate
  permit nopass _ttx as root cmd /usr/sbin/pkg_add args -n nginx
  ```

  Rules list exact commands and arguments.
  All other commands fail closed.

- **Dry run by default.** A destructive action occurs only after a successful dry run
  and an explicit user confirmation.
  No flag can turn this off.

- **Audit.** The harness appends each prompt, tool call, executed command, and exit
  status to `/var/log/ttx/audit.log`. The log opens in append-only mode before the
  privilege drop.

## Model fetch

`ttx fetch` downloads GGUF artifacts with base `ftp(1)`, which speaks HTTPS. It
validates the signify signature against the pinned FuguTTX public key before the model
loads. No TLS library dependency enters the harness.

## Package

The harness ships as an OpenBSD port, `sysutils/ttx`. The port skeleton lives in the
repository. The port includes an `rc.d` script that runs `llama-server` with the TTX
model. Weights do not ship in the package.
`ttx fetch` downloads the models separately.
