# Base Model

TTX 1 trains from **Qwen3-4B**.

## Selection criteria

The base model must have all of these properties:

- A permissive license (Apache 2.0 or equivalent).
- CPU-only operation in 16 GB RAM or less, at Q4_K_M quantization.
- Credible tool-call ability.
- Good C and Perl code ability.
- First-class support in Axolotl and llama.cpp.

## Why Qwen3-4B

- **License:** Apache 2.0 for the full dense family (0.6B, 1.7B, 4B, 8B, 14B, 32B). This is the most important criterion.
- **Capability at size:** Qwen3-4B is equal to much larger prior-generation models. The Qwen3 line has explicit agentic and tool-call training.
- **Context:** the dense models give 32K context at 0.6B–4B, and 128K at 8B and above. This is sufficient for sysadmin tasks with retrieved man-page context.
- **Ecosystem:** first-class support in Axolotl, HF TRL, and llama.cpp.

## Excluded models

- **Llama 3.x:** a custom license with a 700M monthly-active-user clause, plus name and derivative restrictions.
- **Gemma 3:** a Prohibited Use Policy, plus flow-down redistribution obligations.

These licenses are not OSI-approved. They do not agree with the permissive-only culture of OpenBSD.

## Escalation rule

TTX 1 can fail the Phase 4 agentic evaluation bar after reasonable iteration on data and hyperparameters. If it does, change the base to **Qwen3-8B**. Qwen3-8B has the same license and 128K context. Its CPU speed is approximately half of the 4B speed. The pipeline is size-agnostic. Only the configurations change.

## Thinking mode

The Qwen3 thinking mode stays **off** for TTX 1. At CPU token rates, long reasoning chains make interactive latency too high. SFT traces contain no thinking blocks. The harness requests non-thinking completions.

## Fallback models

IBM Granite 3.x and SmolLM3-3B (both Apache 2.0) are the named fallbacks. Use them if the Qwen line becomes unavailable or unsuitable. SmolLM3 has fully open weights, data, and recipe. It is applicable to a "fully open" TTX variant.

## Variant bases

Specialist variants use this base and its CPT checkpoint by default. The escalation policy for a variant is in [variants](variants.md).
