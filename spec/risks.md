# Risks

## Hallucination on destructive commands (highest risk)

A 4B model can give a wrong `pfctl`, `pkg_delete`, or `sysctl` command, with confidence. Mitigations: mandatory dry-run and confirmation gates, per-command doas rules, pledge/unveil, and the safety red team ([harness](harness.md), [evaluation](evaluation.md)). Unattended execution of destructive actions is not possible — by design, not by policy.

## Corpus staleness versus `-current`

OpenBSD moves fast. A model trained on a snapshot drifts from `-current`. Mitigations: periodic retraining on fresh mirrors, and local RAG over live man pages and the FAQ for facts that change often.

## Evaluation difficulty

Automatic grades for sysadmin agentic tasks are hard. The qemu VM suite is real engineering work and a project dependency, not an afterthought. It has its own place in the [roadmap](roadmap.md).

## Synthetic data quality

Naive synthetic agentic traces have high malformed-tool-call rates. Mitigations: schema-constrained generation against the real tool schemas of the harness, a strong teacher (Qwen3-32B), and aggressive judge filters. The tool-call validity evaluation measures the risk that remains.

## Licensing lane discipline

Author-copyrighted material (mailing lists, undeadly.org) must stay in the eval/RAG lane. Mitigation is mechanical: license tags are applied at extraction, and a machine check runs before each training manifest is built ([corpus](corpus.md)).

## Price and availability drift

Scaleway prices and GPU stock change, by region and over time. Confirm the console before each campaign. Exposure is bounded by structure: per-minute billing and the create/destroy lifecycle. An idle GPU can cost money only while `just infra-status` shows that it exists.

## Development-agent blast radius

A development agent with cloud credentials can leave instances in operation, damage infrastructure, or land a bad change. Mitigation is structural, not trust:

- Per-capability credential scopes; IAM administration and the signify key are withheld.
- Spend caps and billing alerts.
- PR-only merges, with human review.
- Object Storage as the only durable layer, so `tofu destroy` is always safe.
- The same audit trail humans leave: git history, CI logs, OpenTofu state.

See [autonomous development](agents.md).
