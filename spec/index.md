# FuguTTX Specification

FuguTTX is a project that makes **TTX 1**. TTX 1 is a small language model, fine-tuned
on OpenBSD knowledge.
It operates locally and offline on OpenBSD machines, on the CPU only.
The model and the harness together make the **TTX agent**: a task agent for OpenBSD
system administration.

The name refers to tetrodotoxin (TTX), the toxin of the fugu pufferfish.
The mascot of OpenBSD is a pufferfish.

The recipe is short:

1. Fine-tune Qwen3-4B (Apache 2.0) with QLoRA: continued pretraining (CPT), then agentic
   supervised fine-tuning (SFT).
2. Train on one Scaleway H100 instance.
   Destroy the instance after each session.
3. Quantize to GGUF Q4_K_M.
4. Serve with the OpenBSD `misc/llama.cpp` port, CPU only, in 16 GB RAM.

A monthly budget governs all cloud spend.
The initial budget is €1,500. A per-Organization quota is the guardrail that blocks.
The budget and its alerts notify only ([infrastructure](infrastructure.md)).

## How to use this specification

This specification is the source for development plans.
Each document specifies one area of work.
When you make a plan:

1. Read the [decisions](decisions.md).
   A plan must not go against a decision.
2. Find the phase in the [roadmap](roadmap.md).
   Each phase lists its scope, its exit criteria, and its documents.
3. Read the listed documents.
   They give the requirements for the plan.

## Conventions

- All documents use ASD-STE100 Simplified Technical English.
- “Must” shows a requirement.
  “Must not” shows a prohibition.
  “Can” shows a capability or an option.
- Prices and model data show the state at the time of publication.
  Confirm them before each campaign.

## Documents

### Product

| Document | Contents |
| --- | --- |
| [Overview](overview.md) | Goals, non-goals, and terminology. |
| [Decisions](decisions.md) | The nine decisions that control all plans. |
| [Variants](variants.md) | User personas and the promotion rule for variants. |

### System components

| Document | Contents |
| --- | --- |
| [Base model](model.md) | Base model selection, escalation rule, and fallbacks. |
| [Harness](harness.md) | The Perl harness on OpenBSD and its safety design. |
| [Inference](inference.md) | Quantization, memory fit, and CPU inference on OpenBSD. |

### Build pipeline

| Document | Contents |
| --- | --- |
| [Corpus](corpus.md) | Data sources, license lanes, and the data pipeline. |
| [Training](training.md) | CPT, SFT, trace generation, and the compute budget. |
| [Evaluation](evaluation.md) | The five evaluation suites and the release gates. |

### Platform and process

| Document | Contents |
| --- | --- |
| [Infrastructure](infrastructure.md) | Scaleway resources as OpenTofu code. |
| [Repository](repository.md) | Monorepo layout, tools, task runner, and CI. |
| [Autonomous development](agents.md) | Development agents, credentials, and human decision points. |

### Governance

| Document | Contents |
| --- | --- |
| [Licensing and release](licensing.md) | Licenses, dataset cards, model cards, and release integrity. |
| [Roadmap](roadmap.md) | The nine phases and their exit criteria. |
| [Risks](risks.md) | Risks and their mitigations. |
