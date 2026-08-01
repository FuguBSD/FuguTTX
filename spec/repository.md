# Repository

This is a Python + Perl + HCL monorepo.
uv workspaces manage the Python packages: one lockfile, a shared virtualenv, and
per-package `uv sync`. `just` is the polyglot task runner for all of it.

## Tools

One language per concern.
The boundary is where the code runs.

| Concern | Tool | Reason |
| --- | --- | --- |
| Model-side work (data, synthesis, training, evaluation, quantization) | Python 3.12, uv workspace, one lockfile | The ML ecosystem is Python. uv gives one lockfile and per-package installation, with no environment drift. |
| Training framework | Axolotl (QLoRA), YAML configurations in git | One framework covers CPT and SFT. Version-controlled YAML makes each run reproducible. |
| GPU runtime | Upstream Docker images (Axolotl for training, vLLM for the teacher) on the Scaleway GPU OS image | No custom environments on ephemeral instances. The uv workspace runs on the operator machine and in CI, not on the GPU. |
| Harness | Perl 5 from OpenBSD base, base modules only | Perl, `OpenBSD::Pledge(3p)`, and `OpenBSD::Unveil(3p)` ship in base. The OpenBSD package tools follow the same discipline. |
| Infrastructure as code | OpenTofu, with the Scaleway provider | Open-source IaC agrees with the project license ethos. It makes the ephemeral GPU lifecycle safe and repeatable. |
| Task runner | `just` | One polyglot entry point for Python, Perl, and OpenTofu. |
| Format and lint | Ruff for Python, flowmark for Markdown | One formatter per language. flowmark makes semantic line breaks: one sentence per line. This agrees with the ASD-STE100 writing standard and keeps diffs small. |
| Inference runtime | llama.cpp everywhere | The same runtime serves development (Metal on Apple Silicon) and production (OpenBSD CPU). What is validated is what ships. |
| Teacher/judge model | Qwen3-32B (Apache 2.0), served by vLLM on the H100 | Clean license provenance for synthetic data. One deployment generates traces and grades evaluations. |
| CI | GitHub Actions | The repository and the corpus mirrors are on GitHub. CI is lint, test, and validation only, with no cloud credentials. |

## Layout

```
fuguttx/
├── justfile                     # top-level recipes: data, synth, train, eval, quant, infra, harness
├── CLAUDE.md                    # development-agent context: conventions, entry points, safety rules
├── pyproject.toml               # uv workspace root (virtual root, no application code)
├── uv.lock                      # single lockfile
├── .python-version              # 3.12
├── spec/                        # this specification
├── packages/                    # Python workspace members — all model-side work
│   ├── ttx-data/                # corpus fetch, extraction, cleanup
│   │   ├── fetch/               #   git-mirror synchronization (src/ports/www)
│   │   ├── extract/             #   mandoc render, HTML→text, code walk
│   │   └── clean/               #   dedup, license tags, chunks
│   ├── ttx-synth/               # synthetic agentic trace generation (vLLM teacher client)
│   ├── ttx-train/               # training entry points
│   │   └── configs/             #   Axolotl YAML: cpt.yaml, sft.yaml, per-variant overlays
│   ├── ttx-eval/                # QA sets, agentic VM suite, judge client, scorecards
│   └── ttx-quant/               # GGUF conversion + quantization sweep + signify manifest
├── harness/                     # the on-OpenBSD harness — Perl, base modules only
│   ├── bin/ttx                  #   entry point
│   ├── lib/TTX/                 #   Agent.pm, LLM.pm, Tools.pm, Sandbox.pm, Audit.pm
│   ├── t/                       #   prove(1) tests
│   └── port/                    #   OpenBSD port skeleton (Makefile, PLIST, DESCR, rc.d)
├── infra/                       # OpenTofu for Scaleway (modules/, persistent/, train/)
├── datasets/                    # dataset cards + manifests (not raw data)
├── models/                      # model cards + release manifests (GGUF via object storage/HF)
├── docs/                        # corpus/licensing notes, runbooks, research notes
│   ├── runbooks/                #   bootstrap, training campaign, release
│   └── research/                #   dated research notes with sources
└── .github/workflows/           # CI
```

## Task recipes

`just data`, `just synth`, `just train cpt`, `just train sft`, `just eval`,
`just quant`, `just infra-up train`, `just infra-down train`, `just harness-test`.

The top-level `just check` runs each local lint, test, and validation step.
It must pass before each commit.
CI runs the same gate.

## CI

GitHub Actions, with no cloud credentials:

- Python packages: ruff and pytest.
- Markdown documents: `flowmark --check`.
- Harness: `perl -c`, `prove`, and the no-CPAN-dependency check.
- Infrastructure: `tofu fmt -check` and `tofu validate`.
- Training: Axolotl configuration validation.

Heavy training stays manual, on Scaleway.
