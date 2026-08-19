# Roadmap

Nine phases, in sequence.
Each phase gives a plan its scope, its exit criteria, and its documents.
A plan for a phase must satisfy the listed documents and the [decisions](decisions.md).

## Phase 0 — Bootstrap

- **Scope:** the monorepo scaffold, CI, the OpenTofu persistent stack, the development
  host (`infra/dev`), a train-stack round trip from CI, the spend guardrails, the
  runbooks, and the autonomous-development environment (toolchain, scoped credentials,
  OpenBSD qemu image, `CLAUDE.md`).
- **Exit criteria:**
  - CI is green.
  - CI applies and destroys the train stack end to end (`make infra-up STACK=train`,
    then `make infra-down STACK=train`), with the pipeline credential.
  - The development host is provisioned from `infra/dev`, and a rebuild from code
    reproduces it.
  - The spend guardrails are active: the billing alerts, the pre-apply consumption
    check, and the idle watchdog.
  - A development agent completes a full cycle without aid: plan → implement →
    `make check` → PR.
- **Documents:** [repository](repository.md), [infrastructure](infrastructure.md),
  [autonomous development](agents.md), [licensing and release](licensing.md).

## Phase 1 — Corpus

- **Scope:** mirror synchronization, the extraction pipeline, and both corpora with
  license tags.
- **Exit criteria:** `make data` reproducibly makes tagged, deduplicated,
  license-classed text.
  The corpus and licensing notes are published.
- **Documents:** [corpus](corpus.md), [licensing and release](licensing.md).

## Phase 2 — Harness slice and baseline evaluation

- **Scope:** build the **harness slice**: the shared artifacts (the system prompt, the
  tool metadata table and its JSON schemas, the error templates, and the re-prompt
  texts), and a minimal agent loop that drives a model through the agentic scenarios in
  the OpenBSD guests. The slice implements these units:

  - [HRN-PERL](harness.md#hrn-perl), [HRN-TOOL-TABLE](harness.md#hrn-tool-table),
    [HRN-TOOL-REPORT](harness.md#hrn-tool-report), [HRN-CALLS](harness.md#hrn-calls),
    [HRN-TRUNC](harness.md#hrn-trunc), and
    [HRN-SAFE-DRYRUN](harness.md#hrn-safe-dryrun), in full.
  - [HRN-LOOP](harness.md#hrn-loop) without HRN-LOOP-1.
  - [HRN-CONFIRM](harness.md#hrn-confirm) without HRN-CONFIRM-6 and HRN-CONFIRM-10.
  - [HRN-INVOKE](harness.md#hrn-invoke) without HRN-INVOKE-5.
  - [HRN-TOOL-RO](harness.md#hrn-tool-ro) without HRN-TOOL-RO-4.
  - [HRN-TOOL-GATE](harness.md#hrn-tool-gate) without HRN-TOOL-GATE-5.
  - [HRN-PROMPT](harness.md#hrn-prompt) without HRN-PROMPT-2 and without the skill-list
    chunk.
  - [HRN-BUDGETS](harness.md#hrn-budgets) without the context-overflow compaction.
  - A part of [INF-RUNTIME](inference.md#inf-runtime): the grammar constraint, prompt
    caching, and context shift off.

  The slice defers every other harness unit to Phase 6, among them the three-process
  privilege separation ([HRN-PROC](harness.md#hrn-proc)), pledge and unveil
  ([HRN-SAFE-PLEDGE](harness.md#hrn-safe-pledge)), the doas C wrappers
  ([HRN-SAFE-WRAP](harness.md#hrn-safe-wrap)), the control socket
  ([HRN-SOCKET](harness.md#hrn-socket)), and the port ([HRN-PKG](harness.md#hrn-pkg)).
  The [implementation register](STATUS.md) lists each unit and its “Done by” phase.
  Build the OpenBSD QA and agentic evaluation sets.
  Measure the [baseline grid](evaluation.md#baselines-and-ablations): the base model
  zero-shot, and the base model with the retrieval tool, both through the slice.
  Re-survey the Qwen line and pin the base-model revision ([base model](model.md)).
  Measure CPU tokens/s on real OpenBSD hardware with `llama-bench`, and measure full
  agent turns against the [latency budget](inference.md#latency-budget).

- **Exit criteria:** the shared artifacts are versioned in the repository.
  A baseline scorecard covers the pre-training rows of the grid.
  The first published OpenBSD CPU inference benchmark exists, with full-turn latency
  against the budget. If the retrieval baseline reaches the
  [release bars](evaluation.md#release-bars), a human reviews the value of training
  before Phase 3 starts.

- **Documents:** [evaluation](evaluation.md), [inference](inference.md),
  [harness](harness.md), [base model](model.md).

The slice exists so that the riskiest assumption — a 4B CPU model can drive the tool
loop — meets evidence before the training spend, and so that Phase 4 traces and the
agentic suite have real schemas and a real loop to run against.

## Phase 3 — Continued pretraining

- **Scope:** generate the synthetic augmentation of the clean corpus with the Qwen3-32B
  teacher, under the judge filter ([corpus](corpus.md#synthetic-augmentation),
  [training](training.md#augmentation-generation)). QLoRA CPT on the clean corpus plus
  the augmentation (H100-1-80G), with replay data and a low learning rate.
- **Exit criteria:** a CPT checkpoint with better domain perplexity than the base, a
  gain over the base on the OpenBSD QA set, and no MMLU regression.
- **Documents:** [corpus](corpus.md), [training](training.md),
  [infrastructure](infrastructure.md), [evaluation](evaluation.md).

## Phase 4 — SFT and agentic tuning

- **Scope:** generate synthetic tool-use traces with the Qwen3-32B teacher, from the
  shared harness artifacts of Phase 2: the system prompt, the tool schemas, and the
  error templates ([training](training.md)). Roll each trace out against a disposable
  OpenBSD guest, so each tool result is real output.
  Judge-filter the rollouts.
  Generate the grounded QA slice ([training](training.md#sft-pass)). Run SFT from the
  CPT checkpoint, on the traces and the grounded QA slice.
- **Exit criteria:** TTX 1 meets the pre-registered
  [release bars](evaluation.md#release-bars), measured against the full
  [baseline grid](evaluation.md#baselines-and-ablations).
  The escalation decision (4B versus 8B) is made.
- **Documents:** [training](training.md), [evaluation](evaluation.md),
  [base model](model.md), [corpus](corpus.md).

## Phase 5 — Quantization and export

- **Scope:** GGUF at Q4_K_M (canonical), Q5_K_M, and Q3_K_M. Validate quality retention.
  Sign the artifacts.
- **Exit criteria:** signed GGUF artifacts, and a quantization quality report.
- **Documents:** [inference](inference.md), [licensing and release](licensing.md).

## Phase 6 — Harness completion

- **Scope:** complete the Phase 2 slice into the full Perl harness:
  [HRN-PROC](harness.md#hrn-proc), [HRN-SAFE-PLEDGE](harness.md#hrn-safe-pledge),
  [HRN-SAFE-WRAP](harness.md#hrn-safe-wrap), [HRN-SOCKET](harness.md#hrn-socket), and
  [HRN-TRANSCRIPT](harness.md#hrn-transcript).
  Phase 6 completes each unit that the [implementation register](STATUS.md) lists with
  “Done by” 6. The llama-server integration study: the grammar constraint, prompt
  caching, context shift, the `/tokenize` endpoint, the sampler settings, and the abort
  of an in-flight generation ([harness](harness.md)). The transcript append discipline:
  the atomicity of one record write on a crash, and the fsync policy.
  The port skeleton builds.
- **Exit criteria:** the end-to-end TTX agent passes the evaluation suite in a VM, with
  no safety escape.
- **Documents:** [harness](harness.md), [evaluation](evaluation.md),
  [inference](inference.md).

## Phase 7 — TTX 1 release

- **Scope:** the weights (Apache 2.0), the model card, the harness port, the
  documentation, and the benchmark publication.
- **Exit criteria:** a signed and published release.
- **Documents:** [licensing and release](licensing.md).

## Phase 8 — Variants

- **Scope:** build the evaluation suites for the candidate personas.
  Run TTX 1 against them.
  Apply the promotion rule.
  Train and release the overlays that earn a release.
- **Exit criteria:** a recorded promotion decision for each candidate.
  Promoted variants are released with the same discipline as TTX 1.
- **Documents:** [variants](variants.md), [training](training.md),
  [evaluation](evaluation.md), [licensing and release](licensing.md),
  [base model](model.md).
