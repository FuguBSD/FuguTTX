# Infrastructure

OpenTofu, with the Scaleway provider, declares each Scaleway resource.
Do not make resources in the console.
Per-minute GPU billing rewards fast create/destroy cycles.
Infrastructure as code makes `destroy` safe and routine.
The infrastructure code has the ISC license, like all project tooling.

## Layout

```
infra/
├── modules/
│   ├── gpu-instance/     # scaleway_instance_server: GPU OS image, cloud-init, flexible IP
│   ├── metal-server/     # scaleway_baremetal_server: OS install, SSH keys, provisioning
│   └── bucket/           # scaleway_object_bucket + access policy
├── persistent/           # long-lived stack: object storage, IAM, billing alerts — applied rarely
├── dev/                  # the development host: one Elastic Metal server — long-lived, rebuildable
└── train/                # ephemeral stack: one GPU instance — up/down around each session
```

## Bare metal rule

A workload runs on an Elastic Metal server, not on a virtual instance, when it needs
hardware virtualization or full native performance.
The agentic evaluation suite needs both: qemu with KVM for the OpenBSD guests, and
native CPU speed for llama.cpp inference in each scenario.
Scaleway provisions virtual instances and Elastic Metal servers with OpenTofu, and both
can boot Linux or OpenBSD. Elastic Metal bills per hour.

## Stacks

Three stacks, with three lifecycles:

- **`infra/persistent`** — the Object Storage buckets `ttx-corpus`, `ttx-checkpoints`,
  and `ttx-artifacts`; the IAM applications, their policies, and their API keys; and the
  billing alerts. Apply this stack rarely.
  Review changes like all code.
- **`infra/dev`** — the development host: one Elastic Metal server, with Linux and KVM.
  It is the runtime for the development agents and for the evaluation sweeps
  ([autonomous development](agents.md)). It runs the OpenBSD guests of the agentic suite
  under qemu with KVM, with scenarios in parallel.
  Linux is the host OS, because qemu has hardware acceleration only there.
  OpenBSD is always the guest.
  The host is long-lived, but a rebuild from code must reproduce it.
  Rebuild it from code on a schedule, so drift cannot accumulate.
  The host holds no durable state.
- **`infra/train`** — one `scaleway_instance_server`. The `instance_type` variable
  defaults to `H100-1-80G`; `L40S-1-48G` is for budget runs.
  The instance boots the Scaleway GPU OS image and has a flexible IP. Cloud-init pulls
  the Axolotl and vLLM images, installs the bucket-scoped API key, and synchronizes the
  corpus from Object Storage to scratch NVMe.
  Apply this stack at the start of a training session.
  Destroy it at the end.
  There are no stop or hibernate half-states: **down means destroyed**. Scratch NVMe is
  ephemeral, so destruction loses nothing.

### Native OpenBSD hosts

Scaleway provisions OpenBSD with OpenTofu, as a virtual instance or on Elastic Metal.
No current suite requires a native OpenBSD host.
When a suite requires one — a native amd64 benchmark host, or a build-graded evaluation
host with chrooted source and port builds — add it as its own stack, with the same
lifecycle discipline.
Do not add the host before the suite exists ([evaluation](evaluation.md)).

## Durability

Object Storage is the only durable layer.
The corpus synchronizes down at boot.
Checkpoints synchronize up during training.
Release artifacts and scorecards land in `ttx-artifacts`. Thus `tofu destroy` cannot
lose data.
The development host follows the same rule: everything on it rebuilds from git
and Object Storage. This invariant permits the aggressive teardown discipline that keeps
costs low.

## State

OpenTofu state lives in a dedicated Scaleway Object Storage bucket, through the
S3-compatible backend.
The state bucket is the only resource not managed by OpenTofu.
Make it once with `scw object bucket create`, per the bootstrap runbook.
CI is the only environment that runs `apply`, and one GitHub Actions concurrency group
serializes each run.
Thus no distributed state lock is necessary.

## Credentials

Two IAM applications exist.
The persistent stack declares both:

- **The pipeline application.** Its API key lives in the CI environment, as a secret.
  Its policy permits: apply and destroy of the `infra/` stacks; read and write of the
  three project buckets; read of consumption and billing data.
  IAM administration and project deletion are excluded.
  A pipeline credential cannot widen its own scope.
- **The recovery application.** Its API key lives in the operator environment
  (`SCW_ACCESS_KEY`, `SCW_SECRET_KEY`, `SCW_DEFAULT_PROJECT_ID`). It is for recovery
  only, for example a manual `just infra-down` when CI is not available.

No credential is in the repository.
The training instance receives only the bucket-scoped API key from the persistent stack.
Rotate the pipeline key and the bucket-scoped key after each training campaign.

## Spend guardrails

The guardrails are platform controls, not conventions:

- A documented monthly cap on the Scaleway project.
  The initial cap is €1,500 ([training](training.md)). Only a human raises the cap.
- Billing alerts at 50, 75, and 100 percent of the cap.
- A pre-apply consumption check: before each `tofu apply`, the pipeline reads the
  Scaleway consumption API. At or above the cap, the apply stops.
- An idle watchdog: a scheduled CI job runs `just infra-status` and destroys a train
  stack with no training in flight.
- The IAM policies above.

## Task runner

```
just infra-plan train     # tofu plan  — review what a session will create
just infra-up train       # tofu apply — GPU billing starts here
just train cpt            # run the Axolotl CPT config on the instance
just train sft            # run the SFT config
just infra-down train     # tofu destroy — billing stops here
just infra-status         # list live resources, so nothing idles unnoticed
```

The same recipes run in CI and on the development host.
On success, `just infra-up` shows the hourly price of the instance.
`just infra-down` is a first-class step of the training runbook, not an afterthought.

## CI

CI operates the pipeline.
An operator does not need to.

- Validation runs on each push: `tofu fmt -check` and `tofu validate`.
- Operation runs with the pipeline credential: plan and apply of every stack, training
  campaigns, evaluation sweeps, the idle watchdog, and the scheduled rebuild of the
  development host.
- One concurrency group serializes each apply.
  The workflow logs are the audit trail.
- A human can start any stack action with a manual workflow dispatch.
- The spend guardrails bound every workflow.
