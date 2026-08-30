# Campaign runbook

This runbook holds a map, not a design. It maps each shared stage name of the
workspace observer set to the verb of this project. It names the stages this
project omits, and it names the file that holds each answer.

Three files own the content. This runbook points at them, and it does not
restate them.

| File                          | Owns                                                         |
| ----------------------------- | ------------------------------------------------------------ |
| `train/config.env`            | The campaign pins and the shared names.                      |
| `infra/persistent/RUNBOOK.md` | The offer probe, the manual platform steps, the human steps. |
| `spec/`                       | Every design fact, the promote rule, the threshold policy.   |

## The state of this project

This project holds no campaign code today. It has no `train/config.env`, no
`infra/persistent/` stack, and no campaign workflow. The verb names below come
from the specification, and no code implements them.

So a dry run is the only test that this project can supply now. An observer that
reaches a stage below must stop, and report the stage as absent.

## The stage map

The specification names these actions: `data`, `synth`, `eval`, `quant`,
`corpus-sync`, `eval-sweep` and `image-build`. Not one FuguSTX action name
appears there, so a skill must never take a verb from FuguSTX.

| Stage      | Verb of this project              | State                        |
| ---------- | --------------------------------- | ---------------------------- |
| `infra`    | the twelve `make infra-*` targets | absent, no stack exists      |
| `corpus`   | `data`, `synth`, `corpus-sync`    | absent, specification only   |
| `train`    | the CPT pass, then the SFT pass   | absent, `spec/training.md`   |
| `evaluate` | `eval`, `eval-sweep`              | absent, `spec/evaluation.md` |
| `promote`  | —                                 | omitted, see below           |
| `teardown` | the twelve `make infra-*` targets | absent, no stack exists      |

The actions `quant` and `image-build` belong to no shared stage. Dispatch them
through the `corpus` skill, and state in the report that the stage name does not
fit.

## What this project omits

- **The promote step.** This project has no promote action. Its variant rule
  `VAR-PROMOTE` sits under decision D5: a variant ships only when the generalist
  fails the persona evaluation suite and the overlay passes it. That is a
  release gate, not a campaign stage.

## The answers

- **The variants and the promotion gate.** Decision D5 of `spec/DECISIONS.md`,
  and `spec/variants.md`.
- **The model and the passes.** `spec/model.md` and `spec/training.md`.
- **The threshold policy.** `spec/evaluation.md`. This project pre-registers its
  bars, so read them before a run, never after it.
- **The agents.** `spec/agents.md`.

## The rules that the observer set adds

- Export this project's `.env` before any command that reaches Scaleway. The
  `env` block of the workspace checkout shadows every project key (Workspace
  D-05).
- State the clone and the git HEAD that each step read.
- This project receives the findings of the two pilots. A finding lands in
  `docs/research/`, and a contradiction becomes a specification change here.
