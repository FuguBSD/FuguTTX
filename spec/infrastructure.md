# Infrastructure

OpenTofu, with the Scaleway provider, declares each Scaleway resource. Do not make resources in the console. Per-minute GPU billing rewards fast create/destroy cycles. Infrastructure as code makes `destroy` safe and routine. The infrastructure code has the ISC license, like all project tooling.

## Layout

```
infra/
├── modules/
│   ├── gpu-instance/     # scaleway_instance_server: GPU OS image, cloud-init, flexible IP
│   └── bucket/           # scaleway_object_bucket + access policy
├── persistent/           # long-lived stack: object storage, IAM — applied rarely
└── train/                # ephemeral stack: one GPU instance — up/down around each session
```

## Stacks

Two stacks, with two lifecycles:

- **`infra/persistent`** — the Object Storage buckets `ttx-corpus`, `ttx-checkpoints`, and `ttx-artifacts`, plus an IAM application with an API key. The key has access to exactly those buckets and is for the training instances. Apply this stack rarely. Review changes like all code.
- **`infra/train`** — one `scaleway_instance_server`. The `instance_type` variable defaults to `H100-1-80G`; `L40S-1-48G` is for budget runs. The instance boots the Scaleway GPU OS image and has a flexible IP. Cloud-init pulls the Axolotl and vLLM images, installs the bucket-scoped API key, and synchronizes the corpus from Object Storage to scratch NVMe. Apply this stack at the start of a training session. Destroy it at the end. There are no stop or hibernate half-states: **down means destroyed**. Scratch NVMe is ephemeral, so destruction loses nothing.

## Durability

Object Storage is the only durable layer. The corpus synchronizes down at boot. Checkpoints synchronize up during training. Release artifacts land in `ttx-artifacts`. Thus `tofu destroy` cannot lose data. This invariant permits the aggressive teardown discipline that keeps costs low.

## State

OpenTofu state lives in a dedicated Scaleway Object Storage bucket, through the S3-compatible backend. The state bucket is the only resource not managed by OpenTofu. Make it once with `scw object bucket create`, per the bootstrap runbook. FuguTTX is a single-operator project, so no distributed state lock is configured. This is documented. Examine it again if the team grows.

## Credentials

`SCW_ACCESS_KEY`, `SCW_SECRET_KEY`, and `SCW_DEFAULT_PROJECT_ID` come from the operator environment. They must not be in the repository. The training instance receives only the bucket-scoped API key from the persistent stack. Rotate that key after each training campaign.

## Task runner

```
just infra-plan train     # tofu plan  — review what a session will create
just infra-up train       # tofu apply — GPU billing starts here
just train cpt            # run the Axolotl CPT config on the instance
just train sft            # run the SFT config
just infra-down train     # tofu destroy — billing stops here
just infra-status         # list live resources, so nothing idles unnoticed
```

On success, `just infra-up` shows the hourly price of the instance. `just infra-down` is a first-class step of the training runbook, not an afterthought.

## CI

`tofu fmt -check` and `tofu validate` run on each push. CI holds no cloud credentials. CI does not run `plan` or `apply`. An operator runs them, with local credentials.
