# FuguTTX Specification

FuguTTX is a project that makes **TTX 1**. TTX 1 is a small language model, fine-tuned
on OpenBSD knowledge.
It operates locally and offline on OpenBSD machines, on the CPU only.
The model and the harness together make the **TTX agent**: a task agent for OpenBSD
system administration.

The name refers to tetrodotoxin (TTX), the toxin of the fugu pufferfish.
The mascot of OpenBSD is a pufferfish.

The recipe is short:

1. Fine-tune Qwen3-4B (Apache 2.0) with QLoRA: continued pretraining (CPT) on the corpus
   and its synthetic augmentation, then agentic supervised fine-tuning (SFT).
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
4. Cite each requirement by its unit ID, for example `HRN-CONFIRM`. A plan lists the
   units that it implements, the units that it implements in part, and the units that it
   defers. A plan lives in `docs/plans/`. The [implementation register](STATUS.md) lists
   each unit and its state.
5. When your change implements a unit, or a part of a unit, set the state of the unit in
   the [implementation register](STATUS.md) in the same change.

## Conventions

- All documents use ASD-STE100 Simplified Technical English.

- “Must” shows a requirement.
  “Must not” shows a prohibition.
  “Can” shows a capability or an option.

- Prices and model data show the state at the time of publication.
  Confirm them before each campaign.

- A unit ID names one unit of one document, for example `HRN-CONFIRM`. A rule ID names
  one rule inside a unit, for example `HRN-CONFIRM-6`. An HTML anchor with the
  lower-case ID marks each unit in its document.
  A unit extends from its anchor to the next unit anchor or heading, whichever comes
  first. An ID must not change.
  A retired ID must not return to use.
  The document codes are fixed:

| Code | Document | Code | Document |
| --- | --- | --- | --- |
| HRN | [harness.md](harness.md) | INF | [inference.md](inference.md) |
| IAC | [infrastructure.md](infrastructure.md) | MDL | [model.md](model.md) |
| COR | [corpus.md](corpus.md) | VAR | [variants.md](variants.md) |
| TRN | [training.md](training.md) | REP | [repository.md](repository.md) |
| EVL | [evaluation.md](evaluation.md) | AGT | [agents.md](agents.md) |
| LIC | [licensing.md](licensing.md) | RSK | [risks.md](risks.md) |
- The [implementation register](STATUS.md) is the only home of implementation state.
  Only the [roadmap](roadmap.md) and the register say when work occurs.
  Every other document describes the target design, in the current state only.

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
| [Corpus](corpus.md) | Data sources, license lanes, synthetic augmentation, per-variant use, and the data pipeline. |
| [Training](training.md) | CPT, augmentation generation, SFT, trace generation, and the compute budget. |
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
| [Implementation register](STATUS.md) | Each unit of the specification and its implementation state. |
| [Risks](risks.md) | Risks and their mitigations. |
