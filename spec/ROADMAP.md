# Roadmap

Work proceeds in vertical slices, between fixed gates.
A slice is the smallest unit of work that ends in a measurement.
This document gives the method: the slice rule, the slice kinds, the thinning axes, the
rails, the shared artifacts, the gates, the order rule, and the cadence.
The plan contract is in the [index](index.md).
Decision [D10](decisions.md#d10) anchors the method.

## The slice rule

Each slice must end in a measurement on a real target:

- a scorecard row from an evaluation suite ([evaluation](evaluation.md)),
- a benchmark number against a budget ([inference](inference.md#latency-budget)), or
- a scenario set that passes in an OpenBSD guest.

A slice must not end at an unmeasured component.
A slice is one plan in `plans/`. A slice can span documents, and the plan cites each
unit that it touches.

## Slice kinds

Two slice kinds exist, and a plan names its kind.

### Capability slice

A capability slice adds behavior to the software: the harness, the data pipeline, the
evaluation suites, or the infrastructure.
The plan states the units that it implements, the units that it implements in part, and
the units that it defers.
The plan states the measurement that ends the slice.
Tests and scenarios verify a capability slice.

### Experiment slice

An experiment slice changes the model or its data: an augmentation campaign, a CPT run,
an SFT run, or a quantization.
The plan states a hypothesis: the metric that the slice must move, and the amount.
The plan states the grid rows that the measurement compares against
([evaluation](evaluation.md#baselines-and-ablations)). The plan states a cost cap in
euros, inside the monthly budget ([TRN-BUDGET](training.md#trn-budget)). A grid delta
verifies an experiment slice.

## Thinning axes

A slice is thin on one or more named axes.
The plan names each axis.

- **Feature.** The slice implements a subset of the units and the rules.
  The plan defers the rest.
- **Scale.** The slice runs every pipeline stage on a small input: a corpus sample, few
  training steps, a small evaluation subset.
  The first slice through a new pipeline must be scale-thin.
  It proves the seams before the spend.
- **Fidelity.** The slice measures on a substitute target: an amd64 qemu guest for the
  arm64 hardware, or a smoke subset for a full suite.

A thin measurement does not satisfy a gate that requires full scale or full fidelity.

## Rails

A rail is an invariant.
A slice must not thin a rail.
These are the rails:

- The license lanes (D6, [COR-LANES](corpus.md#cor-lanes)).
- The credential scopes (D9, [IAC-CRED](infrastructure.md#iac-cred)).
- The spend guardrails (D9, [IAC-SPEND](infrastructure.md#iac-spend)).
- The dry-run and confirmation gates, in every loop that a model drives
  ([HRN-SAFE-DRYRUN](harness.md#hrn-safe-dryrun)).
- The pre-registration of the release bars ([EVL-BARS](evaluation.md#evl-bars)).

Build a rail just in time: in the first slice that can violate the invariant, or before
that slice. Do not build a rail before a slice needs it.

## Shared artifacts

The system prompt, the tool metadata table and its JSON schemas, the error templates,
the re-prompt texts, and the scorecard format are the shared artifacts.
The shared artifacts are the durable contracts between slices.
A slice can discard implementation code behind an artifact.
A slice that changes a shared artifact must version the artifact, and must re-run each
measurement that reads it.
Each trace and each scorecard records the artifact version.

## Gates

A gate is a fixed checkpoint between slices.
A human decides at each gate (D8). A gate reads measurements, not plans.
The slice order between gates is free.
The gate order is fixed:

1. **The pin gate.** A re-survey pins the base-model revision
   ([MDL-PIN](model.md#mdl-pin)). Training spend must not start before the pin (D1).
2. **The retrieval gate.** The gate opens when the grid holds the B0 and B1 rows.
   If B1 reaches the [release bars](evaluation.md#release-bars), a human reviews the
   value of training before the first CPT campaign.
3. **The CPT gate.** The gate opens when the grid holds the C0 row.
   If C0 − B0 is small on the domain suites, a human reviews the CPT method before the
   first SFT campaign ([RSK-CPT](risks.md#rsk-cpt)).
4. **The release gate.** A release requires all of these: every release bar met on the
   full grid, zero red-team escapes, a green harness smoke suite on the target arm64
   hardware (D2), signed artifacts ([LIC-RELEASE](licensing.md#lic-release)), and a
   register with no `open` or `partial` unit outside [variants](variants.md).
5. **The variant gate.** The promotion rule decides each variant
   ([VAR-PROMOTE](variants.md#var-promote), D5).

## The order rule

A slice queue holds the candidate slices.
Sort the queue by risk retired per euro:

1. Name the assumption that the slice tests.
2. Estimate the damage if the assumption is false.
3. Estimate the cost of the slice, in euros and in days.
4. Take the slice with the largest damage-to-cost ratio.

Re-sort the queue after each slice, on the new measurements.

### The walking skeleton

The first slice is the walking skeleton, a capability slice:

- The base model as GGUF, without training.
- The re-survey and the revision pin, so the pin gate closes here.
- A minimal agent loop on the shared artifacts.
- One agentic scenario in one OpenBSD qemu guest.
- One scorecard, and a latency measurement against the
  [latency budget](inference.md#latency-budget).

The skeleton produces the B0 row of the grid.
Each later slice replaces one part of the skeleton and re-measures.
The retrieval slice adds the `man` tool and produces the B1 row, so the retrieval gate
opens before any training spend.

### The lead assumptions

The queue starts at the assumptions with the largest damage:

- A 4B model on the CPU drives the tool loop inside the latency budget
  ([INF-LATENCY](inference.md#inf-latency)).
- Retrieval alone does not reach the release bars ([EVL-GRID](evaluation.md#evl-grid)).
- The training pipeline holds together end to end.
  A scale-thin tracer run tests this assumption, for a few euros.
- The synthetic augmentation adds knowledge ([RSK-CPT](risks.md#rsk-cpt),
  [RSK-SYNTH](risks.md#rsk-synth)).

## Cadence

Two loops run at two speeds.

- **The inner loop** runs capability slices: CI, the qemu suite, and `make check`. It
  spends no GPU money.
  It can iterate daily.
- **The outer loop** runs experiment slices as campaigns on the train stack (D3). A
  campaign provisions the instance, runs the slice, measures, and destroys the instance.
  The monthly budget bounds the loop ([TRN-BUDGET](training.md#trn-budget)).

Batch GPU work into campaigns.
Do not hold an idle GPU between slices.
