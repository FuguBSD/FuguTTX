# Implementation register

This register is the one record of implementation state.
One row exists for each unit of the specification.
A unit is one design element of one specification document.
The [conventions](index.md#conventions) define the unit IDs.
Each row describes the current state only.
A row must not carry a plan name or a reference to an earlier state.
A note can carry the date of a recorded fact.

## States

| State | Meaning |
| --- | --- |
| open | No code implements the unit. |
| partial | Code implements a part of the unit. The note names each absent part. |
| done | Code implements the full unit. The note links the code or the tests. |
| n-a | No code can implement the unit. It exists for citation only. |

The “Done by” column names a phase of the [roadmap](roadmap.md).
At the exit of that phase, the unit must have the state `done`. A unit can reach `done`
before that phase. An `n-a` unit has no “Done by” value.

## Update protocol

1. The change that implements a unit, or a part of a unit, sets the state of the unit in
   this register, in the same change.
2. A `partial` note names each absent rule or part.
   For each absent part, the note names the unit that the part needs.
3. A `done` note holds at least one relative link to code or to tests.
4. A change to the text of a `partial` or `done` unit updates the row of that unit in
   the same change. The CI drift check enforces this rule.
5. The human merge review compares the register diff with the code diff.

## Code roots

| Document | Roots |
| --- | --- |
| harness.md | `harness/` |
| infrastructure.md | `infra/`, `.github/workflows/` |
| corpus.md | `packages/ttx-data/` |
| training.md | `packages/ttx-train/`, `packages/ttx-synth/` |
| evaluation.md | `packages/ttx-eval/` |
| inference.md | `packages/ttx-quant/`, `packages/ttx-eval/` |
| model.md | `packages/ttx-train/` |
| variants.md | `packages/ttx-train/`, `packages/ttx-eval/` |
| repository.md | `Makefile`, `scripts/`, `.github/workflows/` |
| agents.md | `CLAUDE.md`, `.claude/` |
| licensing.md | `models/`, `datasets/`, `docs/` |
| risks.md | — |

## Variants

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [VAR-PERSONA](variants.md#var-persona) | The operator and contributor personas | — | n-a |  |
| [VAR-OVERLAY](variants.md#var-overlay) | Variants as SFT overlays on one CPT checkpoint | 8 | open |  |
| [VAR-PROMOTE](variants.md#var-promote) | The promotion rule | 8 | open |  |
| [VAR-CAND](variants.md#var-cand) | The candidate variants | — | n-a |  |
| [VAR-NAMES](variants.md#var-names) | Variant names and release versions | 8 | open |  |

## Base model

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [MDL-CRIT](model.md#mdl-crit) | The base-model selection criteria | — | n-a |  |
| [MDL-WHY](model.md#mdl-why) | The Qwen3-4B selection rationale | — | n-a |  |
| [MDL-PIN](model.md#mdl-pin) | The revision pin and re-survey | 2 | open |  |
| [MDL-EXCL](model.md#mdl-excl) | The excluded models | — | n-a |  |
| [MDL-ESC](model.md#mdl-esc) | The escalation rule to Qwen3-8B | 4 | open |  |
| [MDL-THINK](model.md#mdl-think) | Operation without thinking mode | 2 | open |  |
| [MDL-FALL](model.md#mdl-fall) | The fallback models | — | n-a |  |
| [MDL-VBASE](model.md#mdl-vbase) | Variant bases | 8 | open |  |

## Harness

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [HRN-SPLIT](harness.md#hrn-split) | The ttxd/ttx two-program split | 6 | open |  |
| [HRN-LANG](harness.md#hrn-lang) | The language constraint and the message framing | 6 | open |  |
| [HRN-PERL](harness.md#hrn-perl) | The Perl execution discipline | 2 | open |  |
| [HRN-ARCH](harness.md#hrn-arch) | The llama-server topology and the three system users | 6 | open |  |
| [HRN-PROC](harness.md#hrn-proc) | The three processes of ttxd | 6 | open |  |
| [HRN-SOCKET](harness.md#hrn-socket) | The control socket | 6 | open |  |
| [HRN-REPL](harness.md#hrn-repl) | The operator REPL on the Fugu::REPL module | 6 | open | The Fugu::REPL module does not exist in the Fugu distribution. Its interface contract lands there with the implementation. |
| [HRN-CONFIRM](harness.md#hrn-confirm) | The confirmation protocol: the dry-run gate and its digest binding | 6 | open |  |
| [HRN-TOOL-RO](harness.md#hrn-tool-ro) | The read-only tools | 6 | open |  |
| [HRN-TOOL-GATE](harness.md#hrn-tool-gate) | The gated mutations | 6 | open |  |
| [HRN-PF-COMMIT](harness.md#hrn-pf-commit) | The pf commit-confirm rule | 6 | open |  |
| [HRN-TOOL-REPORT](harness.md#hrn-tool-report) | The terminal report tool | 2 | open |  |
| [HRN-TOOL-TABLE](harness.md#hrn-tool-table) | The tool metadata table | 2 | open |  |
| [HRN-LOOP](harness.md#hrn-loop) | The agent loop | 6 | open |  |
| [HRN-CANCEL](harness.md#hrn-cancel) | Cancellation | 6 | open | The abort mechanism for an in-flight generation needs a design: signal routing across the processes, and `alarm()` around a blocked read. |
| [HRN-LIVE](harness.md#hrn-live) | The liveness events | 6 | open |  |
| [HRN-INVOKE](harness.md#hrn-invoke) | Model invocation | 6 | open | The `/tokenize` mechanism of HRN-INVOKE-5 needs validation against llama-server. |
| [HRN-PROMPT](harness.md#hrn-prompt) | Prompt assembly | 6 | open |  |
| [HRN-SKILLS](harness.md#hrn-skills) | Skills | 6 | open |  |
| [HRN-CALLS](harness.md#hrn-calls) | Tool-call handling | 2 | open |  |
| [HRN-TRUNC](harness.md#hrn-trunc) | Tool output truncation | 2 | open |  |
| [HRN-BUDGETS](harness.md#hrn-budgets) | The failure budgets | 6 | open | The context-overflow row needs the compaction of HRN-CONTEXT. |
| [HRN-CONTEXT](harness.md#hrn-context) | Context management | 6 | open |  |
| [HRN-TRANSCRIPT](harness.md#hrn-transcript) | The session transcript | 6 | open | The append discipline needs a design: the atomicity of one record write on a crash, and the fsync policy. No surveyed harness answers these questions. |
| [HRN-WIRELOG](harness.md#hrn-wirelog) | The raw wire log | 6 | open |  |
| [HRN-SAFE-PLEDGE](harness.md#hrn-safe-pledge) | pledge and unveil, per process | 6 | open |  |
| [HRN-SAFE-WRAP](harness.md#hrn-safe-wrap) | The fixed-function doas C wrappers | 6 | open |  |
| [HRN-SAFE-DRYRUN](harness.md#hrn-safe-dryrun) | Dry run by default | 2 | open |  |
| [HRN-SAFE-AUDIT](harness.md#hrn-safe-audit) | The audit record and its syslog duplicate | 6 | open |  |
| [HRN-SAFE-CONFID](harness.md#hrn-safe-confid) | Audit confidentiality | 6 | open |  |
| [HRN-SAFE-DROP](harness.md#hrn-safe-drop) | The privilege drop | 6 | open |  |
| [HRN-SAFE-DISPLAY](harness.md#hrn-safe-display) | The untrusted-display filter | 6 | open |  |
| [HRN-SAFE-RECORD](harness.md#hrn-safe-record) | The internal record trust boundary | 6 | open |  |
| [HRN-FETCH](harness.md#hrn-fetch) | Model fetch with signify validation | 6 | open |  |
| [HRN-PKG](harness.md#hrn-pkg) | The OpenBSD package | 6 | open |  |

## Inference

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [INF-RUNTIME](inference.md#inf-runtime) | The llama.cpp runtime and its required settings | 6 | open | The exact llama-server flags need validation. |
| [INF-FORMAT](inference.md#inf-format) | The GGUF format and the quantization levels | 5 | open |  |
| [INF-MEMFIT](inference.md#inf-memfit) | The memory fit in 16 GB | 2 | open |  |
| [INF-PERF](inference.md#inf-perf) | The performance measurement | 2 | open |  |
| [INF-LATENCY](inference.md#inf-latency) | The latency budget | 2 | open |  |
| [INF-ARM64](inference.md#inf-arm64) | The aarch64 build defect work | 2 | open |  |
| [INF-QUANT](inference.md#inf-quant) | The quantization procedure | 5 | open |  |
| [INF-DEVLOOP](inference.md#inf-devloop) | The development loop | 2 | open |  |
| [INF-NOGPU](inference.md#inf-nogpu) | GPU inference is not available on the target | — | n-a |  |
| [INF-INTEGRITY](inference.md#inf-integrity) | Release integrity for GGUF artifacts | 5 | open |  |

## Corpus

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [COR-SRC](corpus.md#cor-src) | The corpus sources | 1 | open |  |
| [COR-LANES](corpus.md#cor-lanes) | The license lanes and the manifest check | 1 | open |  |
| [COR-SYNTH](corpus.md#cor-synth) | The synthetic augmentation rules | 3 | open |  |
| [COR-REPLAY](corpus.md#cor-replay) | The replay-data rules | 3 | open |  |
| [COR-USE](corpus.md#cor-use) | The corpus use per variant | 4 | open |  |
| [COR-MIRROR](corpus.md#cor-mirror) | The mirrors and the commit pins | 1 | open |  |
| [COR-STAGES](corpus.md#cor-stages) | The pipeline stages | 1 | open |  |

## Training

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [TRN-INST](training.md#trn-inst) | The training instances | 3 | open |  |
| [TRN-CPT](training.md#trn-cpt) | The CPT pass | 3 | open |  |
| [TRN-AUG](training.md#trn-aug) | The augmentation generation | 3 | open |  |
| [TRN-SFT](training.md#trn-sft) | The SFT pass | 4 | open |  |
| [TRN-TRACES](training.md#trn-traces) | The trace generation and rollout | 4 | open |  |
| [TRN-EXEC](training.md#trn-exec) | The training execution | 3 | open |  |
| [TRN-BUDGET](training.md#trn-budget) | The training budget | 3 | open |  |

## Evaluation

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [EVL-GRID](evaluation.md#evl-grid) | The baseline grid and its ablations | 4 | open |  |
| [EVL-BARS](evaluation.md#evl-bars) | The release bars | 2 | open |  |
| [EVL-DOMAIN](evaluation.md#evl-domain) | The domain-knowledge suite | 3 | open |  |
| [EVL-QA](evaluation.md#evl-qa) | The OpenBSD QA set | 2 | open |  |
| [EVL-AGENTIC](evaluation.md#evl-agentic) | The agentic task suite | 2 | open |  |
| [EVL-CALLS](evaluation.md#evl-calls) | The tool-call correctness suite | 2 | open |  |
| [EVL-REDTEAM](evaluation.md#evl-redteam) | The safety red team | 6 | open |  |
| [EVL-RUNS](evaluation.md#evl-runs) | Where the suites run | 3 | open |  |

## Infrastructure

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [IAC-CODE](infrastructure.md#iac-code) | Infrastructure as code and the price rules | 0 | open |  |
| [IAC-REGION](infrastructure.md#iac-region) | The region and the zone | 0 | open |  |
| [IAC-PINS](infrastructure.md#iac-pins) | The version pins | 0 | open |  |
| [IAC-LAYOUT](infrastructure.md#iac-layout) | The stack layout | 0 | open |  |
| [IAC-TAGS](infrastructure.md#iac-tags) | The resource tags | 0 | open |  |
| [IAC-METAL](infrastructure.md#iac-metal) | The bare metal rule and the KVM test | 0 | open |  |
| [IAC-PERSIST](infrastructure.md#iac-persist) | The persistent stack | 0 | open |  |
| [IAC-DEV](infrastructure.md#iac-dev) | The development-host stack | 0 | open |  |
| [IAC-TRAIN](infrastructure.md#iac-train) | The train stack | 0 | open |  |
| [IAC-IMAGE](infrastructure.md#iac-image) | The image stack | 0 | open |  |
| [IAC-HOSTS](infrastructure.md#iac-hosts) | OpenBSD hosts on Scaleway | 0 | open |  |
| [IAC-DURA](infrastructure.md#iac-dura) | Durability | 0 | open |  |
| [IAC-STATE](infrastructure.md#iac-state) | The OpenTofu state | 0 | open | The OpenTofu encryption key providers need verification. Read the OpenTofu encryption documentation before you write the backend block. The bootstrap runbook closes this point. |
| [IAC-CRED](infrastructure.md#iac-cred) | The credentials | 0 | open |  |
| [IAC-TRAINCRED](infrastructure.md#iac-traincred) | The train credential | 0 | open |  |
| [IAC-SSH](infrastructure.md#iac-ssh) | The SSH keys | 0 | open |  |
| [IAC-EXCEPT](infrastructure.md#iac-except) | The resources outside OpenTofu | 0 | open |  |
| [IAC-PREREQ](infrastructure.md#iac-prereq) | The prerequisites | 0 | open | No source verifies a GPU price or an Object Storage price after 2026-06-01. The Elastic Metal prices in the document come from a recorded API response, read 2026-06-11. The cost of traffic between an instance and a bucket in the same region is unknown, and it is the largest unpriced item in the project. The live price read of IAC-PREREQ closes this point. |
| [IAC-SPEND](infrastructure.md#iac-spend) | The spend guardrails | 0 | open | The Billing API returns a list of budgets, and no source says that a second create fails. Import an existing budget before the first apply of `infra/persistent`. The bootstrap runbook closes this point. |
| [IAC-TEARDOWN](infrastructure.md#iac-teardown) | Teardown | 0 | open |  |
| [IAC-TASKS](infrastructure.md#iac-tasks) | The task runner | 0 | open |  |
| [IAC-CI](infrastructure.md#iac-ci) | CI | 0 | open |  |

## Repository

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [REP-TOOLS](repository.md#rep-tools) | The tool choices | 0 | open |  |
| [REP-LAYOUT](repository.md#rep-layout) | The monorepo layout | 0 | open |  |
| [REP-RECIPES](repository.md#rep-recipes) | The task targets | 0 | open |  |
| [REP-CI](repository.md#rep-ci) | The CI workflows | 0 | open |  |

## Autonomous development

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [AGT-IFACE](agents.md#agt-iface) | The repository as the interface | 0 | open |  |
| [AGT-RUNTIME](agents.md#agt-runtime) | The agent runtime environment | 0 | open |  |
| [AGT-CRED](agents.md#agt-cred) | The agent credentials | 0 | open |  |
| [AGT-SPEND](agents.md#agt-spend) | The agent spend controls | 0 | open |  |
| [AGT-FEEDBACK](agents.md#agt-feedback) | The feedback loops | 0 | open |  |
| [AGT-DOCS](agents.md#agt-docs) | The documentation duties | 0 | open |  |
| [AGT-HUMAN](agents.md#agt-human) | The human decision points | 0 | open |  |

## Licensing and release

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [LIC-LIC](licensing.md#lic-lic) | The component licenses | 0 | open |  |
| [LIC-DATA](licensing.md#lic-data) | The dataset cards | 1 | open |  |
| [LIC-CARDS](licensing.md#lic-cards) | The model cards | 7 | open |  |
| [LIC-RELEASE](licensing.md#lic-release) | Release integrity | 7 | open |  |

## Risks

| ID | Unit | Done by | State | Note |
| --- | --- | --- | --- | --- |
| [RSK-HALL](risks.md#rsk-hall) | Hallucination on destructive commands | — | n-a |  |
| [RSK-INJECT](risks.md#rsk-inject) | Prompt injection through tool output | — | n-a |  |
| [RSK-STALE](risks.md#rsk-stale) | Corpus staleness versus `-current` | — | n-a |  |
| [RSK-EVAL](risks.md#rsk-eval) | Evaluation difficulty | — | n-a |  |
| [RSK-CPT](risks.md#rsk-cpt) | CPT can add too little knowledge | — | n-a |  |
| [RSK-SYNTH](risks.md#rsk-synth) | Synthetic data quality | — | n-a |  |
| [RSK-LANES](risks.md#rsk-lanes) | Licensing lane discipline | — | n-a |  |
| [RSK-PRICE](risks.md#rsk-price) | Price and availability drift | — | n-a |  |
| [RSK-BLAST](risks.md#rsk-blast) | Autonomous-operation blast radius | — | n-a |  |

## Retired IDs

| ID | Unit |
| --- | --- |
