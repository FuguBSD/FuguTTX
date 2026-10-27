# Infrastructure

<a id="iac-code"></a>

The synced instructions in [infra/CLAUDE.md](../infra/CLAUDE.md) hold the shared
rules: naming, layout, tags, state, credentials, spend guardrails, and teardown.
Two documents state what is specific to FuguTTX: this document and
[infrastructure stacks](infrastructure-stacks.md). They state the buckets, the
development host, the training instance, the guest image, and the human
prerequisites. The project code is `ttx`, and FuguTTX has its own Scaleway
Project in the shared Organization.

Do not make resources in the console. Seven exceptions exist. "Resources outside
OpenTofu" lists them. Each price in the two documents carries the date it was
read. Scaleway revised prices on 2026-06-01. Do not plan a campaign against a
price in the two documents.

`fr-par-2` carries `H100-1-80G`, `L40S-1-48G`, every Elastic Metal range, and
every fallback offer of the two documents. Every `H100-SXM` shape is in
`fr-par-2` only.

<a id="iac-metal"></a>

## Bare metal rule

A workload runs on an Elastic Metal server, not on a virtual instance, when it
needs hardware virtualization. The agentic evaluation suite needs qemu with KVM
for the OpenBSD guests. Scaleway documents nested virtualization nowhere, so a
virtual instance is not a supported foundation for that suite. An Elastic Metal
server carries no hypervisor, so KVM needs no extra setting.

One test can change the host type ([decisions](DECISIONS.md), D9). Before the
first `infra/dev` apply, run one virtual instance for one hour: check
`/dev/kvm`, and boot one OpenBSD guest under qemu. A matched virtual instance
costs less than the metal offer. `GP1-M`, with 16 vCPU and 64 GiB, was EUR
279.97 per month, read 2026-06-23, against EUR 400.04. If both checks pass, the
virtual instance becomes the development host. Record the result in the
bootstrap runbook.

- **IAC-METAL-1** — The KVM test of this unit uses the `fuguvm` tool:
  `fuguvm up`, then `fuguvm ssh "uname -m"`, then `fuguvm down`. The quotes are
  necessary, because the option parser of the tool reads a bare `-m` as an
  unknown option. The test passes when the command prints `amd64` and returns
  exit code 0, and when the tool reports the `kvm` accelerator. The bootstrap
  runbook records the reported accelerator.

Native CPU speed on this host is a convenience, not a requirement. A published
performance number comes only from the target hardware
([evaluation](evaluation.md)). Do not select an offer on a performance argument.

Scaleway provisions a virtual instance and an Elastic Metal server with
OpenTofu. Both boot Linux from the Scaleway catalogue. Neither offers an OpenBSD
image ([OpenBSD hosts](#openbsd-hosts)). Elastic Metal bills per hour.

<a id="iac-hosts"></a>

## OpenBSD hosts

Scaleway offers no OpenBSD image. The Instance catalogue holds Linux and Windows
Server. The Elastic Metal OS list holds Linux and Windows Server. An OpenBSD
host on Scaleway therefore needs a project-built image, and Scaleway gives no
support for a custom image.

Two routes exist for a project-built image.

| Host type        | Method                                                          | Declarable in OpenTofu |
| ---------------- | --------------------------------------------------------------- | ---------------------- |
| Virtual Instance | Import a qcow2 from Object Storage as a snapshot, then an image | Yes                    |
| Elastic Metal    | Boot rescue mode, write a raw image with `dd`, reboot           | No                     |

Prefer a virtual Instance. An Instance has a serial console; Elastic Metal has
none. An Elastic Metal server needs `install_config_afterward = true`, because
the OS list holds no OpenBSD identifier. Do not plan an interactive install. The
KVM-over-IP console is a paid option, and it is not available on each offer. It
expires after 48 hours, and a browser must drive it.

A project-built image must meet each requirement.

| Requirement                                                        | Reason                                               |
| ------------------------------------------------------------------ | ---------------------------------------------------- |
| UEFI boot, with a loader at `\EFI\Boot\bootx64.efi`                | Scaleway rejects legacy BIOS                         |
| A full disk image, not an ISO and not a root file system           | The import accepts one form                          |
| A root device set by DUID                                          | The disk bus differs between a guest and an Instance |
| An `rc.local` that reads `http://169.254.42.42/conf` with `ftp(1)` | OpenBSD base has no cloud-init                       |

No Scaleway offer gives a native arm64 OpenBSD host. Each Elastic Metal offer is
x64, except one Labs offer, which is riscv. Apple silicon accepts macOS and
Asahi Linux only, and Scaleway refuses a change between OS families. The arm64
benchmark host must be project hardware ([inference](inference.md)).

The agentic suite on `infra/dev` therefore grades OpenBSD/amd64 guests. An
arm64-only harness fault escapes the suite.

No current suite requires a native OpenBSD host on Scaleway. Do not add the host
before the suite exists ([evaluation](evaluation.md)).

<a id="iac-dura"></a>

## Durability

Object Storage is the only durable layer. The corpus synchronizes down at boot.
Checkpoints synchronize up after each epoch ([training](training.md)). Release
artifacts and scorecards land in the artifacts bucket.

`tofu destroy` of `infra/train` and `infra/dev` cannot lose durable data. Three
limits apply, and the runbook must state each one:

- A destroy loses up to one epoch of training, because a checkpoint syncs after
  an epoch, not continuously.
- A destroy during an upload leaves an incomplete multipart upload. Scaleway
  bills it. The lifecycle rule of the persistent stack removes it after one day.
- A destroy of `infra/persistent` deletes the buckets and surrenders their
  names. A bucket name is globally unique and first-come. Do not destroy that
  stack routinely.

The development host follows the same rule: everything on it rebuilds from git
and from Object Storage. Elastic Metal accepts no Block Storage volume, so the
platform enforces the rule.

<a id="iac-except"></a>

## Resources outside OpenTofu

Seven resources exist outside OpenTofu. Each one is a documented exception to
the rule at the top of this document. The bootstrap runbook records each one.

| Resource                                | Reason                                     | Who                        |
| --------------------------------------- | ------------------------------------------ | -------------------------- |
| The Organization and the Project        | IAM scopes to them                         | A human, once              |
| The state bucket                        | It holds the state of every stack          | A human, once              |
| The lifecycle rule of the state bucket  | `scw` has no lifecycle argument            | A human, with an S3 client |
| The quota grants                        | Scaleway sets a quota through Support only | A human, per offer         |
| The pipeline key and the operator key   | A managed key writes its secret to state   | A human, per rotation      |
| The train API key                       | A managed key writes its secret to state   | CI, per campaign           |
| An OpenBSD OS install on a metal server | No API path exists                         | A human, per install       |

<a id="iac-prereq"></a>

## Prerequisites

These human acts precede the first apply. No credential replaces them.

| Prerequisite                                                    | Why                                                        |
| --------------------------------------------------------------- | ---------------------------------------------------------- |
| Scaleway identity validation                                    | Each Beryllium and Iridium offer needs it                  |
| A quota grant for `H100-1-80G`                                  | Scaleway grants none by default                            |
| A quota of at least 1 for the dev offer, per zone               | An apply fails without it                                  |
| The Organization security settings                              | MFA and the maximum credential duration                    |
| The KVM test on one virtual instance                            | It selects the `infra/dev` host type                       |
| A live price read                                               | The GPU and storage prices are unverified after 2026-06-01 |
| The GPU fallback analysis, with `scw instance server-type list` | The datasheet is not a complete offer list                 |
| The marketplace label of the GPU OS image                       | The train stack resolves the image by label                |

<a id="iac-spend"></a>

## Spend guardrails

The guardrail design is in [infra/CLAUDE.md](../infra/CLAUDE.md). The FuguTTX
values:

- **Quotas.** Ask Scaleway Support to set a quota of 1 for `H100-1-80G`, 1 for
  `L40S-1-48G`, and 1 for the dev offer, in `fr-par-2`.
- **The budget.** The initial budget is EUR 1,500 per month
  ([training](training.md)), with alerts at 50, 75, and 100 percent.

<a id="iac-tasks"></a>

## Task runner

The shared `infra-*` targets are in [infra/CLAUDE.md](../infra/CLAUDE.md).
FuguTTX adds:

```
make dev-rebuild-check          # the reinstall gates
make dev-reinstall              # reinstall the development host in place
make image-build                # autoinstall OpenBSD under qemu; emit a qcow2
make image-publish              # tofu apply image
make corpus-sync                # move the corpus between the host and Object Storage
make train-cpt                  # run the Axolotl CPT config on the instance
make train-sft                  # run the SFT config
make eval-sweep                 # run an evaluation sweep
```

The runbook must state how a target reaches the GPU instance. `make train-cpt`
runs on the instance, and the transport is part of the deterministic entry point
that D8 requires.
