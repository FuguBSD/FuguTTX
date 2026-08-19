# Overview

## Product

FuguTTX makes **TTX 1**: a small language model, fine-tuned on OpenBSD knowledge.
TTX 1 operates locally and offline on OpenBSD machines.
The model and the [harness](harness.md) together make the TTX agent.

The first release is TTX 1, the general OpenBSD sysadmin model.
Specialist variants are candidates, not commitments.
Evaluation evidence promotes a candidate to a release ([variants](variants.md)).

## Goals

- The TTX agent operates locally on OpenBSD, with 16 GB RAM or less, on the CPU only, in
  an open-source harness.
- The TTX agent does routine tasks: system configuration, maintenance, ports and package
  installation, `pf` debug and configuration, `sysctl` adjustment, and similar tasks.
- All components have permissive licenses: the weights, the harness, and, where
  possible, the data. This agrees with the ISC/BSD ethos of OpenBSD.
- The pipeline is reproducible end to end.
  Each pipeline stage runs from one `make` target.
  OpenTofu declares each cloud resource.
- The pipeline operates continuously from CI, in platform-enforced guardrails
  ([infrastructure](infrastructure.md)).

## Non-goals

- No GPU inference on OpenBSD. CUDA and ROCm are not available on OpenBSD.
- The TTX agent is not a general chatbot.
  The scope is OpenBSD sysadmin and development tasks.
- The TTX agent must not execute destructive commands without a dry run and an explicit
  confirmation.
- Python must not ship to the production OpenBSD target.
- No cloud resources made by hand.
  If a resource is not in OpenTofu, it must not exist.

## Terminology

“Agent” has many meanings.
This specification uses five terms.
Do not replace one term with an other.

| Term | Meaning |
| --- | --- |
| **TTX model** | The fine-tuned weights (TTX 1, a Qwen3-4B derivative), distributed as GGUF files. A model only proposes text and tool calls. A model executes nothing. |
| **Harness** (`ttxd` and `ttx`) | The Perl programs that operate the tool loop and apply each safety gate. The daemon `ttxd` executes commands as the `_ttx` user. The client `ttx` is the operator interface. Only the harness touches the system. See [harness](harness.md). |
| **TTX agent** | The model and the harness together on an OpenBSD machine. This is the product. “Agentic” always refers to the behavior of this system. |
| **Teacher/judge model** | Qwen3-32B, served by vLLM on the training instance. It writes the corpus augmentation and generates synthetic traces (teacher), and it grades evaluations (judge). It does not ship, does not execute tools, and does not touch a system. |
| **Development agents** | Claude agents that build and maintain this repository. They are part of the process, not the product. They do not appear on the OpenBSD target. See [autonomous development](agents.md). |
