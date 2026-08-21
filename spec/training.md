# Training

<a id="trn-inst"></a>

## Instances

Scaleway, in zone `fr-par-2` ([infrastructure](infrastructure.md)). On-demand billing,
per minute of uptime, with a documented minimum of 60 minutes.

| Instance | GPUs | GPU VRAM | System RAM | €/hour |
| --- | --- | --- | --- | --- |
| H100-1-80G | 1× H100 PCIe | 80 GB | 240 GB | €2.73 |
| L40S-1-48G | 1× L40S | 48 GB | 96 GB | €1.47 |

**Each price in this table is unverified.** Scaleway revised prices on 2026-06-01, and
no reachable source confirmed a GPU price after that date
([review](../docs/research/scaleway-infrastructure-review.md)). Read the live price
before you plan a campaign.
Scaleway grants no quota for an H100 offer, so an operator must request the quota before
the first apply.

Extra billed items: the block root volume, the routed IPv4 address, and Object Storage.
Scratch NVMe is ephemeral: it disappears at instance deletion.
By design, nothing durable lives on the instance.

**The H100-1-80G is the standard training instance.** It is the default in the OpenTofu
train stack.
80 GB holds a 4B or 8B model plus the QLoRA optimizer state at long context,
with a large margin.
Public reference points: an 8B QLoRA run of 2 epochs completes in approximately 3–6
hours on one high-end GPU; a 7B QLoRA run peaks below 8 GiB of VRAM. The `instance_type`
variable exposes the L40S-1-48G for budget runs at 4B. QLoRA on one H100 covers the full
range up to 14B. Multi-GPU is not necessary.

## Method

<a id="trn-cpt"></a>

### CPT pass

The CPT pass carries the primary OpenBSD knowledge of the model (D4). QLoRA continued
pretraining trains on the redistributable-clean corpus plus its
[synthetic augmentation](corpus.md#synthetic-augmentation).
1–2 epochs, low learning rate.
General-domain replay data is mixed in to prevent catastrophic forgetting.
The replay data follows the [replay rules](corpus.md#replay-data) of the corpus.

<a id="trn-aug"></a>

### Augmentation generation

`ttx-synth` drives a **Qwen3-32B teacher**, served by vLLM on the same H100. The
[trace generation](#trace-generation) uses the same teacher.
The teacher rewrites each prose chunk of the clean corpus into paraphrases,
question-and-answer pairs, and fact summaries.
The generation prompt contains the source chunk, and the output must restate the facts
of that chunk only. A judge filter compares each record against its source chunk.
The filter drops each record that contradicts the source, and each record that adds a
fact the source does not state.
The augmentation targets three to five accepted restatements per source chunk.
The data rules of the augmentation — the lanes, the tags, and the evaluation splits —
are in the [corpus](corpus.md#synthetic-augmentation).

<a id="trn-sft"></a>

### SFT pass

Supervised fine-tuning from the CPT checkpoint, on two data kinds:

- Synthetic agentic traces: `pf.conf` debug, `pkg_add` workflows, `sysctl` adjustment,
  `rcctl` service management.
- A grounded QA slice: single-turn question-and-answer items, generated from the man
  pages and the FAQ with the source chunk in the prompt, under the augmentation rules
  ([corpus](corpus.md#synthetic-augmentation)). The slice trains fact recall in the
  answer format of the agent.

The corpus components that seed the scenarios of each variant are specified in the
[corpus](corpus.md#corpus-use-per-variant).

<a id="trn-traces"></a>

### Trace generation

`ttx-synth` drives the same **Qwen3-32B teacher** as the
[augmentation generation](#augmentation-generation).
At generation time, tool calls are constrained to the JSON schemas of the harness.
A judge filter removes incorrect and unsafe traces before they enter the training set.
Traces contain no thinking blocks.
Traces target 8K tokens or less, to match the inference context budget.

**The teacher proposes, and a rollout executes.** The rollout driver runs on the
development host.
It rolls each trace out against a disposable OpenBSD guest, through the
agent loop of the harness ([harness](harness.md#hrn-loop)), with a snapshot restore
between traces. Each tool result in a trace is the real output of the guest.
A teacher-written observation must not enter a trace.
A trace with a fabricated observation teaches the model to expect fabricated systems.
The driver reaches the teacher over an SSH tunnel to the train instance, and the vLLM
endpoint binds to localhost on that instance.
A trace enters the training set only when both checks pass: the scenario check passes in
the guest, and the judge filter accepts the trace.

The harness format and the training format must not drift.
The system prompt, the tool schemas, the error templates, and the re-prompt texts are
shared artifacts, defined once in the repository.
`ttx-synth` must read them from the same source as the harness ([harness](harness.md)).
Each trace must end its step with the terminal `report` tool.
The trace set must include recovery examples: a malformed call, its precise error
result, and the corrected call.

<a id="trn-exec"></a>

### Execution

Training runs in the published Axolotl CUDA Docker image on the instance.
The Scaleway GPU OS image supplies the NVIDIA drivers, Docker, and the NVIDIA container
toolkit. All Axolotl YAML configurations live in `packages/ttx-train/configs/`, under
version control. A run is `make train-cpt` or `make train-sft` against a provisioned
instance. Checkpoints synchronize to Object Storage after each epoch.
Thus instance destruction cannot lose work.

<a id="trn-budget"></a>

## Budget

The budget is a guardrail, not the design constraint.
A documented monthly cap governs all cloud spend, and platform controls enforce it
([infrastructure](infrastructure.md)). The initial cap is **€1,500 per month**. Only a
human raises the cap.

Order-of-magnitude estimates, for one H100-1-80G at approximately €2.73/hour:

| Item | GPU-hours | Cost per run |
| --- | --- | --- |
| Augmentation campaign (Qwen3-32B teacher) | 10–30 | €28–82 |
| CPT pass (corpus plus augmentation, QLoRA, 1–2 epochs) | 15–40 | €41–110 |
| SFT pass (tens of thousands of traces, plus the grounded QA slice) | 5–10 | €14–28 |
| Trace generation campaign (Qwen3-32B teacher) | 5–10 | €14–28 |

For evaluation and iteration, budget 2–3 times the clean-run cost, for sweeps and
restarts.

Continuous operation adds recurring items, per month:

| Item | Cost per month |
| --- | --- |
| Development host (Elastic Metal, `infra/dev`) | approximately €200–450 |
| GPU campaigns, in a campaign month | approximately €300–800 |
| Object Storage, flexible IPs, and other items | below €50 |

Each promoted variant adds approximately €50–150 of GPU time.
Variants are SFT-dominated, because they share the CPT checkpoint
([variants](variants.md)).

Local development iteration is almost free: llama.cpp with Metal on Apple Silicon.
