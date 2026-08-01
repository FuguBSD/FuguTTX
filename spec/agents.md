# Autonomous Development

Development agents — Claude agents — plan, develop, and maintain this monorepo. Humans review outcomes; they do not type the code. This document specifies what the agents need: the environment, the credentials, the feedback loops, and the boundaries. In this document, "agent" means a development agent, not the TTX agent.

## The repository is the interface

Each action has a deterministic entry point: a `just` recipe for each pipeline stage, OpenTofu for each cloud resource, version-controlled Axolotl YAML for each training run, and a runbook in `docs/runbooks/` for each operational sequence. Agents run the same commands as humans. Thus each action is reproducible and auditable, no matter who did it. If a capability has no recipe, add the recipe. Do not work around it.

## Runtime environment

Agents need a persistent POSIX development environment with the full toolchain: git, `just`, uv (Python 3.12), OpenTofu, Perl with `prove`, qemu, llama.cpp, and the `scw` CLI. A bootable OpenBSD qemu image with snapshot support must be available. The Perl harness and the agentic evaluation suite operate correctly only on OpenBSD.

Long work — training campaigns, corpus builds, evaluation sweeps — must continue across sessions, or hand off cleanly between sessions. Commit important state to the repository, synchronize it to Object Storage, or write it to the runbook. Do not keep important state only in an agent context.

## Credentials

Each credential comes from the environment or a secret store, never from the repository. Each credential has the minimum scope for its capability:

| Capability | Credential | Scope |
|---|---|---|
| Run the agents | Anthropic API key (`ANTHROPIC_API_KEY`) | Project workspace |
| Infrastructure and training | Scaleway API key, from a dedicated IAM application (separate from a human operator's) | Apply and destroy the `infra/` stacks; read and write the three project buckets; read consumption and billing data, so agents can monitor their own spend. IAM administration is excluded. |
| Code review and CI | GitHub token | Push branches, open PRs, read checks. Pushes to the default branch are excluded — changes land only through reviewed PRs. |
| Base models and datasets | Hugging Face token | Read, for base-model downloads. Write access is withheld until release, which is a human step. |
| Release signatures | signify private key | **Never available to agents.** A signature is a human act, without exception. |

## Spend controls

Agents can start GPU instances, so cost discipline is enforced, not assumed:

- A billing alert and a documented monthly cap on the Scaleway project.
- `just infra-status` at the start and at the end of each work session.
- `just infra-down` before a session ends with no training in flight.
- Spend above the per-campaign budget in the training runbook is possible only with human approval.

## Feedback loops

Autonomous development is only as good as its verification. Each component defines "done" in a form a machine can check:

- `just check` reproduces the full CI gate locally.
- Evaluation results are machine-readable scorecards, not prose.
- A smoke-train configuration (Qwen3-0.6B, a small corpus slice) validates pipeline changes in minutes, without a GPU campaign.
- Harness changes run against disposable OpenBSD qemu snapshots. A destructive error costs one snapshot restore.

Some outcomes have no mechanical check: licensing judgments, release quality, benchmark publication. For those, the runbook says so, and the work goes to a human.

## Documentation

This specification, the runbooks, and the corpus/licensing notes are the source of truth for the agents. Keep them current as part of each change, not after it. The root `CLAUDE.md` carries the per-session context: repository conventions, entry points, and the standing safety rules. The standing rules:

- Do not leave a GPU instance in operation, unattended.
- Do not move eval/RAG-corpus material into a training manifest.
- Do not sign or publish artifacts.

## Human decision points

Agents plan, implement, train, evaluate, and iterate on their own. Four decisions stay human:

1. **Merges.** Agents open pull requests. A human reviews and merges. A green `just check` is necessary, never sufficient.
2. **Releases.** Signatures (signify) and publication of weights, datasets, and the harness port.
3. **Spend** above the documented per-campaign budget.
4. **Licensing lanes.** Each change to what enters the training corpus versus the eval/RAG corpus.

The symmetry is intentional. FuguTTX ships the TTX agent in the boundaries of pledge/unveil, doas, and dry-run gates. The development agents that build it operate with the same philosophy: least privilege by construction, explicit gates before irreversible actions, and an append-only audit trail (git history, CI logs, OpenTofu state).
