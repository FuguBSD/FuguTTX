# Decisions

These eight decisions control all plans.
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

OpenBSD has no CUDA and no ROCm.
Thus inference is CPU only.
The port is maintained and builds on twelve architectures.
A 4B model at Q4_K_M operates well in 16 GB RAM. Details: [inference](inference.md).

## D3 — Training: Axolotl QLoRA on a Scaleway H100, fully as code

OpenTofu declares each cloud resource.
The GPU instance exists only for the duration of a training session.
Object Storage is the only durable layer.
QLoRA runs complete in hours.
Per-minute billing and routine `tofu destroy` keep the costs low.
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
Details: [corpus](corpus.md).

## D7 — Languages and tools are fixed

Python for all model-side work.
Perl for the harness, with base modules only.
OpenTofu for infrastructure.
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
