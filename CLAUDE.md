# CLAUDE.md

FuguTTX is TTX 1: a small language model and agent for OpenBSD system administration. TTX 1 is a fine-tune of Qwen3-4B. It runs on the CPU, on OpenBSD, in 16 GB of RAM or less, through llama.cpp. The `ttx` harness — Perl 5, base modules only — operates the model in the boundaries of pledge, unveil, doas rules, and dry-run gates.

The specification in [`spec/`](spec/index.md) governs all work. Read the [decisions](spec/decisions.md) before you make a plan. A plan must not go against a decision.

## Critical: writing standard

All output and all artifacts must comply with ASD-STE100 Simplified Technical English. This rule applies to documentation, specifications, runbooks, dataset cards, model cards, commit messages, and pull requests. Write short sentences, in the active voice, with one instruction per sentence. Use "must" for a requirement, "must not" for a prohibition, and "can" for a capability.
