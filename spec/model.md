# Base Model

TTX 1 trains from **Qwen3-4B**.

<a id="mdl-crit"></a>

## Selection criteria

The base model must have all of these properties:

- A permissive license (Apache 2.0 or equivalent).
- CPU-only operation in 16 GB RAM or less, at Q4_K_M quantization.
- Credible tool-call ability.
- Good C and Perl code ability.
- First-class support in Axolotl and llama.cpp.

<a id="mdl-why"></a>

## Why Qwen3-4B

- **License:** Apache 2.0 for the full dense family (0.6B, 1.7B, 4B, 8B, 14B, 32B). This
  is the most important criterion.
- **Capability at size:** Qwen3-4B is equal to much larger prior-generation models.
  The Qwen3 line has explicit agentic and tool-call training.
- **Context:** the dense models give 32K context at 0.6B–4B, and 128K at 8B and above.
  This is sufficient for sysadmin tasks with retrieved man-page context.
- **Ecosystem:** first-class support in Axolotl, HF TRL, and llama.cpp.

<a id="mdl-pin"></a>

## Revision pin and re-survey

“Qwen3-4B” names a family line, and the line has revisions.
The 2507 refresh split the hybrid model into two revisions: Qwen3-4B-Instruct-2507 and
Qwen3-4B-Thinking-2507, both Apache 2.0. The Instruct revision is natively non-thinking,
it raises the context length, and it reports stronger agentic and tool-call scores than
the original hybrid in non-thinking mode.
That is exactly the TTX 1 configuration, so **Qwen3-4B-Instruct-2507 is the leading
candidate revision**.

The project re-surveys the Qwen line and pins the exact revision before any training
spend ([roadmap](roadmap.md)). The training configuration records the revision name and
the weight hash. Model facts in this document show the state at the time of publication.
Confirm them at the re-survey.

<a id="mdl-excl"></a>

## Excluded models

- **Llama 3.x:** a custom license with a 700M monthly-active-user clause, plus name and
  derivative restrictions.
- **Gemma 3:** a Prohibited Use Policy, plus flow-down redistribution obligations.

These licenses are not OSI-approved.
They do not agree with the permissive-only culture of OpenBSD.

<a id="mdl-esc"></a>

## Escalation rule

TTX 1 can fail the [release bars](evaluation.md#release-bars) after reasonable iteration
on data and hyperparameters.
If it does, change the base to **Qwen3-8B**. Qwen3-8B has the same license and 128K
context. Its CPU speed is approximately half of the 4B speed.
The pipeline is size-agnostic.
Only the configurations change.

<a id="mdl-think"></a>

## Thinking mode

TTX 1 runs **without** thinking.
At CPU token rates, long reasoning chains make interactive latency too high.
SFT traces contain no thinking blocks.
The harness requests non-thinking completions.
A hybrid base revision fights this configuration, because its non-thinking mode is the
weaker of its two modes.
A natively non-thinking revision removes that mismatch (see
[Revision pin and re-survey](#revision-pin-and-re-survey)).

<a id="mdl-fall"></a>

## Fallback models

IBM Granite 3.x and SmolLM3-3B (both Apache 2.0) are the named fallbacks.
Use them if the Qwen line becomes unavailable or unsuitable.
SmolLM3 has fully open weights, data, and recipe.
It is applicable to a “fully open” TTX variant.

<a id="mdl-vbase"></a>

## Variant bases

Specialist variants use this base and its CPT checkpoint by default.
The escalation policy for a variant is in [variants](variants.md).
