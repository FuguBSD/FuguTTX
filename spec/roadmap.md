# Roadmap

Nine phases, in sequence. Each phase gives a plan its scope, its exit criteria, and its documents. A plan for a phase must satisfy the listed documents and the [decisions](decisions.md).

## Phase 0 — Bootstrap

- **Scope:** the monorepo scaffold, CI, the OpenTofu persistent stack, a train-stack round trip, the runbooks, and the autonomous-development environment (toolchain, scoped credentials, OpenBSD qemu image, `CLAUDE.md`).
- **Exit criteria:**
  - CI is green.
  - `just infra-up train` and then `just infra-down train` complete end to end.
  - A development agent completes a full cycle without aid: plan → implement → `just check` → PR.
- **Documents:** [repository](repository.md), [infrastructure](infrastructure.md), [autonomous development](agents.md).

## Phase 1 — Corpus

- **Scope:** mirror synchronization, the extraction pipeline, and both corpora with license tags.
- **Exit criteria:** `just data` reproducibly makes tagged, deduplicated, license-classed text. The corpus and licensing notes are published.
- **Documents:** [corpus](corpus.md), [licensing and release](licensing.md).

## Phase 2 — Baseline evaluation

- **Scope:** build the OpenBSD QA and agentic evaluation sets. Benchmark Qwen3-4B zero-shot on OpenBSD tasks. Measure CPU tokens/s on real OpenBSD hardware with `llama-bench`.
- **Exit criteria:** a baseline scorecard, and the first published OpenBSD CPU inference benchmark.
- **Documents:** [evaluation](evaluation.md), [inference](inference.md).

## Phase 3 — Continued pretraining

- **Scope:** QLoRA CPT on the clean corpus (H100-1-80G), with replay data and a low learning rate.
- **Exit criteria:** a CPT checkpoint with better domain perplexity than the base, and no MMLU regression.
- **Documents:** [training](training.md), [infrastructure](infrastructure.md).

## Phase 4 — SFT and agentic tuning

- **Scope:** generate and judge-filter synthetic tool-use traces with the Qwen3-32B teacher. Run SFT from the CPT checkpoint.
- **Exit criteria:** the agentic evaluation pass-rate threshold is met. Tool-call validity is high. The escalation decision (4B versus 8B) is made.
- **Documents:** [training](training.md), [evaluation](evaluation.md), [base model](model.md).

## Phase 5 — Quantization and export

- **Scope:** GGUF at Q4_K_M (canonical), Q5_K_M, and Q3_K_M. Validate quality retention. Sign the artifacts.
- **Exit criteria:** signed GGUF artifacts, and a quantization quality report.
- **Documents:** [inference](inference.md), [licensing and release](licensing.md).

## Phase 6 — Harness integration

- **Scope:** the complete Perl harness, with pledge/unveil, doas policies, dry-run gates, and the audit log. The port skeleton builds.
- **Exit criteria:** the end-to-end TTX agent passes the evaluation suite in a VM, with no safety escape.
- **Documents:** [harness](harness.md), [evaluation](evaluation.md).

## Phase 7 — TTX 1 release

- **Scope:** the weights (Apache 2.0), the model card, the harness port, the documentation, and the benchmark publication.
- **Exit criteria:** a signed and published release.
- **Documents:** [licensing and release](licensing.md).

## Phase 8 — Variants

- **Scope:** build the evaluation suites for the candidate personas. Run TTX 1 against them. Apply the promotion rule. Train and release the overlays that earn a release.
- **Exit criteria:** a recorded promotion decision for each candidate. Promoted variants are released with the same discipline as TTX 1.
- **Documents:** [variants](variants.md), [training](training.md), [evaluation](evaluation.md), [licensing and release](licensing.md).
