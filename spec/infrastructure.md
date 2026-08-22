# Infrastructure

<a id="iac-code"></a>

OpenTofu, with the Scaleway provider, declares each Scaleway resource. Do not
make resources in the console. Seven exceptions exist. “Resources outside
OpenTofu” lists them. Scaleway bills a GPU instance per minute of uptime.
Scaleway also documents a minimum of 60 minutes for each created resource. Plan
for the 60-minute minimum. A create/destroy cycle is therefore cheap. A cycle
shorter than one hour saves nothing. Infrastructure as code makes `destroy`
repeatable. It does not make `destroy` complete: read “Teardown”. The
infrastructure code has the ISC license, like all project tooling.

Prices change. Scaleway revised prices on 2026-06-01. Each price in this
document carries the date it was read. The pipeline must read the live price
before it creates a resource. Do not plan a campaign against a price in this
document.

<a id="iac-region"></a>

## Region and zone

One region and one zone hold everything.

| Item                    | Value                         |
| ----------------------- | ----------------------------- |
| Region                  | `fr-par`                      |
| Zone                    | `fr-par-2`                    |
| Object Storage endpoint | `https://s3.fr-par.scw.cloud` |

`fr-par-2` carries `H100-1-80G`, `L40S-1-48G`, every Elastic Metal range, and
every fallback offer of this document. Every `H100-SXM` shape is in `fr-par-2`
only. A quota applies per Organization and per Availability Zone. One zone
therefore caps the number of instances that a defective loop can create.

Each bucket must use the region `fr-par`. Do not put a bucket in a second
region. A quota, a price, and a data-transfer charge each depend on the region.

<a id="iac-pins"></a>

## Version pins

| Tool              | Constraint                       |
| ----------------- | -------------------------------- |
| OpenTofu          | `required_version = ">= 1.11.0"` |
| Scaleway provider | `version = "~> 2.80"`            |

Each stack must hold a `versions.tf` with both constraints. Each stack must
commit its `.terraform.lock.hcl`. OpenTofu 1.11 is the floor, because the
credential design uses ephemeral resources and write-only arguments.

The provider publishes `action` resources and list resources. OpenTofu supports
neither. A stack must not use them.

<a id="iac-layout"></a>

## Layout

```
infra/
├── modules/              # a module needs three or more callers
├── persistent/           # buckets, IAM, budget, alerts — applied rarely
├── dev/                  # the development host: one Elastic Metal server
├── train/                # one GPU instance — up/down around each session
└── image/                # the OpenBSD guest image — applied on an OpenBSD release
```

Each stack holds the same files:

| File                                      | Content                                            |
| ----------------------------------------- | -------------------------------------------------- |
| `versions.tf`                             | The version pins above                             |
| `backend.tf`                              | The S3 backend block, with `use_lockfile = true`   |
| `providers.tf`                            | `provider "scaleway"`, with no credential argument |
| `variables.tf`, `outputs.tf`, `locals.tf` | Inputs, outputs, and the tag maps                  |
| `.terraform.lock.hcl`                     | Committed                                          |

A stack is a root module. Create a module only when a pattern has three or more
callers. A stack must not read the state of another stack with
`terraform_remote_state`. A stack must not contain a hardcoded Scaleway UUID.
Resolve each identifier with a data source: `scaleway_account_project`,
`scaleway_baremetal_offer`, `scaleway_baremetal_os`, `scaleway_iam_ssh_key`,
`scaleway_marketplace_image`, `scaleway_instance_server_type`.

<a id="iac-tags"></a>

## Tags

The Scaleway provider has no default tags. Each stack must tag each resource it
creates. An instance takes a list of strings. A bucket takes a map. Build both
shapes from one map in `locals.tf`.

| Tag             | Example                            | Purpose                             |
| --------------- | ---------------------------------- | ----------------------------------- |
| `ttx:stack`     | `ttx:stack=train`                  | Names the owning stack              |
| `ttx:managed`   | `ttx:managed=true`                 | Marks a resource the pipeline owns  |
| `ttx:lifecycle` | `ttx:lifecycle=ephemeral`          | The watchdog reaps `ephemeral` only |
| `ttx:run-id`    | `ttx:run-id=8891fa2c`              | Ties a resource to one CI run       |
| `ttx:expires`   | `ttx:expires=2026-08-02T18:00:00Z` | The hard end of the lease, in UTC   |

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
costs less than the metal offer: `GP1-M`, with 16 vCPU and 64 GiB, was EUR
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

## Stacks

Three operational stacks, with three lifecycles, and one image stack.

<a id="iac-persist"></a>

### `infra/persistent`

The stack holds the buckets, the IAM applications and policies, the budget, and
the billing alerts. Apply this stack rarely. Review each change like all code.

Four buckets exist. A bucket name is unique across the whole Scaleway platform,
so each name carries a project suffix. The bootstrap runbook records the suffix.

| Logical name               | Lane                  | Versioning | Purpose                   |
| -------------------------- | --------------------- | ---------- | ------------------------- |
| `ttx-corpus-<suffix>`      | Redistributable-clean | On         | Training corpus           |
| `ttx-evalcorpus-<suffix>`  | Eval and RAG          | On         | Author-copyright material |
| `ttx-checkpoints-<suffix>` | Internal              | Off        | Training checkpoints      |
| `ttx-artifacts-<suffix>`   | Internal              | On         | Releases and scorecards   |

The lane rule of [corpus](corpus.md) is absolute, so the storage layer must
enforce it. The two corpus lanes must live in separate buckets. Eval and RAG
material must not enter `ttx-corpus-<suffix>`. Eval and RAG raw text must not
enter `ttx-artifacts-<suffix>`. No bucket is public. Each bucket keeps the
default private ACL. Set `force_destroy = false` on each bucket.

Versioning is off on the checkpoint bucket, because a checkpoint is large and a
run writes one after each epoch. Scaleway holds at most 1,000 versions of one
object, and it bills each version. A checkpoint key must therefore carry the run
identifier and the step number, so no key is overwritten.

A lifecycle rule must abort an incomplete multipart upload after one day.
Scaleway bills an incomplete multipart upload. A destroy during an upload
creates one.

A storage class is a property of an object, not of a bucket. An object with no
class becomes Standard Multi-AZ. A transition to Standard One Zone needs an
object age of 30 days. A transition to Glacier needs an object age of 90 days.
Do not send a checkpoint to Glacier. A Glacier restore takes up to 24 hours to
start, and it restores to Standard Multi-AZ only.

Object lock must stay off on each bucket. Object lock cannot be disabled again.

<a id="iac-dev"></a>

### `infra/dev`

The development host is one Elastic Metal server. It runs Linux with KVM. It is
the runtime for the development agents and for the evaluation sweeps
([autonomous development](agents.md)). It runs the OpenBSD guests of the agentic
suite under qemu with KVM, with scenarios in parallel. Linux is the host OS,
because Scaleway offers no OpenBSD image and because qemu has no hardware
acceleration on OpenBSD. OpenBSD is always the guest.

The offer is `EM-B430E-NVMe`, in `fr-par-2`, on the **hourly** billing plan.

| Property | Value                                                              |
| -------- | ------------------------------------------------------------------ |
| CPU      | AMD EPYC 4545P, 3.00 GHz, 16 cores, 32 threads                     |
| RAM      | 64 GiB DDR5                                                        |
| Disk     | 2 × 3.84 TB NVMe                                                   |
| OS       | Ubuntu 24.04 LTS, with cloud-init                                  |
| Price    | EUR 0.548 per hour, read 2026-06-11; EUR 400.04 per 730-hour month |

The stack must not use the monthly billing plan. The monthly plan charges a
commitment fee equal to one month of subscription, at each order. The change
from hourly to monthly is one way. The loyalty voucher that offset the fee ended
for a new subscription on 2026-04-01.

The offer choice follows the parallelism target of the agentic suite. One
scenario needs about 8 GiB and 4 threads. Four parallel scenarios fit 64 GiB.
Eight parallel scenarios need a 128 GiB offer. [Evaluation](evaluation.md) must
fix the target.

Fallback chain, in order. Each price was read on 2026-06-11 for `fr-par-2`.

| Rank | Offer              | Cores/threads | RAM     | EUR/hour |
| ---- | ------------------ | ------------- | ------- | -------- |
| 1    | EM-B430E-NVMe      | 16 / 32       | 64 GiB  | 0.548    |
| 2    | EM-B330E-NVMe      | 12 / 24       | 64 GiB  | 0.438    |
| 3    | EM-B230E-NVMe-128G | 8 / 16        | 128 GiB | 0.411    |
| 4    | EM-I120E-NVMe      | 8 / 16        | 64 GiB  | 0.370    |

Facts the runbook needs:

| Fact                    | Value                                                           |
| ----------------------- | --------------------------------------------------------------- |
| Delivery of the machine | A few minutes                                                   |
| OS installation         | Up to one hour                                                  |
| Billing starts          | At server creation                                              |
| Billing stops           | At server deletion, never at power off                          |
| Public IPv4             | One, included, static, not transferable                         |
| Block Storage           | Not compatible with Elastic Metal                               |
| SSH keys                | `ssh_key_ids` at install time. A later change needs a reinstall |
| Cloud-init              | A change needs a reboot, not a reinstall                        |
| Rescue mode             | An Ubuntu system in RAM, user `rescue`, the server SSH keys     |
| Serial console          | None. Rescue mode is the out-of-band route                      |

The stack must not set `install_config_afterward`. That flag delivers a server
with no operating system and no SSH key, and a human must then finish the
install. An attached option costs money. A Private Network option on this offer
costs EUR 0.06 per hour, read 2026-06-11, which is about EUR 43.80 per month. Do
not attach an option without a recorded reason.

The host is long-lived, and a reinstall from code must reproduce it. CI
reinstalls the host on the first day of each month, at 03:00 UTC. The cron
expression is `0 3 1 * *`. A reinstall keeps the machine, the static public
IPv4, and the hourly billing period. CI must not destroy and re-order the host
on a schedule, because an offer can be out of stock. A re-order needs two
conditions: the `stock` attribute of the offer data source reads `available`,
and a human approves a workflow dispatch.

`make dev-rebuild-check` runs the gates. A reinstall must not start unless each
gate passes.

| Gate                       | Check                                                   |
| -------------------------- | ------------------------------------------------------- |
| No training in flight      | `make infra-status` reports no live train stack         |
| No agent session in flight | No `dev-busy` object exists in the artifacts bucket     |
| No unsaved work            | `git status --porcelain` is empty in each clone         |
| The corpus is durable      | The local corpus digest equals the digest in the bucket |
| Spend is under the cap     | `make infra-cost` reports below 100 percent             |

A reinstall wipes the disk and takes up to one hour. After the reinstall, CI
must run `make check`, must boot one OpenBSD guest under KVM, and must generate
one token with llama.cpp. A failure must fail the workflow.

The host must pin an exact qemu version. A qemu upgrade must not reach the host
without the guest-boot test above. The host holds no durable state.

- **IAC-DEV-1** — The host declares one guest for each parallel scenario, in one
  `.fuguvmrc` of the `fuguvm` tool. Each guest carries its own name, and each
  guest takes its host ports automatically. The guests share one read-only image
  cache.
- **IAC-DEV-2** — Each forwarded guest port must bind to `127.0.0.1`. The host
  holds a public IPv4 address, so a guest port must not listen on a public
  interface.
- **IAC-DEV-3** — The guest architecture of the suite is amd64, and the `fuguvm`
  tool must select the KVM accelerator on this host. A guest that falls back to
  software emulation fails the target.
- **IAC-DEV-4** — The `.fuguvmrc` of this host names the pinned qemu version,
  and the tool must refuse a guest under an other version, with exit code 3. The
  directive is optional, and a guest with no directive runs no check. The image
  build of [IAC-IMAGE](#iac-image) runs on a CI runner with an other qemu
  version, so its guest carries no version directive.

The host is the largest recurring cost line of the project, so idle time is
waste. Two lifecycle rules bound it:

- The idle watchdog must report a development host with no agent session, no
  evaluation sweep, and no CI job in the last 48 hours. The watchdog reports the
  host. It must not destroy the host.
- A metal host stays long-lived for one reason only: a re-order can fail on
  stock. If the KVM test passes and a virtual instance becomes the host
  ([decisions](DECISIONS.md), D9), the host becomes ephemeral, like the train
  stack: `make infra-up STACK=dev` before a work session, and
  `make infra-down STACK=dev` after. A virtual instance re-creates in minutes,
  and the host holds no durable state, so the cycle loses nothing. The monthly
  reinstall schedule then retires.

<a id="iac-train"></a>

### `infra/train`

The stack declares four resources: a routed IPv4 address, a scratch volume, a
block root volume, and one `scaleway_instance_server`.

The `instance_type` variable defaults to `H100-1-80G`. `L40S-1-48G` is for a
budget run at 4B. The `L40S-1-48G` must not host the BF16 teacher, because 48 GB
does not hold Qwen3-32B at BF16 ([training](training.md)).

**Scaleway grants no quota for an H100 offer.** An operator must request the
quota from Scaleway Support before the first apply. The bootstrap runbook
records the request and the grant. Until the grant exists,
`make infra-up STACK=train` fails.

The instance boots the **Ubuntu Noble GPU OS 13 (NVIDIA)** image. That image
supplies the NVIDIA driver, Docker, and the NVIDIA Container Toolkit. Ubuntu
Focal GPU OS 12 is the legacy image and must not be used. Resolve the image with
`scaleway_marketplace_image`. Confirm the marketplace label with
`scw marketplace image list` before the first apply.

| Resource                   | Requirement                                                         |
| -------------------------- | ------------------------------------------------------------------- |
| `scaleway_instance_ip`     | `type = "routed_ipv4"`                                              |
| `scaleway_instance_volume` | `type = "scratch"`; 3000 GB on H100, 1600 GB on L40S                |
| Root volume                | `volume_type = "sbs_volume"`, `size_in_gb = 125`, `sbs_iops = 5000` |
| `scaleway_instance_server` | `additional_volume_ids` holds the scratch volume                    |

OpenTofu must declare the scratch volume. Scaleway attaches scratch storage
automatically only through the console and the CLI. Without the declaration the
corpus lands on the 125 GB root volume, which Scaleway bills per hour of
allocated size.

The stack must not use `scaleway_flexible_ip`. That resource works with an
Elastic Metal server only.

Cloud-init pulls the Axolotl and vLLM images and installs the S3 client.
Cloud-init must not receive a credential, because `user_data` is readable
through the instance API. CI delivers the train credential over SSH after boot,
and the first SSH step synchronizes the corpus from Object Storage to scratch
NVMe ([credentials](#credentials)). The cloud-init must not run a distribution
upgrade. A `package_upgrade` on a GPU OS image breaks the NVIDIA driver, and the
failure survives a reboot. If the cloud-init upgrades a package, it must set
`apt_get_upgrade_subcommand: "upgrade"`. A broken driver still bills at the full
GPU rate.

Apply this stack at the start of a training session. Destroy it at the end.
There are no stop or hibernate half-states: **down means destroyed**. A stopped
instance stops its compute billing, but its root volume and its reserved IPv4
continue to bill. Standby bills as a running instance.

Scratch NVMe is ephemeral at deletion, so destruction loses no durable data. A
reboot and a stop-in-place keep the scratch data. A full stop, a server-type
migration, and a delete erase it.

Public bandwidth bounds the corpus transfer: 10 Gb/s on `H100-1-80G` and 2.5
Gb/s on `L40S-1-48G`. Transfer time is billed GPU time.

<a id="iac-image"></a>

### `infra/image`

The stack publishes the OpenBSD guest image that the agentic suite needs.
`make image-build` runs `autoinstall(8)` under qemu in CI and emits a qcow2
file. `make image-publish` uploads the file to the artifacts bucket. Apply the
stack when the OpenBSD release changes. Keep the previous image in the artifacts
bucket.

- **IAC-IMAGE-1** — The `fuguvm` tool drives the `autoinstall(8)` install of
  `make image-build`, and it exports the installed disk as the qcow2 file. The
  `autoinstall(8)` response file lives in the stack directory. The build records
  the digest of the response file with the image, so a rebuild is reproducible.
- **IAC-IMAGE-2** — The tool must accept an existing qcow2 file as the base disk
  of a guest. The suite then installs nothing per host. A raw export serves the
  Elastic Metal route of [IAC-HOSTS](#iac-hosts).

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
KVM-over-IP console is a paid option, it is not available on each offer, it
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

<a id="iac-state"></a>

## State

OpenTofu state lives in a dedicated Scaleway Object Storage bucket, through the
S3-compatible backend. Each stack keeps its own key.

The backend must set `use_lockfile = true`. Scaleway Object Storage supports
conditional writes, so the backend holds a native lock. The lock is necessary,
because three writers exist: CI, the operator, and the development host. A
`tofu apply` must not set `-lock=false`. A pull-request plan must set
`-lock=false`, because a plan writes no state.

The backend block must use `endpoints = { s3 = ... }` and `use_path_style`. The
arguments `endpoint` and `force_path_style` are deprecated. The backend must
take its credential from the environment. The backend block must not hold an
access key or a secret key.

The state bucket must have versioning on. A lifecycle rule must expire a
noncurrent version after 30 days, because the lock adds a write and a delete at
each run.

The state object holds a secret. `scaleway_iam_api_key` exports `secret_key` as
a state attribute, and the corpus synchronization key reaches the state through
`user_data`. Three controls apply together:

1. OpenTofu must encrypt the state and the plan.
2. A bucket policy on the state bucket must name each principal that needs the
   bucket, and no other principal.
3. OpenTofu must not create the pipeline key, the operator key, or the train
   key.

A bucket policy is an allow list. A Deny statement has no effect under version
`2023-04-17`. A bucket holds one policy, and a new policy overwrites the old
one. A principal that the policy does not name loses access to that bucket. Test
each bucket-policy change on a scratch bucket first.

Recovery from a bad state is a human act. The runbook must hold the
`tofu force-unlock` procedure and the `tofu import` procedure.

<a id="iac-cred"></a>

## Credentials

Scaleway offers no federation for a machine caller. A stored API key is the only
option, so each key needs a scope, an expiry, and a rotation period.

Three IAM applications split the credentials by blast radius
([decisions](DECISIONS.md), D9). The persistent stack declares each application
and each policy. The persistent stack must not declare an API key.

- **The pipeline application.** Its API key lives in the CI environment, as a
  secret. Its policy permits: apply and destroy of `infra/dev`, `infra/train`,
  and `infra/image`; read and write of Object Storage in the project; and read
  of consumption and billing data. IAM administration and project deletion are
  excluded, so the credential cannot widen its own scope. The policy must not
  hold `IAMManager`, `OrganizationManager`, or `ProjectManager`.
- **The operator application.** Its API key lives in the operator environment
  (`SCW_ACCESS_KEY`, `SCW_SECRET_KEY`, `SCW_DEFAULT_PROJECT_ID`,
  `SCW_DEFAULT_ORGANIZATION_ID`). A human holds it. Its policy adds the IAM
  administration that `infra/persistent` needs. In CI, only a protected manual
  workflow dispatch uses it, and only to apply `infra/persistent`. The same
  application serves recovery, for example a manual `make infra-down` when CI is
  not available.
- **The train application.** Its policy permits read and write of Object Storage
  in the project, and nothing else. Each of its keys lives for one campaign.

An environment variable beats the `provider` block. CI must export exactly one
credential set. The `provider` block must not set `access_key`, `secret_key`, or
`project_id`.

IAM grants access to Object Storage at the project level. IAM cannot grant
access to one bucket. The training instance therefore reaches each bucket in the
project. A bucket policy is the only per-bucket control, and both gates must
allow the action.

A new policy needs up to one minute to apply, and up to five minutes for Object
Storage. The first bucket call after a policy change must retry.

No credential is in the repository. A human creates the pipeline key and the
operator key with `scw iam api-key create` and sets `expires-at`. An expiry
cannot be changed afterwards, so a rotation is always a create and a delete. An
application holds several keys at the same time, so a rotation causes no outage.
Rotate the pipeline key after each training campaign, and at 90 days.

Rotation order:

1. Create a second key on the same application.
2. Set the new key in the CI secret.
3. Run one workflow and confirm it passes.
4. Delete the old key.

<a id="iac-traincred"></a>

### The train credential

A Scaleway instance has no metadata identity. `user_data` is readable through
the instance API. A managed `scaleway_iam_api_key` writes its secret to state.
The train key therefore must not touch OpenTofu, `user_data`, or state:

1. At `make infra-up STACK=train`, CI creates a key on the train application
   with `scw iam api-key create`, and sets `expires-at` to the value of the
   `ttx:expires` tag.
2. CI delivers the key to the instance over SSH, after boot. The SSH channel is
   the same transport that `make train-cpt` uses.
3. The first SSH step synchronizes the corpus to scratch NVMe.
4. `make infra-down STACK=train` deletes the key. The expiry is the backstop
   when the teardown fails.

<a id="iac-ssh"></a>

### SSH keys

Each SSH key is an IAM resource. `ssh_key_ids` is required on the metal server,
and a change to it forces a reinstall. Rescue mode authenticates with the same
keys. The runbook must record which key reaches which host.

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

One guardrail blocks. The others inform or gate.

| Guardrail                         | Kind                  | Effect                                  |
| --------------------------------- | --------------------- | --------------------------------------- |
| Per-Organization quotas           | Platform, hard        | Scaleway refuses to create the resource |
| Scoped IAM policies               | Platform, hard        | Scaleway refuses the action             |
| The monthly budget and its alerts | Platform, soft        | Scaleway sends a notification           |
| The pre-apply forecast check      | Pipeline              | The pipeline stops its own apply        |
| The idle watchdog                 | Pipeline, best effort | The pipeline destroys an idle stack     |

**Quotas.** Ask Scaleway Support to set a quota of 1 for `H100-1-80G`, 1 for
`L40S-1-48G`, and 1 for the dev offer, in `fr-par-2`. A quota applies per
Organization and per Availability Zone, so one zone bounds the exposure.

**The budget.** A monthly budget on the Scaleway Organization. Scaleway has no
project-level budget. The initial budget is EUR 1,500 ([training](training.md)).
Only a human raises it. `scaleway_billing_budget` takes the value in cents. A
Scaleway budget notifies. It does not block. It is not a cap.

**The alerts.** Billing alerts at 50, 75, and 100 percent of the budget, to
email and to a CI webhook. Scaleway triggers an alert on the amount after
discount and tax. Each price in this project is before tax. The runbook must
record the tax status of the Organization, and must derive the budget value from
it.

**The forecast check.** Before each `tofu apply`, the pipeline reads
`GET /billing/v2beta1/consumptions` for the project. The pipeline stops the
apply when either condition holds:

| Condition                                                  | Reason                       |
| ---------------------------------------------------------- | ---------------------------- |
| The `updated_at` field is older than 6 hours               | The data is too old to trust |
| Consumption plus the forecast of the run passes the budget | The run cannot complete      |

The forecast is the hourly price of the instance multiplied by the maximum
lifetime of the run. A level check alone cannot bound spend, because it looks
only at money already spent. Scaleway publishes no freshness figure for the
consumption data.

**The idle watchdog.** `make infra-watchdog` runs every 30 minutes from CI, and
every 30 minutes from a systemd timer on the development host. The target must
be idempotent. A scheduled GitHub workflow is best effort. GitHub delays it
under load, and GitHub disables it after 60 days with no new commit in a public
repository. The second timer is therefore necessary.

A train stack is **idle** when each test passes:

| Test                                                        | Value |
| ----------------------------------------------------------- | ----- |
| The stack holds a server tagged `ttx:lifecycle=ephemeral`   | true  |
| The server is older than 20 minutes                         | true  |
| The heartbeat object is absent, or is older than 20 minutes | true  |

The training driver writes the heartbeat object every 60 seconds, on a timer.
The timer must not depend on checkpointing, because an epoch can exceed 20
minutes. The driver claims the stack once at start, with an `If-None-Match: *`
conditional write against an owner object. A second run fails the claim and must
not start.

The watchdog destroys the train stack when the stack is idle, or when the
current time passes the `ttx:expires` tag, whichever comes first. The watchdog
must report, and must not destroy, a resource with no `ttx:managed` tag. The
watchdog must report a state lock older than two hours. The watchdog must never
touch a resource tagged `ttx:lifecycle=persistent`.

<a id="iac-teardown"></a>

## Teardown

`tofu destroy` alone is not a teardown. A cancelled apply can create a resource
that never enters the state file, and that resource bills without limit.

A destroy of `infra/train` must remove the server, the scratch volume, the root
volume, and the routed IPv4 address. Scaleway bills a reserved IPv4 whether it
is attached or not.

`make infra-watchdog` reconciles the live resources against the state of each
stack. It reports each resource that carries no `ttx:managed` tag. A human
removes it.

A teardown of the whole project runs in this order: `train`, then `dev`, then
`image`, then `persistent`. A destroy of `persistent` surrenders four globally
unique bucket names. Only a human runs it.

<a id="iac-tasks"></a>

## Task runner

```
make infra-bootstrap            # the state bucket and its lifecycle rule — a human, once
make infra-fmt-check            # tofu fmt -recursive -check — no credential
make infra-validate STACK=name  # tofu validate — no credential
make infra-check                # infra-fmt-check, then infra-validate for each stack
make infra-plan STACK=name      # tofu plan — review what a session will create
make infra-plan-ro STACK=name   # tofu plan -lock=false — the pull-request plan
make infra-up STACK=name        # tofu apply — GPU billing starts here for train
make infra-down STACK=name      # tofu destroy — billing stops here
make infra-status               # list live resources, so nothing idles unnoticed
make infra-price STACK=name     # print the hourly price of the stack compute
make infra-cost                 # month-to-date consumption against the budget
make infra-watchdog             # destroy an idle train stack; report an orphan
make dev-rebuild-check          # the reinstall gates
make dev-reinstall              # reinstall the development host in place
make image-build                # autoinstall OpenBSD under qemu; emit a qcow2
make image-publish              # tofu apply image
make corpus-sync                # move the corpus between the host and Object Storage
make train-cpt                  # run the Axolotl CPT config on the instance
make train-sft                  # run the SFT config
make eval-sweep                 # run an evaluation sweep
```

The same targets run in CI and on the development host. `make check` must call
`make infra-check`, so a local run reproduces the CI gate. `make infra-down` is
a first-class step of the training runbook, not an afterthought.

`make infra-price STACK=train` reads `hourly_price` from the
`scaleway_instance_server_type` data source. `make infra-price STACK=dev` must
call the Scaleway Product Catalog API, because the Elastic Metal offer data
source exposes no price. Do not hardcode a price in the repository.

The runbook must state how a target reaches the GPU instance. `make train-cpt`
runs on the instance, and the transport is part of the deterministic entry point
that D8 requires.

<a id="iac-ci"></a>

## CI

CI operates the pipeline. An operator does not need to.

Each trigger binds to one credential and one guard:

| Trigger             | Job                                     | Credential         | Guard                                                   |
| ------------------- | --------------------------------------- | ------------------ | ------------------------------------------------------- |
| `pull_request`      | `tofu fmt -check`, `tofu validate`      | none               | Each pull request                                       |
| `pull_request`      | `tofu plan -lock=false`                 | none, or read only | The branch is not a fork                                |
| `push` to `main`    | `tofu apply` of `dev`, `train`, `image` | pipeline           | Environment `infra-apply`                               |
| `workflow_dispatch` | Any action of `dev`, `train`, `image`   | pipeline           | Environment `infra-apply`                               |
| `workflow_dispatch` | `tofu apply` of `infra/persistent`      | operator           | Environment `infra-admin`, with a required human review |
| `schedule`          | Watchdog, reinstall                     | pipeline           | Environment `infra-apply`                               |

A workflow must not use the `pull_request_target` trigger. A plan job must not
run on a pull request from a fork. `tofu init` runs the provider binary that the
branch names, so a plan on an untrusted branch executes untrusted code. The
`infra-apply` environment must permit the `main` branch only.

The `infra-admin` environment holds the operator key. A required human review
gates each of its runs. Operation runs with the pipeline credential: plan and
apply of `dev`, `train`, and `image`, training campaigns, evaluation sweeps, the
idle watchdog, and the scheduled reinstall of the development host.

One concurrency group serializes each apply, per stack. The group must set
`cancel-in-progress: false`, because the runner kills a cancelled step after
about ten seconds and a cancelled apply can orphan a billed resource. The group
must set `queue: max`, because the default keeps one pending run and cancels the
rest. A concurrency group does not replace the state lock.

A GitHub-hosted runner has no KVM, so it cannot run the agentic suite. CI must
drive the suite on the development host. If the repository is public, do not
register a self-hosted runner. Use SSH from a GitHub-hosted runner instead.

The workflow logs are one audit trail. Scaleway Audit Trail is the second, and
it is free. It records each `CreateServer` and `DeleteServer` call for Instances
and for Elastic Metal, with the principal and the source address. Audit Trail
keeps 90 days, so a daily export writes each day to the artifacts bucket. Audit
Trail does not cover Object Storage, Block Storage, or Billing.

A human can start any stack action with a manual workflow dispatch. The spend
guardrails bound every workflow.
