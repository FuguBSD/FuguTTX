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

The register holds no schedule.
A slice plan in `plans/` names the units that it implements, and the gates of the
[roadmap](roadmap.md) read the register.

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

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [VAR-PERSONA](variants.md#var-persona) | The operator and contributor personas | n-a |  |
| [VAR-OVERLAY](variants.md#var-overlay) | Variants as SFT overlays on one CPT checkpoint | open |  |
| [VAR-PROMOTE](variants.md#var-promote) | The promotion rule | open |  |
| [VAR-CAND](variants.md#var-cand) | The candidate variants | n-a |  |
| [VAR-NAMES](variants.md#var-names) | Variant names and release versions | open |  |

## Base model

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [MDL-CRIT](model.md#mdl-crit) | The base-model selection criteria | n-a |  |
| [MDL-WHY](model.md#mdl-why) | The Qwen3-4B selection rationale | n-a |  |
| [MDL-PIN](model.md#mdl-pin) | The revision pin and re-survey | open |  |
| [MDL-EXCL](model.md#mdl-excl) | The excluded models | n-a |  |
| [MDL-ESC](model.md#mdl-esc) | The escalation rule to Qwen3-8B | open |  |
| [MDL-THINK](model.md#mdl-think) | Operation without thinking mode | open |  |
| [MDL-FALL](model.md#mdl-fall) | The fallback models | n-a |  |
| [MDL-VBASE](model.md#mdl-vbase) | Variant bases | open |  |

## Harness

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [HRN-SPLIT](harness.md#hrn-split) | The ttxd/ttx two-program split | open |  |
| [HRN-LANG](harness.md#hrn-lang) | The language constraint and the message framing | open |  |
| [HRN-PERL](harness.md#hrn-perl) | The Perl execution discipline | open |  |
| [HRN-ARCH](harness.md#hrn-arch) | The llama-server topology and the three system users | open |  |
| [HRN-PROC](harness.md#hrn-proc) | The three processes of ttxd | open |  |
| [HRN-SOCKET](harness.md#hrn-socket) | The control socket | open |  |
| [HRN-REPL](harness.md#hrn-repl) | The operator REPL on the Fugu::REPL module | open | The Fugu::REPL module does not exist in the Fugu distribution. Its interface contract lands there with the implementation. |
| [HRN-CONFIRM](harness.md#hrn-confirm) | The confirmation protocol: the dry-run gate and its digest binding | open |  |
| [HRN-TOOL-RO](harness.md#hrn-tool-ro) | The read-only tools | open |  |
| [HRN-TOOL-GATE](harness.md#hrn-tool-gate) | The gated mutations | open |  |
| [HRN-PF-COMMIT](harness.md#hrn-pf-commit) | The pf commit-confirm rule | open |  |
| [HRN-TOOL-REPORT](harness.md#hrn-tool-report) | The terminal report tool | open |  |
| [HRN-TOOL-TABLE](harness.md#hrn-tool-table) | The tool metadata table | open |  |
| [HRN-LOOP](harness.md#hrn-loop) | The agent loop | open |  |
| [HRN-CANCEL](harness.md#hrn-cancel) | Cancellation | open | The abort mechanism for an in-flight generation needs a design: signal routing across the processes, and `alarm()` around a blocked read. |
| [HRN-LIVE](harness.md#hrn-live) | The liveness events | open |  |
| [HRN-INVOKE](harness.md#hrn-invoke) | Model invocation | open | The `/tokenize` mechanism of HRN-INVOKE-5 needs validation against llama-server. |
| [HRN-PROMPT](harness.md#hrn-prompt) | Prompt assembly | open |  |
| [HRN-SKILLS](harness.md#hrn-skills) | Skills | open |  |
| [HRN-CALLS](harness.md#hrn-calls) | Tool-call handling | open |  |
| [HRN-TRUNC](harness.md#hrn-trunc) | Tool output truncation | open |  |
| [HRN-BUDGETS](harness.md#hrn-budgets) | The failure budgets | open | The context-overflow row needs the compaction of HRN-CONTEXT. |
| [HRN-CONTEXT](harness.md#hrn-context) | Context management | open |  |
| [HRN-TRANSCRIPT](harness.md#hrn-transcript) | The session transcript | open | The append discipline needs a design: the atomicity of one record write on a crash, and the fsync policy. No surveyed harness answers these questions. |
| [HRN-WIRELOG](harness.md#hrn-wirelog) | The raw wire log | open |  |
| [HRN-SAFE-PLEDGE](harness.md#hrn-safe-pledge) | pledge and unveil, per process | open |  |
| [HRN-SAFE-WRAP](harness.md#hrn-safe-wrap) | The fixed-function doas C wrappers | open |  |
| [HRN-SAFE-DRYRUN](harness.md#hrn-safe-dryrun) | Dry run by default | open |  |
| [HRN-SAFE-AUDIT](harness.md#hrn-safe-audit) | The audit record and its syslog duplicate | open |  |
| [HRN-SAFE-CONFID](harness.md#hrn-safe-confid) | Audit confidentiality | open |  |
| [HRN-SAFE-DROP](harness.md#hrn-safe-drop) | The privilege drop | open |  |
| [HRN-SAFE-DISPLAY](harness.md#hrn-safe-display) | The untrusted-display filter | open |  |
| [HRN-SAFE-RECORD](harness.md#hrn-safe-record) | The internal record trust boundary | open |  |
| [HRN-FETCH](harness.md#hrn-fetch) | Model fetch with signify validation | open |  |
| [HRN-PKG](harness.md#hrn-pkg) | The OpenBSD package | open |  |

## Inference

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [INF-RUNTIME](inference.md#inf-runtime) | The llama.cpp runtime and its required settings | open | The exact llama-server flags need validation. |
| [INF-FORMAT](inference.md#inf-format) | The GGUF format and the quantization levels | open |  |
| [INF-MEMFIT](inference.md#inf-memfit) | The memory fit in 16 GB | open |  |
| [INF-PERF](inference.md#inf-perf) | The performance measurement | open |  |
| [INF-LATENCY](inference.md#inf-latency) | The latency budget | open |  |
| [INF-ARM64](inference.md#inf-arm64) | The aarch64 build defect work | open |  |
| [INF-QUANT](inference.md#inf-quant) | The quantization procedure | open |  |
| [INF-DEVLOOP](inference.md#inf-devloop) | The development loop | open |  |
| [INF-NOGPU](inference.md#inf-nogpu) | GPU inference is not available on the target | n-a |  |
| [INF-INTEGRITY](inference.md#inf-integrity) | Release integrity for GGUF artifacts | open |  |

## Corpus

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [COR-SRC](corpus.md#cor-src) | The corpus sources | open |  |
| [COR-LANES](corpus.md#cor-lanes) | The license lanes and the manifest check | open |  |
| [COR-SYNTH](corpus.md#cor-synth) | The synthetic augmentation rules | open |  |
| [COR-REPLAY](corpus.md#cor-replay) | The replay-data rules | open |  |
| [COR-USE](corpus.md#cor-use) | The corpus use per variant | open |  |
| [COR-MIRROR](corpus.md#cor-mirror) | The mirrors and the commit pins | open |  |
| [COR-STAGES](corpus.md#cor-stages) | The pipeline stages | open |  |

## Training

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [TRN-INST](training.md#trn-inst) | The training instances | open |  |
| [TRN-CPT](training.md#trn-cpt) | The CPT pass | open |  |
| [TRN-AUG](training.md#trn-aug) | The augmentation generation | open |  |
| [TRN-SFT](training.md#trn-sft) | The SFT pass | open |  |
| [TRN-TRACES](training.md#trn-traces) | The trace generation and rollout | open |  |
| [TRN-EXEC](training.md#trn-exec) | The training execution | open |  |
| [TRN-BUDGET](training.md#trn-budget) | The training budget | open |  |

## Evaluation

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [EVL-GRID](evaluation.md#evl-grid) | The baseline grid and its ablations | open |  |
| [EVL-BARS](evaluation.md#evl-bars) | The release bars | open |  |
| [EVL-DOMAIN](evaluation.md#evl-domain) | The domain-knowledge suite | open |  |
| [EVL-QA](evaluation.md#evl-qa) | The OpenBSD QA set | open |  |
| [EVL-AGENTIC](evaluation.md#evl-agentic) | The agentic task suite | open |  |
| [EVL-CALLS](evaluation.md#evl-calls) | The tool-call correctness suite | open |  |
| [EVL-REDTEAM](evaluation.md#evl-redteam) | The safety red team | open |  |
| [EVL-RUNS](evaluation.md#evl-runs) | Where the suites run | open |  |

## Infrastructure

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [IAC-CODE](infrastructure.md#iac-code) | Infrastructure as code and the price rules | open |  |
| [IAC-REGION](infrastructure.md#iac-region) | The region and the zone | open |  |
| [IAC-PINS](infrastructure.md#iac-pins) | The version pins | open |  |
| [IAC-LAYOUT](infrastructure.md#iac-layout) | The stack layout | open |  |
| [IAC-TAGS](infrastructure.md#iac-tags) | The resource tags | open |  |
| [IAC-METAL](infrastructure.md#iac-metal) | The bare metal rule and the KVM test | open |  |
| [IAC-PERSIST](infrastructure.md#iac-persist) | The persistent stack | open |  |
| [IAC-DEV](infrastructure.md#iac-dev) | The development-host stack | open |  |
| [IAC-TRAIN](infrastructure.md#iac-train) | The train stack | open |  |
| [IAC-IMAGE](infrastructure.md#iac-image) | The image stack | open |  |
| [IAC-HOSTS](infrastructure.md#iac-hosts) | OpenBSD hosts on Scaleway | open |  |
| [IAC-DURA](infrastructure.md#iac-dura) | Durability | open |  |
| [IAC-STATE](infrastructure.md#iac-state) | The OpenTofu state | open | The OpenTofu encryption key providers need verification. Read the OpenTofu encryption documentation before you write the backend block. The bootstrap runbook closes this point. |
| [IAC-CRED](infrastructure.md#iac-cred) | The credentials | open |  |
| [IAC-TRAINCRED](infrastructure.md#iac-traincred) | The train credential | open |  |
| [IAC-SSH](infrastructure.md#iac-ssh) | The SSH keys | open |  |
| [IAC-EXCEPT](infrastructure.md#iac-except) | The resources outside OpenTofu | open |  |
| [IAC-PREREQ](infrastructure.md#iac-prereq) | The prerequisites | open | No source verifies a GPU price or an Object Storage price after 2026-06-01. The Elastic Metal prices in the document come from a recorded API response, read 2026-06-11. The cost of traffic between an instance and a bucket in the same region is unknown, and it is the largest unpriced item in the project. The live price read of IAC-PREREQ closes this point. |
| [IAC-SPEND](infrastructure.md#iac-spend) | The spend guardrails | open | The Billing API returns a list of budgets, and no source says that a second create fails. Import an existing budget before the first apply of `infra/persistent`. The bootstrap runbook closes this point. |
| [IAC-TEARDOWN](infrastructure.md#iac-teardown) | Teardown | open |  |
| [IAC-TASKS](infrastructure.md#iac-tasks) | The task runner | open |  |
| [IAC-CI](infrastructure.md#iac-ci) | CI | open |  |

## Repository

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [REP-TOOLS](repository.md#rep-tools) | The tool choices | open |  |
| [REP-LAYOUT](repository.md#rep-layout) | The monorepo layout | open |  |
| [REP-RECIPES](repository.md#rep-recipes) | The task targets | open |  |
| [REP-CI](repository.md#rep-ci) | The CI workflows | open |  |

## Autonomous development

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [AGT-IFACE](agents.md#agt-iface) | The repository as the interface | open |  |
| [AGT-RUNTIME](agents.md#agt-runtime) | The agent runtime environment | open |  |
| [AGT-CRED](agents.md#agt-cred) | The agent credentials | open |  |
| [AGT-SPEND](agents.md#agt-spend) | The agent spend controls | open |  |
| [AGT-FEEDBACK](agents.md#agt-feedback) | The feedback loops | open |  |
| [AGT-DOCS](agents.md#agt-docs) | The documentation duties | open |  |
| [AGT-HUMAN](agents.md#agt-human) | The human decision points | open |  |

## Licensing and release

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [LIC-LIC](licensing.md#lic-lic) | The component licenses | open |  |
| [LIC-DATA](licensing.md#lic-data) | The dataset cards | open |  |
| [LIC-CARDS](licensing.md#lic-cards) | The model cards | open |  |
| [LIC-RELEASE](licensing.md#lic-release) | Release integrity | open |  |

## Risks

| ID | Unit | State | Note |
| --- | --- | --- | --- |
| [RSK-HALL](risks.md#rsk-hall) | Hallucination on destructive commands | n-a |  |
| [RSK-INJECT](risks.md#rsk-inject) | Prompt injection through tool output | n-a |  |
| [RSK-STALE](risks.md#rsk-stale) | Corpus staleness versus `-current` | n-a |  |
| [RSK-EVAL](risks.md#rsk-eval) | Evaluation difficulty | n-a |  |
| [RSK-CPT](risks.md#rsk-cpt) | CPT can add too little knowledge | n-a |  |
| [RSK-SYNTH](risks.md#rsk-synth) | Synthetic data quality | n-a |  |
| [RSK-LANES](risks.md#rsk-lanes) | Licensing lane discipline | n-a |  |
| [RSK-PRICE](risks.md#rsk-price) | Price and availability drift | n-a |  |
| [RSK-BLAST](risks.md#rsk-blast) | Autonomous-operation blast radius | n-a |  |

## Retired IDs

| ID | Unit |
| --- | --- |
