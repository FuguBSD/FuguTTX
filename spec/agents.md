# Autonomous Development

Development agents — Claude agents — plan, develop, and maintain this monorepo.
Humans review outcomes; they do not type the code. This document specifies what
the agents need: the environment, the credentials, the feedback loops, and the
boundaries. In this document, “agent” means a development agent, not the TTX
agent.

<a id="agt-iface"></a>

## The repository is the interface

Each action has a deterministic entry point: a `make` target for each pipeline
stage, OpenTofu for each cloud resource, version-controlled Axolotl YAML for
each training run, and a runbook in `docs/runbooks/` for each operational
sequence. Agents run the same commands as humans. Thus each action is
reproducible and auditable, no matter who did it. If a capability has no target,
add the target. Do not work around it.

<a id="agt-runtime"></a>

## Runtime environment

Agents work on the development host: the Elastic Metal server of the `infra/dev`
stack, with Linux and KVM ([infrastructure](infrastructure.md)). Bare metal
gives hardware virtualization for the OpenBSD guests. Native CPU performance is
a convenience, because a published performance number comes only from the target
hardware ([evaluation](evaluation.md)). The host carries the full toolchain:
git, `make`, uv (Python 3.12), OpenTofu, Perl with `prove`, qemu with KVM,
llama.cpp, and the `scw` CLI. The host must pin an exact qemu version. A
bootable OpenBSD qemu image with snapshot support must be available on the host.
The `infra/image` stack produces that image and stores it in the artifacts
bucket ([infrastructure](infrastructure.md)). The Perl harness and the agentic
evaluation suite operate correctly only on OpenBSD. CI reinstalls the host in
place each month, and the host holds no durable state.

- **AGT-RUNTIME-1.** The host operates each OpenBSD guest with the `fuguvm`
  tool. One `.fuguvmrc` of the repository declares each guest. The tool must run
  as a command, and the repository must not load an `App::FuguVM` module.
  [IAC-DEV](infrastructure.md#iac-dev) states the guest architecture, the
  accelerator, the host ports and the qemu version gate.

Long work — training campaigns, corpus builds, evaluation sweeps — must continue
across sessions, or hand off cleanly between sessions. Commit important state to
the repository, synchronize it to Object Storage, or write it to the runbook. Do
not keep important state only in an agent context.

<a id="agt-cred"></a>

## Credentials

Each credential comes from the environment or a secret store, never from the
repository. Each credential has the minimum scope for its capability:

| Capability                  | Credential                                                                                                           | Scope                                                                                                                                                                                                                                                                    |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Run the agents              | Anthropic API key (`ANTHROPIC_API_KEY`)                                                                              | Project workspace                                                                                                                                                                                                                                                        |
| Infrastructure and training | Scaleway API key of the pipeline IAM application, shared with CI (separate from the operator application of a human) | Apply and destroy `infra/dev`, `infra/train`, and `infra/image`; read and write Object Storage in the project, which holds four buckets; read consumption and billing data, so agents can monitor their own spend. IAM administration and project deletion are excluded. |
| Code review and CI          | GitHub token                                                                                                         | Push branches, open PRs, read checks. Pushes to the default branch are excluded — changes land only through reviewed PRs.                                                                                                                                                |
| Base models and datasets    | Hugging Face token                                                                                                   | Read, for base-model downloads. Write access is withheld until release, which is a human step.                                                                                                                                                                           |
| Release signatures          | signify private key                                                                                                  | **Never available to agents.** A signature is a human act, without exception.                                                                                                                                                                                            |

The operator application applies `infra/persistent`, which declares the IAM
objects. A human holds its key, and a protected manual workflow dispatch is the
only CI route to it ([infrastructure](infrastructure.md)). Thus the pipeline
credential cannot widen its own scope.

IAM cannot grant access to one bucket. A bucket policy is the only per-bucket
control.

<a id="agt-spend"></a>

## Spend controls

Agents and CI can start GPU instances and metal servers, so cost discipline must
not rest on a convention. The controls live in the infrastructure specification
([spend guardrails](infrastructure.md)): the per-Organization quotas, the scoped
IAM policies, the monthly budget, the billing alerts, the pre-apply forecast
check, and the idle watchdog. Only the quotas and the IAM policies block. The
budget and the alerts notify. Two habits therefore remain:

- `make infra-status` at the start and at the end of each work session.
- `make infra-down` before a session ends with no training in flight.

Only a human raises the budget.

<a id="agt-feedback"></a>

## Feedback loops

Autonomous development is only as good as its verification. Each component
defines “done” in a form a machine can check:

- `make check` reproduces the full CI gate locally.
- Evaluation results are machine-readable scorecards, not prose.
- A smoke-train configuration (Qwen3-0.6B, a small corpus slice) validates
  pipeline changes in minutes, without a GPU campaign.
- Harness changes run against disposable OpenBSD qemu snapshots. A destructive
  error costs one snapshot restore.
- **AGT-FEEDBACK-1.** `fuguvm snapshot save` records the clean guest state, and
  `fuguvm snapshot restore` returns to it after each destructive step.
  [REP-RECIPES](repository.md#rep-recipes) states how a target reads the exit
  code of the tool.
- **AGT-FEEDBACK-2.** `fuguvm status` writes each guest fact on standard output,
  so a `make` target and a test can read it.

Some outcomes have no mechanical check: licensing judgments, release quality,
benchmark publication. For those, the runbook says so, and the work goes to a
human.

<a id="agt-docs"></a>

## Documentation

This specification, the runbooks, and the corpus/licensing notes are the source
of truth for the agents. Keep them current as part of each change, not after it.
The root `CLAUDE.md` carries the per-session context: repository conventions,
entry points, and the standing safety rules. The standing rules:

- Do not leave a GPU instance in operation, unattended.
- Do not move eval/RAG-corpus material into a training manifest.
- Do not sign or publish artifacts.

<a id="agt-human"></a>

## Human decision points

Agents plan, implement, train, evaluate, and iterate on their own. Four
decisions stay human:

1. **Merges.** Agents open pull requests. A human reviews and merges. A green
   `make check` is necessary, never sufficient. A human can delegate the
   mechanical merge of one reviewed branch with the `/ship-it` skill. The
   invocation is the approval.
2. **Releases.** Signatures (signify) and publication of weights, datasets, and
   the harness port.
3. **Spend** above the monthly cap. The pipeline stops at the cap. A human
   raises it.
4. **Licensing lanes.** Each change to what enters the training corpus versus
   the eval/RAG corpus.

The symmetry is intentional. FuguTTX ships the TTX agent in the boundaries of
pledge/unveil, doas, and dry-run gates. The development agents that build it
operate with the same philosophy: least privilege by construction, explicit
gates before irreversible actions, and an append-only audit trail (git history,
CI logs, OpenTofu state).
