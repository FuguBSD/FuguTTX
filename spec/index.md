# FuguTTX Specification

FuguTTX is a project that makes **TTX 1**. TTX 1 is a small language model,
fine-tuned on OpenBSD knowledge. It operates locally and offline on OpenBSD
machines, on the CPU only. The model and the harness together make the **TTX
agent**: a task agent for OpenBSD system administration.

The name refers to tetrodotoxin (TTX), the toxin of the fugu pufferfish. The
mascot of OpenBSD is a pufferfish.

The recipe is short:

1. Fine-tune Qwen3-4B (Apache 2.0) with QLoRA: continued pretraining (CPT) on
   the corpus and its synthetic augmentation, then agentic supervised
   fine-tuning (SFT).
2. Train on one Scaleway H100 instance. Destroy the instance after each session.
3. Quantize to GGUF Q4_K_M.
4. Serve with the OpenBSD `misc/llama.cpp` port, CPU only, in 16 GB RAM.

A monthly budget governs all cloud spend. The initial budget is €1,500. A
per-Organization quota is the guardrail that blocks. The budget and its alerts
notify only ([infrastructure](infrastructure.md)).

This document is the entry point of the specification. It holds the plan
contract, the ID conventions, and the document tables.

## Plan contract

- Read [DECISIONS.md](DECISIONS.md) before you make a plan.
- A plan must not go against a decision. To go against a decision, propose a
  change to [DECISIONS.md](DECISIONS.md) and get human approval first.
- Take the next slice from the [roadmap](ROADMAP.md). The roadmap gives the
  method: the slice rule, the slice kinds, the thinning axes, the rails, the
  gates, and the order rule.
- A plan must cite each unit that it implements, for example
  `Implements: HRN-CONFIRM`.
- A plan can exclude a rule from a cited unit with `without`, for example
  `Implements: HRN-CONFIRM without HRN-CONFIRM-6`.
- A plan must cite each unit that it touches but defers, for example
  `Defers: HRN-SOCKET`.
- A slice plan also states the slice kind, the thinning axes, and the
  measurement that ends the slice. An experiment-slice plan adds the hypothesis
  and the cost cap.
- The change that implements a unit, or a part of a unit, must set the state of
  the unit in [STATUS.md](STATUS.md) in the same change.

<a id="conventions"></a>

## Conventions

A unit is one implementable design element. An invisible HTML anchor marks each
unit, and the unit ID is the anchor in upper case:

```markdown
<a id="hrn-confirm"></a>

## Confirmation protocol

- **HRN-CONFIRM-1** — The harness must …
```

- The anchor of a unit must start with the code of its document, in lower case,
  followed by a hyphen.
- A unit extends from its anchor to the next unit anchor or heading, whichever
  comes first.
- A rule ID names one requirement inside a unit. A rule is a bold-lead list
  item: the bold rule ID, one em dash, then the requirement text, as the example
  above shows.
- Rule numbers only append: never renumber a rule, and never reuse a number.
- An ID must not change. To retire a unit: delete its anchor and its register
  row, and add the ID to the "Retired IDs" table of [STATUS.md](STATUS.md).
- Each document describes the target design in the current state only. Only
  [ROADMAP.md](ROADMAP.md) and [STATUS.md](STATUS.md) say when work occurs.
- A citation of a unit of a sibling repository is a prose token with the
  repository name in front, for example Fugu ARC-BOUNDARY. It is never a link,
  and it never names a plan.
- Prices and model data show the state at the time of publication. Confirm them
  before each campaign.

## Specification documents

Each document specifies one area of work. The code of a document prefixes the
IDs of its units.

| Code | Document                               | Area                                                             |
| ---- | -------------------------------------- | ---------------------------------------------------------------- |
| HRN  | [harness.md](harness.md)               | The Perl harness on OpenBSD and its safety design                |
| IAC  | [infrastructure.md](infrastructure.md) | Scaleway resources as OpenTofu code                              |
| COR  | [corpus.md](corpus.md)                 | Data sources, license lanes, augmentation, and the data pipeline |
| TRN  | [training.md](training.md)             | CPT, SFT, trace generation, and the compute budget               |
| EVL  | [evaluation.md](evaluation.md)         | The five evaluation suites and the release gates                 |
| INF  | [inference.md](inference.md)           | Quantization, memory fit, and CPU inference on OpenBSD           |
| MDL  | [model.md](model.md)                   | Base model selection, escalation rule, and fallbacks             |
| VAR  | [variants.md](variants.md)             | User personas and the promotion rule for variants                |
| REP  | [repository.md](repository.md)         | Monorepo layout, tools, task runner, and CI                      |
| AGT  | [agents.md](agents.md)                 | Development agents, credentials, and human decision points       |
| LIC  | [licensing.md](licensing.md)           | Licenses, dataset cards, model cards, and release integrity      |
| RSK  | [risks.md](risks.md)                   | Risks and their mitigations                                      |

## Governance documents

These documents carry no units.

| Document                     | Role                                                        |
| ---------------------------- | ----------------------------------------------------------- |
| [overview.md](overview.md)   | Goals, non-goals, and terminology.                          |
| [DECISIONS.md](DECISIONS.md) | The decisions. A plan must not go against a decision.       |
| [ROADMAP.md](ROADMAP.md)     | The slice method, the rails, the gates, and the order rule. |
| [STATUS.md](STATUS.md)       | The implementation register.                                |
