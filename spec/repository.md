# Repository

This is a Python + Perl + HCL monorepo.
uv workspaces manage the Python packages: one lockfile, a shared virtualenv, and
per-package `uv sync`. `make` is the polyglot task runner for all of it.

<a id="rep-tools"></a>

## Tools

One language per concern.
The boundary is where the code runs.

| Concern | Tool | Reason |
| --- | --- | --- |
| Model-side work (data, synthesis, training, evaluation, quantization) | Python 3.12, uv workspace, one lockfile | The ML ecosystem is Python. uv gives one lockfile and per-package installation, with no environment drift. |
| Training framework | Axolotl (QLoRA), YAML configurations in git | One framework covers CPT and SFT. Version-controlled YAML makes each run reproducible. |
| GPU runtime | Upstream Docker images (Axolotl for training, vLLM for the teacher) on the Scaleway GPU OS image | No custom environments on ephemeral instances. The uv workspace runs on the operator machine and in CI, not on the GPU. |
| Harness body | Perl 5 from OpenBSD base, base modules plus the Fugu module allow-list of [D7](decisions.md#d7), from the p5-Fugu package | Perl, `OpenBSD::Pledge(3p)`, and `OpenBSD::Unveil(3p)` ship in base. The OpenBSD package tools follow the same discipline. The Fugu library supplies the shared modules: the line editor, the sandbox, the logger, the process control, the configuration grammar, the file operations, and the command line. |
| doas target wrappers | C, against libc alone | The privileged side of doas. A small C wrapper avoids the interpreter startup surface under doas, and libc gives `pledge(2)`, `unveil(2)`, and `execv(3)`. See [D7](decisions.md) and [harness](harness.md). |
| OpenBSD guests | The `fuguvm` tool, over qemu | One tool installs and operates each guest, so the FuguBSD projects share one guest lifecycle. |
| Infrastructure as code | OpenTofu, with the Scaleway provider | Open-source IaC agrees with the project license ethos. It makes the ephemeral GPU lifecycle safe and repeatable. |
| Task runner | `make` | One polyglot entry point for Python, Perl, and OpenTofu. `make` needs no installation step. |
| External dependencies | `deps/<OS>.txt` manifests, installed by `scripts/deps` | The shared FuguBSD bootstrap script installs OS packages, CPAN modules, and prebuilt binaries the same way in every repository. FuguBSD/Tooling holds the canonical copy of the script. |
| Format and lint | Ruff for Python, flowmark for Markdown | One formatter per language. flowmark makes semantic line breaks: one sentence per line. This agrees with the ASD-STE100 writing standard and keeps diffs small. |
| Inference runtime | llama.cpp everywhere | The same runtime serves development (Metal on Apple Silicon) and production (OpenBSD CPU). What is validated is what ships. |
| Teacher/judge model | Qwen3-32B teacher (Apache 2.0), served by vLLM on the H100; a release judge from a different model family | Clean license provenance for synthetic data. The teacher writes the corpus augmentation, and it proposes and filters traces. A judge outside the Qwen family grades each release bar ([evaluation](evaluation.md)). |
| CI | GitHub Actions | The repository and the corpus mirrors are on GitHub. CI validates each push, and it operates the pipeline with the scoped pipeline credential ([infrastructure](infrastructure.md)). |

- **REP-TOOLS-1.** The repository operates each OpenBSD guest with the `fuguvm` tool,
  and it holds no qemu command line.
  A global option comes before the subcommand.
  The repository must not load an `App::FuguVM` module, because a sibling application is
  not a library.

<a id="rep-layout"></a>

## Layout

```
fuguttx/
├── Makefile                     # top-level targets: data, synth, train, eval, quant, infra, harness
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
│   ├── ttx-synth/               # corpus augmentation and agentic trace generation (vLLM teacher client)
│   ├── ttx-train/               # training entry points
│   │   └── configs/             #   Axolotl YAML: cpt.yaml, sft.yaml, per-variant overlays
│   ├── ttx-eval/                # QA sets, agentic VM suite, judge client, scorecards
│   └── ttx-quant/               # GGUF conversion + quantization sweep + signify manifest
├── harness/                     # the on-OpenBSD harness
│   ├── bin/ttx                  #   client entry point (Perl)
│   ├── sbin/ttxd                #   daemon (Perl)
│   ├── lib/TTX/                 #   Agent.pm, LLM.pm, Tools.pm, Sandbox.pm, Audit.pm
│   ├── libexec/                 #   fixed-function doas target wrappers (C, libc only)
│   ├── t/                       #   prove(1) tests
│   └── port/                    #   OpenBSD port skeleton (Makefile, PLIST, DESCR, rc.d)
├── infra/                       # OpenTofu for Scaleway (modules/, persistent/, dev/, train/, image/)
├── datasets/                    # dataset cards + manifests (not raw data)
├── models/                      # model cards + release manifests (GGUF via object storage/HF)
├── plans/                       # implementation plans, with unit citations
├── docs/                        # corpus/licensing notes, runbooks, research notes
│   ├── runbooks/                #   bootstrap, training campaign, release
│   └── research/                #   dated research notes with sources
├── deps/                        # per-OS dependency manifests (deps/<OS>.txt)
├── scripts/                     # repository checks (Python, standard library only);
│                                #   plus deps and ftp, verbatim copies from FuguBSD/Tooling
└── .github/workflows/           # CI
```

<a id="rep-recipes"></a>

## Task targets

`make data`, `make synth`, `make train-cpt`, `make train-sft`, `make eval`,
`make quant`, `make infra-up STACK=train`, `make infra-down STACK=train`,
`make harness-test`.

The top-level `make check` runs each local lint, test, and validation step.
It must pass before each commit.
CI runs the same gate.

- **REP-RECIPES-1.** The guest targets are `make vm-up`, `make vm-down`,
  `make vm-snapshot NAME=<name>`, `make vm-restore NAME=<name>` and `make vm-clean`.
  Each target runs the `fuguvm` tool.
  A target must act on the exit code.
  Exit code 11 reports an absent snapshot, and the target then installs the guest again.
  Exit code 5 reports a running guest, and exit code 7 reports a timeout.

<a id="rep-ci"></a>

## CI

GitHub Actions runs two kinds of workflows.

Validation, on each push, with no cloud credentials:

- Python packages: ruff and pytest.
- Markdown documents: `flowmark --check`, and the cross-reference check
  (`make spec-check`). The check verifies each internal link and each anchor, and it
  verifies that `spec/index.md` lists each specification document.
  A reference between the specification and the code must not rot silently.
- Harness body: `perl -c`, `prove`, taint mode, the dependency check, and the
  execution-discipline check (list-form exec, three-argument open, no backticks).
  The dependency check permits a base-module import and a module of the allow-list of
  [D7](decisions.md#d7), and it refuses each other module.
  D7 alone holds the list.
  CI installs the Fugu distribution through `scripts/deps`, so `prove` runs with the
  real modules ([harness](harness.md#hrn-repl)). The harness reaches pledge(2) and
  unveil(2) through `Fugu::Sandbox`, which restricts nothing off OpenBSD and returns
  success, so `perl -c` and `prove` run on any runner.
  The OpenBSD guests of the development host verify the enforcement.
- doas wrappers: compile with the base toolchain, and `lint`.
- Infrastructure: `tofu fmt -check` and `tofu validate`.
- Training: Axolotl configuration validation.

Operation, with the pipeline credential:

- Plan and apply of the `infra/` stacks.
- Training campaigns and evaluation sweeps, end to end.
- The idle watchdog and the scheduled rebuild of the development host.

One concurrency group serializes each operation.
The platform guardrails bound every workflow ([infrastructure](infrastructure.md),
[autonomous development](agents.md)).
