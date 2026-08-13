# Risks

<a id="rsk-hall"></a>

## Hallucination on destructive commands (highest risk)

A 4B model can give a wrong `pfctl`, `pkg_delete`, or `sysctl` command, with confidence.
Mitigations: mandatory dry-run and confirmation gates, per-command doas rules,
pledge/unveil, and the safety red team ([harness](harness.md),
[evaluation](evaluation.md)). Unattended execution of destructive actions is not
possible — by design, not by policy.

<a id="rsk-inject"></a>

## Prompt injection through tool output

A sysadmin agent feeds logs, configuration files, and `dmesg` output back into the model
context as tool results.
An attacker can influence that text, and an injected instruction can steer the next tool
call. Mitigations: the fixed tool table bounds what a steered model can request; the
parent applies every gate, whatever the model claims; a mutation needs a dry run and a
human confirmation ([harness](harness.md)). No surveyed harness fences tool output
toward the model, so no proven pattern exists
([research](../docs/research/harness-loops/index.md)). The residual risk stands.
The safety red team must include injected-observation scenarios
([evaluation](evaluation.md)).

<a id="rsk-stale"></a>

## Corpus staleness versus `-current`

OpenBSD moves fast. A model trained on a snapshot drifts from `-current`. Mitigations:
periodic retraining on fresh mirrors, and local RAG over live man pages and the FAQ for
facts that change often.

<a id="rsk-eval"></a>

## Evaluation difficulty

Automatic grades for sysadmin agentic tasks are hard.
The qemu VM suite is real engineering work and a project dependency, not an
afterthought. It has its own place in the [roadmap](roadmap.md).

<a id="rsk-cpt"></a>

## CPT can add too little knowledge

CPT must carry the primary knowledge of the model (D4), and two effects work against
that. A model learns a fact only from many diverse statements of the fact, and low-rank
adapters learn less than a full fine-tune.
The first mitigation is in the method: the synthetic augmentation multiplies the
statements of each fact ([corpus](corpus.md#synthetic-augmentation)), and the grounded
QA slice trains recall in the answer format of the agent.
The [baseline grid](evaluation.md#baselines-and-ablations) measures the CPT delta
directly, on perplexity and on the OpenBSD QA set, and the retrieval baseline bounds the
value of training. If the delta is small, the recorded escalations are: a larger
augmentation multiple, a higher adapter rank, or a full-parameter CPT run.
Each escalation fits one H100 at the 4B size.
A human reviews the method before the SFT campaign starts ([roadmap](roadmap.md)).

<a id="rsk-synth"></a>

## Synthetic data quality

Naive synthetic agentic traces have high malformed-tool-call rates.
Mitigations: schema-constrained generation against the real tool schemas of the harness,
a strong teacher (Qwen3-32B), and aggressive judge filters.
The tool-call validity evaluation measures the risk that remains.

The synthetic augmentation adds a second failure mode: the teacher can write a wrong
fact into the CPT data.
Mitigations: the source chunk grounds each generation, and a judge filter drops each
record that contradicts its source or adds a fact
([training](training.md#augmentation-generation)). The OpenBSD QA suite and the
hallucinated-flag rate measure the risk that remains.

<a id="rsk-lanes"></a>

## Licensing lane discipline

Author-copyrighted material (mailing lists, undeadly.org) must stay in the eval/RAG
lane. Mitigation is mechanical: license tags are applied at extraction, and a machine
check runs before each training manifest is built ([corpus](corpus.md)).

<a id="rsk-price"></a>

## Price and availability drift

Scaleway prices and GPU stock change, by region and over time.
Confirm the console before each campaign.
Exposure is bounded by structure: per-minute billing and the create/destroy lifecycle.
An idle GPU can cost money only while `just infra-status` shows that it exists.
The idle watchdog destroys a train stack with no training in flight
([infrastructure](infrastructure.md)).

<a id="rsk-blast"></a>

## Autonomous-operation blast radius

A development agent or a CI workflow with cloud credentials can leave instances in
operation, damage infrastructure, or land a bad change.
Mitigation is structural, not trust:

- Per-capability credential scopes; IAM administration, project deletion, and the
  signify key are withheld.
- The monthly cap, the billing alerts, the pre-apply consumption check, and the idle
  watchdog ([infrastructure](infrastructure.md)).
- PR-only merges, with human review.
- Object Storage as the only durable layer, so `tofu destroy` is always safe.
- One CI concurrency group serializes each apply, with full logs.
- The same audit trail humans leave: git history, CI logs, OpenTofu state.

See [autonomous development](agents.md).
