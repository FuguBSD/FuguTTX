# Training

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

### CPT pass

QLoRA continued pretraining on the redistributable-clean corpus.
1–2 epochs, low learning rate.
General-domain replay data is mixed in to prevent catastrophic forgetting.

### SFT pass

Supervised fine-tuning from the CPT checkpoint, on synthetic agentic traces: `pf.conf`
debug, `pkg_add` workflows, `sysctl` adjustment, `rcctl` service management.

### Trace generation

`ttx-synth` drives a **Qwen3-32B teacher**, served by vLLM on the same H100. At
generation time, tool calls are constrained to the JSON schemas of the harness.
A judge filter removes incorrect and unsafe traces before they enter the training set.
Traces contain no thinking blocks.
Traces target 8K tokens or less, to match the inference context budget.

### Execution

Training runs in the published Axolotl CUDA Docker image on the instance.
The Scaleway GPU OS image supplies the NVIDIA drivers, Docker, and the NVIDIA container
toolkit. All Axolotl YAML configurations live in `packages/ttx-train/configs/`, under
version control. A run is `just train cpt` or `just train sft` against a provisioned
instance. Checkpoints synchronize to Object Storage after each epoch.
Thus instance destruction cannot lose work.

## Budget

The budget is a guardrail, not the design constraint.
A documented monthly cap governs all cloud spend, and platform controls enforce it
([infrastructure](infrastructure.md)). The initial cap is **€1,500 per month**. Only a
human raises the cap.

Order-of-magnitude estimates, for one H100-1-80G at approximately €2.73/hour:

| Item | GPU-hours | Cost per run |
| --- | --- | --- |
| CPT pass (domain corpus, QLoRA, 1–2 epochs) | 10–20 | €28–55 |
| SFT pass (tens of thousands of traces) | 5–10 | €14–28 |
| Trace generation campaign (Qwen3-32B teacher) | 5–10 | €14–28 |

For evaluation and iteration, budget 2–3 times the clean-run cost, for sweeps and
restarts.

Continuous operation adds recurring items, per month:

| Item | Cost per month |
| --- | --- |
| Development host (Elastic Metal, `infra/dev`) | approximately €200–450 |
| GPU campaigns, in an active phase | approximately €300–800 |
| Object Storage, flexible IPs, and other items | below €50 |

Each promoted variant adds approximately €50–150 of GPU time.
Variants are SFT-dominated, because they share the CPT checkpoint
([variants](variants.md)).

Local development iteration is almost free: llama.cpp with Metal on Apple Silicon.
