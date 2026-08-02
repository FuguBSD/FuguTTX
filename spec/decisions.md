# Decisions

These nine decisions control all plans.
A plan must not go against a decision.
To change a decision, change this document first.

## D1 — Base model: Qwen3-4B (Apache 2.0)

Qwen3-4B is the only current model family with all of these properties: an Apache 2.0
license, strong tool-call ability, good C and Perl code ability, long context, and full
fine-tune ecosystem support.
Llama 3.x and Gemma 3 have custom licenses that are not OSI-approved.
Those licenses do not agree with the permissive-only culture of OpenBSD. Those models
are excluded. Details: [base model](model.md).

## D2 — Inference: the `misc/llama.cpp` port, CPU only

The target hardware has no usable GPU path.
OpenBSD/arm64 has no kernel driver for the Apple GPU, and no Apple Vulkan ICD. The one
Apple GPU driver that exists anywhere is Rust code in a branch that Asahi Linux rebases,
and the OpenBSD kernel has no Rust.
Token generation would also gain nothing from the GPU of a Mac mini M1, because the CPU
and the GPU share the same measured 59 to 60 GB/s of memory bandwidth.

This decision is “CPU only on the target hardware”.
It is not “OpenBSD has no GPU path”.
OpenBSD supports GPU offload on amd64 with an AMD card, through the ggml Vulkan back
end. A move to GPU inference is an escalation, and it needs a new decision.

The port is maintained and builds on twelve architectures.
A 4B model at Q4_K_M operates well in 16 GB RAM. No cloud offer gives an arm64 OpenBSD
host, so the agentic suite grades amd64 guests.
Before a release, the harness smoke suite must pass on the target arm64 hardware.
Details: [inference](inference.md), and
[OpenBSD and the Apple GPU](../docs/research/openbsd-apple-silicon-gpu.md).

## D3 — Training: Axolotl QLoRA on a Scaleway H100, fully as code

OpenTofu declares each cloud resource, with the documented exceptions
([infrastructure](infrastructure.md)). The GPU instance exists only for the duration of
a training session. A quota grant from Scaleway Support is a bootstrap prerequisite.
Scaleway grants no H100 quota by default.
Object Storage is the only durable layer.
QLoRA runs complete in hours.
On-demand billing and routine `tofu destroy` keep the costs low.
Details: [training](training.md), [infrastructure](infrastructure.md).

## D4 — Method: continued pretraining, then supervised fine-tuning

CPT on the OpenBSD corpus adds vocabulary and idioms.
SFT on synthetic agentic traces teaches tool use.
Replay data and a low learning rate prevent catastrophic forgetting.
A Qwen3-32B teacher generates the traces.
A judge filter removes bad traces before use.
Details: [training](training.md).

## D5 — Variants are personas, and evaluation promotes them

TTX 1 serves the operator (sysadmin).
Candidate variants serve the contributor.
Variants are SFT overlays on the CPT checkpoint of TTX 1, not separate bases.
A variant ships only when the generalist fails the persona evaluation suite and the
overlay passes it. A move to a different base model is an escalation, not a default.
Details: [variants](variants.md).

## D6 — The corpus has two lanes, and the lane rule is absolute

OpenBSD source (ISC/BSD), man pages (mandoc, ISC), and the FAQ/website (BSD, the `www`
repository) make the redistributable-clean corpus.
This corpus trains the model.
Mailing-list archives and undeadly.org are copyright of their authors.
That material is only for evaluation and optional local RAG. It must not enter the
training data. Its raw text must not be redistributed.
Each lane has its own bucket.
The training corpus and the eval/RAG corpus must not share a bucket.
No project bucket is public.
Details: [corpus](corpus.md).

## D7 — Languages and tools are fixed

Python for all model-side work.
Perl for the harness, with base modules only.
OpenTofu, 1.11 or later, for infrastructure.
`just` as the task runner.
Python must not ship to the OpenBSD target.
The harness must not have dependencies outside OpenBSD base.
Details: [repository](repository.md).

## D8 — Claude agents develop the project autonomously

Each pipeline stage has a deterministic entry point.
Each outcome has a machine-checkable definition of done.
Each credential has a minimal scope.
Agents plan, implement, train, and evaluate end to end.
Humans keep a short list of decisions: merges, release signatures, licensing lanes, and
spend above the budget.
Details: [autonomous development](agents.md).

## D9 — Operation is continuous, and the platform blocks what it can

A one-time bootstrap precedes continuous operation.
A human performs it: the Organization and the Project, the identity validation, the
quota grants, the state bucket, and the operator API keys.
The bootstrap runbook records each act.

After the bootstrap, the pipeline runs from CI, without an operator in the loop.
Three IAM applications split the credentials by blast radius:

- **The pipeline application** operates `infra/dev`, `infra/train`, and `infra/image`.
  Its policy excludes IAM administration and project deletion, so it cannot widen its
  own scope.
- **The operator application** applies `infra/persistent`, which declares the IAM
  objects. A human holds its key.
  In CI, only a protected manual workflow dispatch uses it.
  The same application serves recovery.
- **The train application** holds Object Storage rights only.
  Each of its keys lives for one campaign and carries an expiry.

The guardrails divide into two kinds, and the specification names the kind of each.
Per-Organization quotas and scoped IAM policies block.
The monthly budget and its alerts notify.
The pre-apply forecast check and the idle watchdog are pipeline code, and they gate.

The development host needs hardware virtualization.
Elastic Metal gives it by construction.
If a one-hour test proves `/dev/kvm` and an OpenBSD guest boot on a virtual instance,
the cheaper instance can become the host without a new decision.
The four human decisions of D8 stand.
Details: [infrastructure](infrastructure.md), [autonomous development](agents.md).
