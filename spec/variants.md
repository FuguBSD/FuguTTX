# Variants

TTX releases follow **user personas, not data slices**.

<a id="var-persona"></a>

## Personas

- **Operator** (TTX 1): the sysadmin who configures, maintains, and debugs an OpenBSD
  system.
- **Contributor** (candidate variants): the developer who writes ports and patches.

The boundary is sharp.
To *use* packages (`pkg_add`, `pkg_delete`, `pkg_info`) is operator work.
It stays in TTX 1. To *make and update* ports is contributor work.
It goes in a variant.

<a id="var-overlay"></a>

## Overlays, not forks

Each variant starts from the CPT checkpoint of TTX 1. The clean corpus contains the base
source tree, the ports tree, and their commit logs.
Thus the domain knowledge is shared: the CPT checkpoint carries it, from the clean
corpus and its synthetic augmentation (D4). The SFT mix is what makes a variant
different. The corpus components that seed each trace mix are specified per variant
([corpus](corpus.md#corpus-use-per-variant)). Each variant is an Axolotl overlay in
`packages/ttx-train/configs/`. This keeps one base model, one CPT run, and one validated
inference envelope for the full family.

A move to a different base model is an escalation, not a default.
Two conditions must hold:

1. The overlay clearly fails the evaluation bar of the variant.
2. The replacement base satisfies the [selection criteria](model.md) for the base model.

Qwen2.5-Coder-7B (Apache 2.0, pretrained on 92 programming languages, C and Perl
included) is the strongest known candidate for a code fork.
Its 3B sibling has the restrictive Qwen-Research license and is excluded.

<a id="var-promote"></a>

## Promotion rule

A variant is a candidate until evaluation earns it a release.
All three conditions must hold, measured against versioned evaluation suites
([evaluation](evaluation.md)):

1. The persona has its own evaluation suite, built and maintained like each other
   evaluation asset.
2. Measurements show that TTX 1 fails that suite.
3. Measurements show that the variant passes that suite, with no regression on the
   general suite.

If a candidate fails condition 2, the generalist covers the persona and no variant
ships. That result is a success, not a failure.

<a id="var-cand"></a>

## Candidates

| Candidate | Persona and scope | Evaluation story |
| --- | --- | --- |
| **TTX 1 Port** | Ports-tree maintenance: Makefiles, `bsd.port.mk`, PLIST discipline, port updates to new upstream releases. | Strongest candidate. A port builds, or it does not. `portcheck` and `make port-lib-depends-check` are machine-checkable. “Update port X to upstream release Y” grades end to end in a qemu VM. |
| **TTX 1 Code** | OpenBSD-flavored development: patches against the ports and src trees, Perl, shell, `rc.d` scripts. | Weakest candidate. No known benchmark exists for OpenBSD src work. The suite must be built: does the patch apply, compile, and pass regress? Kernel and libc patch generation is out of scope for this size class. |

A port evaluation builds the port in a disposable guest of the agentic suite
([EVL-AGENTIC](evaluation.md#evl-agentic)).

The two candidates overlap where code work touches the ports tree.
If their evaluation suites show large overlap, merge them into one contributor variant.
Do not ship two models that a user must select between.
On a 16 GB machine, each added GGUF file is real friction.

<a id="var-names"></a>

## Names

Variants get the release version.
TTX 1 Port is the Port overlay of TTX 1. A retrained family ships together: TTX 2, TTX 2
Port, and so on.
