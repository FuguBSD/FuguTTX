# Training

## Instances

Scaleway, in Paris PAR-2 or Warsaw WAW-2. On-demand, per-minute billing. Prices before tax, "starting at" values.

| Instance | GPUs | GPU VRAM | System RAM | €/hour |
|---|---|---|---|---|
| H100-1-80G | 1× H100 PCIe | 80 GB | 240 GB | €2.73 |
| L40S-1-48G | 1× L40S | 48 GB | 96 GB | €1.47 |

Extra billed items: Block Storage (root volume), Flexible IP (€0.004/hour), Object Storage. Scratch NVMe is ephemeral: it disappears at instance deletion. By design, nothing durable lives on the instance.

**The H100-1-80G is the standard training instance.** It is the default in the OpenTofu train stack. 80 GB holds a 4B or 8B model plus the QLoRA optimizer state at long context, with a large margin. Public reference points: an 8B QLoRA run of 2 epochs completes in approximately 3–6 hours on one high-end GPU; a 7B QLoRA run peaks below 8 GiB of VRAM. The `instance_type` variable exposes the L40S-1-48G for budget runs at 4B. QLoRA on one H100 covers the full range up to 14B. Multi-GPU is not necessary.

## Method

### CPT pass

QLoRA continued pretraining on the redistributable-clean corpus. 1–2 epochs, low learning rate. General-domain replay data is mixed in to prevent catastrophic forgetting.

### SFT pass

Supervised fine-tuning from the CPT checkpoint, on synthetic agentic traces: `pf.conf` debug, `pkg_add` workflows, `sysctl` adjustment, `rcctl` service management.

### Trace generation

`ttx-synth` drives a **Qwen3-32B teacher**, served by vLLM on the same H100. At generation time, tool calls are constrained to the JSON schemas of the harness. A judge filter removes incorrect and unsafe traces before they enter the training set. Traces contain no thinking blocks. Traces target 8K tokens or less, to match the inference context budget.

### Execution

Training runs in the published Axolotl CUDA Docker image on the instance. The Scaleway GPU OS image supplies the NVIDIA drivers, Docker, and the NVIDIA container toolkit. All Axolotl YAML configurations live in `packages/ttx-train/configs/`, under version control. A run is `just train cpt` or `just train sft` against a provisioned instance. Checkpoints synchronize to Object Storage after each epoch. Thus instance destruction cannot lose work.

## Budget

Order-of-magnitude estimates, for one H100-1-80G at approximately €2.73/hour:

| Item | GPU-hours | Cost per run |
|---|---|---|
| CPT pass (domain corpus, QLoRA, 1–2 epochs) | 10–20 | €28–55 |
| SFT pass (tens of thousands of traces) | 5–10 | €14–28 |
| Trace generation campaign (Qwen3-32B teacher) | 5–10 | €14–28 |

For evaluation and iteration, budget 2–3 times the clean-run cost, for sweeps and restarts.

The full TTX 1 program (CPT + SFT + several iterations) costs approximately **€200–500** of GPU time. Each promoted variant adds approximately €50–150. Variants are SFT-dominated, because they share the CPT checkpoint ([variants](variants.md)).

Local development iteration is almost free: llama.cpp with Metal on Apple Silicon.
