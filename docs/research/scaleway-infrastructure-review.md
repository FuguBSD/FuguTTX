# Infrastructure research report

Date: 2026-08-02. Scope: `spec/infrastructure.md`, and the sibling documents it touches.
Method: eight verified research dimensions, each with an independent verification pass.

Evidence rule for this report: a price or an offer name carries its source in the text.
A claim that no reachable source proves carries the word UNVERIFIED. Do not remove the
word UNVERIFIED when you copy a line from this report.

## 1. Summary

The research changes five things about the specification.

1. Scaleway offers no OpenBSD image.
   The word “openbsd” does not appear once in the Scaleway documentation corpus.
   Two sentences of the specification are false.
2. No state lock is a defect, not a saving.
   Scaleway Object Storage gained conditional writes on 2026-05-26, and the
   specification creates a second writer by design.
3. Scaleway has no hard spend cap.
   A budget notifies. Only a per-Organization quota blocks resource creation, and the
   specification never mentions quotas.
4. The train stack cannot deliver what it promises.
   Scratch NVMe needs an explicit volume.
   There is no such thing as a bucket-scoped API key.
   No H100 quota exists by default, so the default train stack cannot apply today.
5. Every euro figure in the specification is unverified after the Scaleway price
   revision of 2026-06-01.

## 2. Corrections

Order is by severity.
“Line” is the line in `spec/infrastructure.md` at commit
`077dfa9d84942660e4b544a6a9ccd473c0e89710`.

| # | Line | Current text | Corrected text | Evidence |
| --- | --- | --- | --- | --- |
| 1 | 60 | “Scaleway provisions OpenBSD with OpenTofu, as a virtual instance or on Elastic Metal.” | Scaleway offers no OpenBSD image. A project-built image is the only route. | `rg -ri openbsd` over the whole `scaleway/docs-content` repository returns zero matches. The Elastic Metal OS list is 28 images, all Linux or Windows (recorded API response, `zones/fr-par-2/os`, 2026-06-11). `instances/reference-content/images-and-instantapps.mdx` lists Linux and Windows only (validated 2025-07-01). |
| 2 | 29 | “both can boot Linux or OpenBSD” | Both boot Linux from the Scaleway catalogue. Neither offers an OpenBSD image. | Same as #1. `scaleway_baremetal_os` resolves only against the platform OS list. |
| 3 | 84-86 | “one GitHub Actions concurrency group serializes each run. Thus no distributed state lock is necessary.” | The backend must set `use_lockfile = true`. | Three writers exist: CI, the recovery operator (lines 98-100), and the development host (line 130, `agents.md` lines 57-58). Conditional writes reached general availability on 2026-05-26 (Scaleway changelog `may2026/2026-05-26-object-storage-added-conditional-writes...`; the provider `backend_guide.md` says “Since May of 2026”). OpenTofu `s3.mdx`: “native S3 locking via conditional writes with `If-None-Match` header … `use_lockfile=true`”. |
| 4 | 108-112 | “The guardrails are platform controls, not conventions” ... “A documented monthly cap on the Scaleway project.” | A Scaleway budget notifies. It does not block. The budget is Organization-scoped. A per-Organization quota is the only control that blocks creation. | `billing/how-to/use-billing-alerts.mdx` line 12: alerts “notify you when predefined budget thresholds are met” (validated 2025-09-03). The Billing v2 API `Budget` struct has no enforcement field. `scaleway_billing_budget` takes `organization_id` and `consumption_limit` in cents, and has no `project_id`. `organizations-and-projects/additional-content/organization-quotas.mdx` line 32: “At Scaleway, quotas are applicable per Organization” (validated 2025-10-29). |
| 5 | 97 | “A pipeline credential cannot widen its own scope.” | The pipeline credential applies the stack that declares the IAM objects, so it holds IAM administration rights. It can widen its own scope. | Line 91 puts the IAM applications and policies in `infra/persistent`. Lines 140-141 make CI apply every stack. `iam/reference-content/permission-sets.mdx`: “Any user or application benefiting from the `IAMManager` and/or `OrganizationManager` permission sets is able to create policies giving themselves access to any other actions and resources within the Organization” (validated 2026-03-20). The minimum to apply the stack is `IAMApplicationManager` plus `IAMPolicyManager`; that pair does not carry project deletion, so only half of line 96 fails. |
| 6 | 103 | “the bucket-scoped API key” | No bucket-scoped IAM grant exists. IAM scopes to a Project or to the Organization. A bucket policy is the only per-bucket control. | `iam/reference-content/supported-products-resource-level.mdx` (validated 2026-07-13) lists three integrated products: IAM, Key Manager, Secret Manager. Object Storage is absent. `object-storage/api-cli/combining-iam-and-object-storage.mdx`: “Bucket policies operate at the bucket level” (validated 2025-06-12). |
| 7 | 14, 52 | Module list omits the scratch volume, and line 52 states the corpus lands on scratch NVMe. | The module must declare `scaleway_instance_volume` with `type = "scratch"` and attach it with `additional_volume_ids`. | `gpu/how-to/use-scratch-storage-h100-instances.mdx` (validated 2025-12-04) gives three separate answers: auto-attach applies to “the Scaleway CLI or console”; the API needs an extra volume; the OpenTofu section declares the volume. Provider `instance_volume.md`: “`type` - (Required) ... `scratch` (Local Scratch SSD)”. |
| 8 | 48-49 | The `instance_type` variable defaults to `H100-1-80G`. | The default holds, but a quota grant is a prerequisite. Scaleway grants no H100 quota by default. | `organization-quotas.mdx`, GPU section (validated 2025-10-29): every H100 row reads “To use this product, you must contact our Support team” in both the payment-validated and the identity-validated columns. `L40S-1-48G` and `L4-1-24G` read 1 after identity validation. |
| 9 | 14, 51 | “flexible IP”; “installs the bucket-scoped API key” | The resource is `scaleway_instance_ip` with `type = "routed_ipv4"`. `scaleway_flexible_ip` is Elastic Metal only. | Provider `flexible_ip.md`: “Flexible IPs are exclusively available for Elastic Metal (bare metal) servers.” `routed_ip_enabled` no longer exists on `scaleway_instance_server`; `rg` over the provider `docs/` tree returns zero matches. |
| 10 | 51 | “Cloud-init pulls the Axolotl and vLLM images” | The cloud-init must not run a distribution upgrade. | `gpu/troubleshooting/updating-gpu-instance-with-cloud-init.mdx` (validated 2025-10-28): “the Nvidia drivers may break causing the GPU to become unavailable. This problem persists even after a manual reboot.” The remedy is `system_info: apt_get_upgrade_subcommand: "upgrade"`. |
| 11 | 50 | “the Scaleway GPU OS image” | Name the image: Ubuntu Noble GPU OS 13 (NVIDIA), on Ubuntu 24.04. Ubuntu Focal GPU OS 12 is legacy. | `gpu/how-to/use-preinstalled-env.mdx` (validated 2025-07-21). The exact marketplace label is UNVERIFIED. Scaleway’s own OpenTofu example still uses `ubuntu_jammy_gpu_os_12`, uses typographic quotes, and misspells the resource as `scaleway_instance-server`. |
| 12 | 55-56 | “Scratch NVMe is ephemeral, so destruction loses nothing.” | The sentence is accurate but the reason is incomplete. A stopped instance still bills its root volume and its reserved IPv4. | `instances/reference-content/understanding-instance-pricing.mdx` (validated 2025-08-19): “any attached storage or flexible IPv4s continue to be billed even when powered off.” A reboot and a stop-in-place keep scratch data; a full stop/start erases it (`use-scratch-storage-h100-instances.mdx`). |
| 13 | 82-83 | “The state bucket is the only resource not managed by OpenTofu. Make it once with `scw object bucket create`.” | The command must set versioning. The lifecycle rule the lock needs cannot be made with `scw`. | scaleway-cli `docs/commands/object.md`: `enable-versioning` defaults to `false`. `grep -in lifecycle` over the same file returns zero hits. OpenTofu `s3.mdx` advises a version-expiry lifecycle rule when `use_lockfile` runs against a versioned bucket. |
| 14 | 35-36 | Bucket names `ttx-corpus`, `ttx-checkpoints`, `ttx-artifacts`. | Bucket names are unique across the whole Scaleway platform. Add a suffix. | `object-storage/faq.mdx` (validated 2025-12-19): “Bucket names are unique in our whole platform … The 'Bucket already exists’ error message is triggered when the name … is already reserved by another user.” A deleted name is free for anybody. |
| 15 | 35-36 | Three buckets, with no licensing-lane boundary. | The eval/RAG corpus needs its own bucket. D6 makes the lane rule absolute; the storage layer enforces nothing today. | `spec/decisions.md` D6. No specification file separates the lanes by bucket, prefix, or policy. |
| 16 | 91-92 | The persistent stack declares the API keys. | OpenTofu must not create the pipeline key or the recovery key as managed resources. | Provider `iam_api_key.md`, Attributes Reference: “`secret_key`: The secret Key of the IAM API key.” A managed attribute persists to state, and the state lives in a bucket the same credential reads. |
| 17 | 115-116 | “destroys a train stack with no training in flight” | “No training in flight” has no machine-checkable definition. D8 requires one. | `spec/decisions.md` D8: “Each outcome has a machine-checkable definition of done.” Line 127 defines `just infra-status` as a lister only. |
| 18 | 39-47 | `infra/dev` names no SKU, no zone, and no billing plan. | Name all three. Forbid the monthly plan. | `elastic-metal/faq.mdx` (validated 2025-09-24): a monthly commitment fee equals one month of subscription, and the switch to monthly is one-way. `elastic-metal/how-to/get-use-loyalty-reward.mdx`: the offsetting voucher ended for new subscriptions on 2026-04-01. |
| 19 | 46 | “Rebuild it from code on a schedule.” | Reinstall in place. Do not destroy and re-order. | Three recorded catalogue snapshots of `fr-par-2` show stock movement. Eight offers reported `stock: empty` on 2026-06-11. `elastic-metal-stock-levels.mdx` (validated 2025-09-09) documents the `empty` state. `scw baremetal server install` and the provider `reinstall_on_config_changes` reinstall without releasing the machine. |
| 20 | 143-144 | “The workflow logs are the audit trail.” | Scaleway Audit Trail is a second record, and it is free. It does not cover Object Storage. | `audit-trail/faq.mdx` (validated 2025-11-10): “Audit Trail is free of charge.” `audit-trail/reference-content/resource-integration-with-adt.mdx` (validated 2026-06-12) lists Object Storage, Billing, Block Storage, and GPU Instances as not integrated. |
| 21 | 5 | “Per-minute GPU billing” | Three Scaleway pages disagree. Plan for a 60-minute minimum. | `instances/faq.mdx` (validated 2025-12-19): GPU instances “Billed per minute of uptime”. `billing/faq.mdx` (validated 2025-09-09): “billed separately for a minimum of 60 minutes”. `understanding-instance-pricing.mdx` (validated 2025-08-19): “Instances are billed per hour” with “no minimum commitment”. |
| 22 | 72-73 | “Thus `tofu destroy` cannot lose data.” | The claim fails in three ways. | Up to one epoch is unsynchronized (`training.md` line 53). A destroy during an upload leaves an incomplete multipart upload, which Scaleway bills. A destroy of `infra/persistent` deletes the buckets and surrenders the names. |
| 23 | 3-4 | “Do not make resources in the console.” | Six documented exceptions exist. | The state bucket, its lifecycle rule, the Organization and Project, the quota grants, the two operator API keys, and any OpenBSD OS install. |
| 24 | 14-16 | Module descriptions. | The `gpu-instance` module also needs the scratch volume and the root volume. The `metal-server` word “provisioning” is undefined. The `bucket` phrase “access policy” is ambiguous. | Provider `instance_server.md`: `root_volume { volume_type, size_in_gb, sbs_iops }`. `gpu/how-to/create-manage-gpu-instance.mdx` (validated 2025-09-17): “For a GPU OS, the recommended size is 125 GB”, with a 5,000 IOPS block volume by default. `ObjectStorageFullAccess` excludes bucket-policy actions, so the choice between an ACL and a bucket policy changes the IAM table. |
| 25 | 11-20 | The layout names no `versions.tf`, no backend file, and no lockfile. | Pin OpenTofu, pin the provider, and commit the lockfile. | Provider v2.80.0 published 2026-07-30. The local clone is untagged at HEAD `c90f1e2`, 2026-07-31. Ephemeral resources and write-only arguments need OpenTofu 1.11 or later. |

## 3. Answers to the four open questions

### 3.1 The Elastic Metal SKU

**Answer: `EM-B430E-NVMe`, in zone `fr-par-2`, on the hourly plan.**

Specification, from `elastic-metal/reference-content/elastic-metal-datasheet.mdx`
(validated 2026-06-16): AMD EPYC 4545P at 3.00 GHz, 16 cores and 32 threads, 64 GiB
DDR5, two NVMe disks of 3.84 TB, public bandwidth 3 Gb/s with a maximum of 10 Gb/s.
Zones: `fr-par-1`, `fr-par-2`, `nl-ams-1`, `nl-ams-2`.

Price: EUR 0.548 per hour, read from a recorded Scaleway API response for `fr-par-2`,
dated 2026-06-11, in the Scaleway OpenTofu provider test data.
The date is after the price revision of 2026-06-01. A 730-hour month is EUR 400.04. The
monthly-plan price of this SKU is UNVERIFIED, and the project must not use the monthly
plan.

Stock on 2026-06-11 in `fr-par-2`: `available`. Images: the offer accepts 11 of the 28
catalogue images, including Ubuntu 24.04 LTS. It does not accept Proxmox VE or Rocky
Linux. It carries the `cloud-init` tag.

Fallback chain, all prices read on 2026-06-11 from the same recorded response:

| Rank | Offer | Cores/threads | RAM | EUR/hour | EUR/730 h |
| --- | --- | --- | --- | --- | --- |
| 1 | EM-B430E-NVMe | 16 / 32 | 64 GiB | 0.548 | 400.04 |
| 2 | EM-B330E-NVMe | 12 / 24 | 64 GiB | 0.438 | 319.74 |
| 3 | EM-B230E-NVMe-128G | 8 / 16 | 128 GiB | 0.411 | 300.03 |
| 4 | EM-I120E-NVMe | 8 / 16 | 64 GiB | 0.370 | 270.10 |

Reasoning. The offer must give hardware virtualization, enough RAM for the parallel
OpenBSD guests, and enough cores for llama.cpp in each guest.
`spec/inference.md` gives about 6 GB for one 4B model at Q4_K_M with an 8K context.
A guest of 8 GiB and 4 vCPU therefore holds one scenario.
Four parallel scenarios need 32 GiB of guests plus about 16 GiB for the host, which fits
64 GiB. Eight parallel scenarios need 64 GiB of guests and do not fit; that target needs
a 128 GiB offer.

**`spec/evaluation.md` does not state a parallelism target.
This answer assumes four.** The specification must fix the target, because the target
selects the offer.

Cost warnings. A Private Network option on this offer is priced at EUR 0.06 per hour in
the same recorded response, which is about EUR 43.80 per month and would take the total
close to the EUR 450 ceiling of `training.md`. Elastic Metal billing starts at creation
and stops only at deletion; a power-off saves nothing.

Rejected alternatives.

| Alternative | Reason |
| --- | --- |
| Dedibox | The Scaleway OpenTofu provider has no Dedibox resource. 155 resource pages, none matching. |
| Apple silicon | Scaleway installs macOS or experimental Asahi Linux only, and refuses a switch between OS families. |
| A virtual instance | Scaleway documents nested virtualization nowhere. See the risk in section 5.4. |

### 3.2 The zone and the region

**Answer: zone `fr-par-2` for every compute resource.
Region `fr-par` for every bucket.**

Reasoning, from `elastic-metal-datasheet.mdx` (validated 2026-06-16) and
`instances-datasheet.mdx` (validated 2026-04-09):

| Fact | Consequence |
| --- | --- |
| `H100-1-80G` and `L40S-1-48G` are in `fr-par-2` and `pl-waw-2`. | Both train offers are available. |
| Every `H100-SXM` shape is in `fr-par-2` only. | A stock-out fallback stays in the zone. |
| `fr-par-2` carries every Elastic Metal range. | Every fallback SKU is available. |
| The Glacier storage class exists in `fr-par` and `nl-ams` only. | An archive lane stays possible. |
| The provider acceptance tests default to `fr-par-2`. | The best-tested path. |

One zone also caps the quota exposure.
A quota is per Organization **per Availability Zone**, from
`organizations-and-projects/how-to/manage-quotas.mdx` (validated 2025-07-15), which
names the console field “Max quota per Availability Zone”.
A quota of 1 across `fr-par-2` and `pl-waw-2` permits two concurrent H100 instances.

Cost. Unknown, and this is the largest unpriced item in the project.
No reachable source states whether traffic between an instance and a bucket in the same
region is free or is billed as egress.
The corpus downloads at each training boot, and the checkpoints upload each epoch.
See section 7.

### 3.3 The rebuild schedule

**Answer: reinstall in place, on the first day of each month, at 03:00 UTC. The cron
expression is `0 3 1 * *`.**

Reinstall, not destroy.
`elastic-metal/how-to/reinstall-server.mdx` (validated 2025-08-19) and the provider
argument `reinstall_on_config_changes` keep the physical machine, the static public
IPv4, and the hourly billing period.
A destroy returns the machine to stock, and stock moves: eight `fr-par-2` offers
reported `stock: empty` on 2026-06-11, and three were empty in all three recorded
snapshots.

Period. Monthly matches the purpose in line 46, which is to stop drift.
Weekly would interrupt a training campaign or an evaluation sweep for no extra benefit.
The first day of the month aligns the rebuild with the billing period.

Cost. A reinstall keeps the server allocated, so hourly billing continues through the
window. Delivery of a machine takes a few minutes and an OS installation takes up to one
hour (`elastic-metal/faq.mdx`, validated 2025-09-24). The rebuild is therefore an outage
of up to one hour, and it wipes the disk.
Nothing in the specification says what the host re-pulls afterwards.

Gates. A reinstall must not start unless each of these passes.

| Gate | Check |
| --- | --- |
| No training in flight | `just infra-status` reports no live train stack. |
| No agent session in flight | No `dev-busy` marker object exists in the artifacts bucket. |
| No unsaved work | `git status --porcelain` is empty in each clone on the host. |
| The corpus is durable | The local corpus digest equals the digest in the corpus bucket. |
| Spend is under the cap | The consumption check reports below 100 percent. |

After the reinstall, the workflow must run `just check`, boot one OpenBSD guest under
KVM, and generate one token with llama.cpp.
A failure must fail the workflow.

### 3.4 The machine-checkable definition of “idle”

**Answer: a heartbeat object with conditional-write claim, plus an expiry tag.**

The training driver writes a heartbeat object every 60 seconds, on a timer that is
independent of checkpointing.
The object holds the run identifier, the server identifier, the phase, and the write
time. The driver claims the stack once at start, with an `If-None-Match: *` conditional
write against a separate owner object.
A second run fails the claim and must not start.

Conditional writes are generally available.
Source: `object-storage/api-cli/using-conditional-writes.mdx` (validated 2026-07-03),
and the Scaleway changelog entry of 2026-05-26.

A train stack is idle when each of these is true.

| Test | Value |
| --- | --- |
| The stack has a server tagged `ttx:lifecycle=ephemeral`. | true |
| The server is older than 20 minutes. | true |
| The heartbeat object is absent, or its write time is older than 20 minutes. | true |

The watchdog destroys the stack when the stack is idle, or when the current time passes
the `ttx:expires` tag, whichever comes first.
The expiry tag is the backstop for a hung run that keeps writing heartbeats.

Why a timer and not a checkpoint.
`training.md` line 53 synchronizes a checkpoint after each epoch.
An epoch can exceed 20 minutes.
A heartbeat tied to checkpointing would therefore make the watchdog destroy a live run.
A 60-second timer tolerates 19 consecutive missed writes before the threshold.

Cost. A 10-minute watchdog cadence with a 20-minute threshold wastes at most 30 minutes
of GPU time after a crash.
A crash on a Friday evening with no watchdog costs 60 hours.

## 4. Additions

The specification must gain these items.
Each is absent today.

1. **A region and zone rule.** No specification file names a region or a zone.
2. **A named Project.** IAM scopes to a Project, and the specification names none.
3. **Per-Organization quotas**, as the first guardrail, with the per-zone caveat.
4. **A lane boundary in storage.** D6 is absolute, and the storage layer enforces
   nothing. The eval/RAG corpus needs its own bucket, and no bucket may be public.
5. **Version pins.** OpenTofu 1.11 or later, the provider at `~> 2.80`, and a committed
   `.terraform.lock.hcl` in each stack.
6. **A tag vocabulary.** The provider has no `default_tags`. Instance tags are a list of
   strings; bucket tags are a map.
   The watchdog needs a tag to find its targets.
7. **An SSH key rule.** `ssh_key_ids` is required on a metal server, a change forces a
   reinstall, rescue mode authenticates with the registered keys, and the agents need a
   key to reach the GPU instance.
   No specification file mentions SSH keys.
8. **An execution channel.** `just train cpt` runs “on the instance”, and no document
   says how a recipe reaches the instance.
   D8 requires a deterministic entry point.
9. **A teardown order and an orphan sweep.** A cancelled apply can create a billed
   resource that never enters state.
10. **A state recovery procedure**, including `tofu force-unlock`, which the new lock
    makes necessary.
11. **Nine more `just` recipes.** The current `justfile` has four recipes and none for
    infrastructure, so `just check` cannot reproduce the CI gate it claims to reproduce.
12. **A list of human prerequisites**: identity validation, the quota tickets, the
    Organization security settings, and the GitHub environment policies.
13. **An OpenBSD image artifact**, with a producer and a store.
    `agents.md` requires a bootable OpenBSD qemu image on a host that holds no durable
    state, and no document produces it.

## 5. Risks

### 5.1 Elastic Metal stock

A scheduled destroy of the development host can leave the project with no host.
Three recorded `fr-par-2` catalogue snapshots (2025-07-23, 2026-04-07, 2026-06-11) show
eight offers empty in the latest snapshot, three empty in all three, and about eleven
that moved between states.
`elastic-metal-stock-levels.mdx` (validated 2025-09-09) documents `low` as five machines
or fewer.

Control: reinstall in place.
Gate any genuine re-order on a stock pre-check and on human approval.
Note that the stock value is read at plan time and can go stale before apply, so the
pre-check narrows the race and does not remove it.

### 5.2 The state file holds live credentials

`scaleway_iam_api_key` exports `secret_key` as an attribute, so a managed key writes the
credential into the state file.
The state file lives in an Object Storage bucket.
IAM cannot scope to a bucket, so any credential with Object Storage rights in the
Project reaches the state bucket.
A compromised training instance therefore reads the pipeline credential.

Four controls exist and they are complementary, not alternative:

1. Create the operator keys outside OpenTofu.
2. Put the state bucket in its own Project.
3. Put a bucket policy on the state bucket that names every principal that needs it.
4. Turn on OpenTofu state encryption.

Control 4 is the most direct and the least examined.
The OpenTofu encryption page could not be read from this environment, so the
key-provider list and the environment variable name are UNVERIFIED. Read the page before
you write the block.

Warning on control 3. A bucket policy holds one policy per bucket, a new policy
overwrites the old one, and version `2023-04-17` ignores a Deny statement
(`object-storage/api-cli/bucket-policy.mdx`, validated 2025-07-30). A single-principal
Allow locks every other principal out, including the pipeline.

### 5.3 The spend cap is soft

Nothing in Scaleway stops spend.
The budget notifies.
The billing alerts notify.
The pre-apply consumption check is pipeline code, and it is a level check that says
nothing about the money the apply is about to commit.
The idle watchdog is a scheduled GitHub job, which GitHub delays under load and, for a
public repository, disables after 60 days with no new commit.

Counting honestly, of the five guardrails in line 108, only the IAM policies are a
platform control, and they cannot express the bucket scoping the same section assumes.
The one real hard control is the per-Organization quota, which the specification does
not mention.

Arithmetic. `training.md` gives EUR 2.73 per hour for `H100-1-80G`, and that price is
UNVERIFIED. If it holds, one forgotten instance costs EUR 1,992.90 in a 730-hour month
and passes EUR 1,500 after 22.9 days.
The recurring table of `training.md` tops out at EUR 1,300 before tax, which is 87
percent of the cap, so the 50 and 75 percent alerts fire in normal operation.
An alert that fires normally gets ignored.

### 5.4 The bare-metal premise is untested

The specification gives two reasons for Elastic Metal.
The performance reason contradicts `evaluation.md` lines 57-58, which forbid a published
number from an amd64 server.
The virtualization reason rests on documentation silence: `rg -i nested` over the whole
corpus returns no relevant match, so Scaleway neither confirms nor denies nested
virtualization on a virtual instance.

The price argument for metal is also inverted by the evidence.
A recorded instance catalogue for `fr-par-1`, dated 2026-06-23, gives `GP1-M` at EUR
0.38352 per hour and EUR 279.97 per month for 16 vCPU and 64 GiB. `EM-B430E-NVMe` costs
EUR 400.04 for a 730-hour month at the same memory size.
Bare metal is 43 percent more expensive at matched specification, not cheaper.

Nobody ran `kvm-ok` on a Scaleway virtual instance, and nobody confirmed `/dev/kvm` on
the recommended EPYC 4545P. The Proxmox argument for KVM on this SKU fails, because
`EM-B430E-NVMe` does not accept the Proxmox image.
One hour of hourly billing settles the question.

### 5.5 The licensing lane has no storage boundary

D6 makes the lane rule absolute and says the enforcement is mechanical.
At the storage layer the enforcement is nothing.
One corpus bucket holds both lanes.
No rule keeps eval/RAG raw text out of the artifacts bucket, which holds published
releases. No bucket policy and no public-access rule exist.
A wrong prefix, a wrong `force_destroy`, or a mis-scoped policy becomes a licensing
incident, not an outage.

### 5.6 Vendor support and OpenBSD

Scaleway states twice that a custom image carries no support: in the custom-image
tutorial and in the iPXE Error 500 troubleshooting page (validated 2025-12-05). Every
OpenBSD host on Scaleway is therefore the project’s own outage.
No `risks.md` entry covers this, nor the H100 quota gate, nor the stock risk, nor
credentials in state.

### 5.7 The QEMU regression

QEMU issue 2644 records an OpenBSD 7.5 guest aborting QEMU on a `virtio-pci` assertion,
after commit `ffa8a3e3b2e6ff017113b98d500d6a9e05b1560a` of 2024-09-03. The assertion is
still present in QEMU master, read on 2026-08-02. The fix status is UNVERIFIED, and the
report is one guest on one host, so the generality is unproven.
The development host pins no qemu version and runs no guest-boot smoke test, and line 46
schedules exactly the rebuild that would pull in a breaking qemu.

## 6. Decision pressure

Each item below needs human approval before any plan adopts it.
The proposed specification is written to the decisions as they stand.

### D9 — three of four sentences are threatened

1. “The guardrails are platform controls, not conventions.”
   Two of the four named guardrails do not enforce.
   The budget and its alerts notify.
   The consumption check is pipeline code.
   A human must decide whether to amend the sentence, or to add the per-Organization
   quota as the named hard control, or both.
2. “CI … runs `tofu plan` and `tofu apply` for every stack.”
   “Every stack” includes `infra/persistent`, which declares IAM. That forces IAM
   administration onto the CI credential.
   Three research dimensions each proposed a fix, and each fix contradicts D9’s single
   “dedicated pipeline IAM application”.
   A human must decide between: keep D9 and accept that the CI credential can widen its
   own scope; or amend D9 to permit a separate, human-gated credential for
   `infra/persistent`; or amend D9 to permit a read-only plan credential separate from
   the apply credential.
3. “The pipeline runs from CI, without an operator in the loop.”
   Four one-time human acts block the first run: the H100 quota ticket, identity
   validation, the Organization security settings, and Project creation.
   A human must decide whether these are prerequisites outside D9, or an amendment to
   it.

### D3 — availability, not fitness

`H100-1-80G` remains the right technical choice.
It gives about 4.2 times the FP16 tensor-core throughput of the `L40S-1-48G` (1513
against 362 TFLOPS, `gpu/reference-content/choosing-gpu-instance-type.mdx`, validated
2025-10-28), and 80 GB holds the Qwen3-32B teacher at BF16, which 48 GB cannot.

What is threatened is availability, not fitness: no quota by default, constrained PCIe
supply with Scaleway recommending an SXM successor, and no verifiable price.
One research dimension recommended defaulting to `L40S-1-48G`; that would contradict D3
and also contradicts the same dimension’s own finding that the L40S cannot host the
teacher. Do not adopt it.
The proposed specification keeps the H100 default and records the quota grant as a
prerequisite.

A human must decide one point: the fallback catalogue was analysed against the
datasheet, which is not a complete offer list.
The quota table lists `H100-SXM-1-80G`, which the datasheet omits.
Redo the fallback analysis against `scw instance server-type list` before you fix a
fallback in the specification.

### D7 — one addition

D7 fixes OpenTofu. Two consequences are unrecorded.
The provider ships 25 `action` resources and 32 list resources that only Terraform
supports, so a copied example will not validate.
And ephemeral resources and write-only arguments need OpenTofu 1.11 or later, while no
specification file pins any version.
A human must approve a minimum version in D7, or accept the pin in `infrastructure.md`
alone.

### D6 — an enforcement gap, not a conflict

D6 needs no change. The storage layer must gain the lane boundary that D6 already
requires. The proposed specification adds a fourth bucket.
That changes “the three project buckets” in `agents.md` and in `infrastructure.md`, so
the two files must change together.

### D2 — an indirect consequence

No Scaleway offer can host an accelerated OpenBSD/arm64 guest.
All 41 non-Labs Elastic Metal offers are x64, and one Labs offer is riscv.
The agentic suite therefore grades amd64 guests only, while D2 targets arm64. An
arm64-only harness fault escapes the suite.
`evaluation.md` has the hardware-profile mechanism and does not use it.
A human must decide whether to accept the gap, or to fund arm64 hardware.

## 7. Open questions

Order is by cost of leaving it open.

| # | Question | How to close it |
| --- | --- | --- |
| 1 | Is traffic between an instance and a bucket in the same region free, or billed as egress? | Read the Scaleway pricing page for Object Storage, or run one measured transfer and read the invoice line. This is the largest unpriced item in the project. |
| 2 | Does a Scaleway virtual instance expose `/dev/kvm`? | Create one `GP1-M`, run `kvm-ok`, boot one OpenBSD guest. One hour of hourly billing. It decides whether `infra/dev` needs metal at all. |
| 3 | What are the current prices, after 2026-06-01, of `H100-1-80G`, `L40S-1-48G`, the flexible IPv4, `sbs_5k` block storage, and Object Storage per GB-month? | Read the console, or call the Billing or Product Catalog API with a credential. Every page was blocked from the research environment. |
| 4 | How does the training instance get its Object Storage credential? | Three proposed mechanisms each fail. A Scaleway instance has no metadata IAM identity, so there is no bootstrap identity. Design work, not research. |
| 5 | What lead time does a Scaleway H100 quota grant need, and does it apply per Organization or per Project? | Open the Support ticket now. It gates the first campaign. |
| 6 | What is the token count of the redistributable-clean corpus? | Measure it and record it in `corpus.md`. The whole GPU-hour budget rests on it. |
| 7 | Is the repository public or private? | Ask a human. It gates the fork pull-request risk, the 60-day schedule rule, and the self-hosted runner decision. |
| 8 | What is the exact marketplace label of Ubuntu Noble GPU OS 13? | `scw marketplace image list`. |
| 9 | What parallelism target does the agentic suite need? | Fix it in `evaluation.md`. It selects the Elastic Metal offer. |
| 10 | Does `H100-SXM-1-80G` exist as an orderable offer? | `scw instance server-type list zone=fr-par-2`. The quota page lists it; the datasheet does not. |
| 11 | What is the Elastic Metal quota for `EM-B430E-NVMe`? | The quota page has not been updated for the EPYC 4000 Beryllium offers. Read the console. The offer object exposes `quota_name`, for example `EM_B430E_NVMe`. |
| 12 | Is QEMU issue 2644 fixed, and in which release? | Read the issue. It decides the qemu pin. |
| 13 | Do the OpenTofu encryption key providers work as described? | Read `opentofu.org/docs/language/state/encryption/`. The current description is UNVERIFIED. |
| 14 | Is `scaleway_billing_budget` a singleton per Organization? | The API returns a list. Test a second create, or import an existing budget before the first apply. |
| 15 | Does the Product Catalog API need authentication? | Call it. The SDK constructs it with an authenticated client, which points against the no-auth claim. |
| 16 | Is Standard One Zone available in all regions? | The Scaleway docs and the provider docs disagree. Read the current pricing page. |
| 17 | Do the B130E, B230E, B330E, and B430E offers have KVM-over-IP? | The install page says no; the API returns a “Remote Access” option. Read the offer object. |

## 8. Sources

### Project files

- `/home/user/FuguTTX/spec/infrastructure.md`
- `/home/user/FuguTTX/spec/decisions.md`
- `/home/user/FuguTTX/spec/training.md`
- `/home/user/FuguTTX/spec/agents.md`
- `/home/user/FuguTTX/spec/evaluation.md`
- `/home/user/FuguTTX/spec/repository.md`
- `/home/user/FuguTTX/spec/risks.md`
- `/home/user/FuguTTX/spec/corpus.md`
- `/home/user/FuguTTX/spec/inference.md`
- `/home/user/FuguTTX/justfile`

### Scaleway documentation corpus

Root: `scratchpad/docs-content`. Validation dates are the page front matter.

- `pages/instances/reference-content/instances-datasheet.mdx` (2026-04-09)
- `pages/instances/reference-content/images-and-instantapps.mdx` (2025-07-01)
- `pages/instances/reference-content/understanding-instance-pricing.mdx` (2025-08-19)
- `pages/instances/reference-content/identify-devices.mdx` (2025-10-01)
- `pages/instances/reference-content/migrating-vms-vmware-scaleway.mdx` (2025-12-09)
- `pages/instances/how-to/use-serial-console.mdx` (2025-09-11)
- `pages/instances/how-to/snapshot-import-export-feature.mdx` (2025-06-02)
- `pages/instances/faq.mdx` (2025-12-19)
- `pages/gpu/reference-content/choosing-gpu-instance-type.mdx` (2025-10-28)
- `pages/gpu/reference-content/migration-h100.mdx` (2025-11-04)
- `pages/gpu/reference-content/gpu-instances-bandwidth-overview.mdx` (2025-11-18)
- `pages/gpu/reference-content/docker-images.mdx` (2025-07-28, stale)
- `pages/gpu/how-to/use-scratch-storage-h100-instances.mdx` (2025-12-04)
- `pages/gpu/how-to/use-preinstalled-env.mdx` (2025-07-21)
- `pages/gpu/how-to/create-manage-gpu-instance.mdx` (2025-09-17)
- `pages/gpu/troubleshooting/updating-gpu-instance-with-cloud-init.mdx` (2025-10-28)
- `pages/elastic-metal/reference-content/elastic-metal-datasheet.mdx` (2026-06-16)
- `pages/elastic-metal/reference-content/elastic-metal-stock-levels.mdx` (2025-09-09)
- `pages/elastic-metal/reference-content/elastic-metal-networking.mdx` (2025-06-03)
- `pages/elastic-metal/faq.mdx` (2025-09-24)
- `pages/elastic-metal/concepts.mdx` (2025-11-03)
- `pages/elastic-metal/how-to/install-server.mdx` (2025-08-27)
- `pages/elastic-metal/how-to/reinstall-server.mdx` (2025-08-19)
- `pages/elastic-metal/how-to/use-rescue-mode.mdx` (2025-08-27)
- `pages/elastic-metal/how-to/activate-remote-access.mdx` (2025-07-16)
- `pages/elastic-metal/how-to/change-billing-period.mdx` (2025-09-17)
- `pages/elastic-metal/how-to/get-use-loyalty-reward.mdx`
- `pages/elastic-metal/api-cli/elastic-metal-with-cli.mdx` (2025-07-15)
- `pages/elastic-metal/troubleshooting/troubleshoot-error-500-on-boot.mdx` (2025-12-05)
- `pages/elastic-metal/troubleshooting/cant-install-from-virtualmedia.mdx` (2025-10-02)
- `pages/object-storage/faq.mdx` (2025-12-19)
- `pages/object-storage/concepts.mdx` (2025-06-09)
- `pages/object-storage/api-cli/using-conditional-writes.mdx` (2026-07-03)
- `pages/object-storage/api-cli/bucket-policy.mdx` (2025-07-30)
- `pages/object-storage/api-cli/lifecycle-rules-api.mdx` (2026-03-31)
- `pages/object-storage/api-cli/combining-iam-and-object-storage.mdx` (2025-06-12)
- `pages/object-storage/api-cli/object-operations.mdx`
- `pages/object-storage/how-to/use-bucket-versioning.mdx` (2026-05-20)
- `pages/object-storage/how-to/use-object-lock.mdx` (2026-05-21)
- `pages/object-storage/how-to/use-obj-stor-with-private-networks.mdx` (2025-08-11)
- `pages/object-storage/reference-content/optimize-object-storage-performance.mdx`
  (2025-09-02)
- `pages/object-storage/reference-content/s3-iam-permissions-equivalence.mdx` (no date)
- `pages/iam/reference-content/permission-sets.mdx` (2026-03-20)
- `pages/iam/reference-content/policy.mdx` (2025-10-29)
- `pages/iam/reference-content/supported-products-resource-level.mdx` (2026-07-13)
- `pages/iam/reference-content/understanding-request-level-conditions.mdx` (2026-07-13)
- `pages/iam/concepts.mdx` (2025-10-29)
- `pages/iam/how-to/create-api-keys.mdx` (2025-07-15)
- `pages/iam/how-to/set-credentials-maximum-duration.mdx` (2026-01-05)
- `pages/iam/how-to/set-up-identity-federation.mdx` (2025-11-24)
- `pages/iam/api-cli/using-api-key-object-storage.mdx` (2025-06-09)
- `pages/iam/faq.mdx` (2025-12-19)
- `pages/billing/how-to/use-billing-alerts.mdx` (2025-09-03)
- `pages/billing/api-cli/retrieve-monthly-consumption.mdx` (2025-10-16)
- `pages/billing/concepts.mdx` (2025-08-25)
- `pages/billing/faq.mdx` (2025-09-09)
- `pages/billing/troubleshooting/fix-common-billing-issues.mdx`
- `pages/organizations-and-projects/additional-content/organization-quotas.mdx`
  (2025-10-29)
- `pages/organizations-and-projects/how-to/manage-quotas.mdx` (2025-07-15)
- `pages/audit-trail/faq.mdx` (2025-11-10)
- `pages/audit-trail/concepts.mdx` (2025-11-10)
- `pages/audit-trail/reference-content/adt-supported-endpoints.mdx` (2026-06-12)
- `pages/audit-trail/reference-content/resource-integration-with-adt.mdx` (2026-06-12)
- `pages/cockpit/reference-content/cockpit-product-integration.mdx` (2025-11-24)
- `pages/cockpit/reference-content/cockpit-pricing.mdx` (2026-01-20)
- `pages/apple-silicon/reference-content/apple-silicon-datasheet.mdx` (2026-02-03)
- `pages/apple-silicon/faq.mdx` (2026-02-18)
- `pages/apple-silicon/concepts.mdx`
- `pages/public-gateways/concepts.mdx` (2025-11-24)
- `pages/terraform/quickstart.mdx` (2026-02-03)
- `macros/object-storage/lifecycle-minimal-duration-message.mdx`
- `macros/storage/important-bucket-policy.mdx`
- `macros/developer-tools/scaleway-environment-variables.mdx` (2025-10-23)
- `macros/developer-tools/environment-variables-priority.mdx` (2025-10-23)
- `macros/audit-trail/instances-endpoints.mdx`, `elastic-metal-endpoints.mdx`
- `changelog/may2026/2026-05-26-object-storage-added-conditional-writes-and-terraform-s.mdx`
- `tutorials/create-openwrt-image-for-scaleway/index.mdx` (2025-06-09)
- `tutorials/install-kvm-elastic-metal/index.mdx` (2025-07-02, posted 2019-05-10)
- `tutorials/cicd-github-action-object-storage-sync/index.mdx` (2025-03-10)

### Scaleway OpenTofu provider

Root: `scratchpad/terraform-provider-scaleway`, HEAD `c90f1e2`, 2026-07-31, untagged.
Release v2.80.0 was published 2026-07-30, so the clone is at or ahead of v2.80.0.

- `docs/index.md`, `docs/guides/backend_guide.md`,
  `docs/guides/using-ephemeral-resources.md`,
  `docs/guides/using-write-only-arguments.md`
- `docs/resources/`: `instance_server.md`, `instance_ip.md`, `instance_volume.md`,
  `instance_snapshot.md`, `instance_image.md`, `instance_user_data.md`,
  `baremetal_server.md`, `flexible_ip.md`, `object_bucket.md`,
  `object_bucket_policy.md`, `iam_policy.md`, `iam_api_key.md`, `secret_version.md`,
  `billing_budget.md`, `billing_budget_alert.md`,
  `billing_budget_alert_notification.md`, `apple_silicon_server.md`
- `docs/data-sources/`: `baremetal_offer.md`, `baremetal_os.md`, `baremetal_option.md`,
  `instance_server_type.md`, `marketplace_image.md`, `iam_api_key.md`,
  `account_project.md`, `billing_consumptions.md`, `audit_trail_event.md`
- `docs/ephemeral-resources/`: `iam_api_key.md`, `secret_version.md`
- `internal/services/`: `baremetal/server.go`, `instance/server.go`,
  `instance/volume.go`, `instance/snapshot.go`, `instance/server_type_data_source.go`,
  `block/snapshot.go`, `object/bucket.go`, `billing/budget_resource.go`,
  `billing/consumption_data_source.go`, `meta/meta.go`
- Recorded API responses, used for prices and stock:
  `internal/services/baremetal/testdata/server-create-server-with-custom-install-config.cassette.yaml`
  (2026-06-11), `.../server-create-server-with-option.cassette.yaml` (2026-04-07),
  `.../data-source-offer-subscription-period-monthly.cassette.yaml` (2025-07-23),
  `internal/services/instance/testdata/server-minimal.cassette.yaml` (2026-06-23)

### OpenTofu

- `scratchpad/opentofu/website/docs/language/settings/backends/s3.mdx`, HEAD `1af92c8`
- `https://raw.githubusercontent.com/opentofu/opentofu/v1.10/CHANGELOG.md`
- `https://raw.githubusercontent.com/opentofu/opentofu/main/internal/backend/remote-state/s3/client.go`

### Other reachable sources

- `https://raw.githubusercontent.com/scaleway/scaleway-cli/master/docs/commands/object.md`
- `https://raw.githubusercontent.com/scaleway/scaleway-cli/master/docs/commands/baremetal.md`
- `https://raw.githubusercontent.com/scaleway/scaleway-cli/master/docs/commands/instance.md`
- `https://raw.githubusercontent.com/scaleway/scaleway-cli/master/docs/commands/billing.md`
- `https://raw.githubusercontent.com/scaleway/scaleway-sdk-go/master/scw/env.go`
- `https://raw.githubusercontent.com/scaleway/scaleway-sdk-go/master/api/billing/v2beta1/billing_sdk.go`
- `https://raw.githubusercontent.com/scaleway/scaleway-sdk-go/master/api/product_catalog/v2alpha1/product_catalog_sdk.go`
- `https://raw.githubusercontent.com/scaleway/action-scw/master/action.yml`
- `https://raw.githubusercontent.com/opentofu/setup-opentofu/main/README.md`
- `https://raw.githubusercontent.com/qemu/qemu/master/hw/virtio/virtio-pci.c`
- `https://gitlab.com/qemu-project/qemu/-/issues/2644`
- `https://github.com/scaleway/terraform-provider-scaleway/releases` (v2.80.0,
  2026-07-30)

### Blocked sources

The egress proxy returned HTTP 403 for every one of these.
Each price that depends on them is UNVERIFIED.

- `https://www.scaleway.com/en/pricing/gpu/`
- `https://www.scaleway.com/en/pricing/storage/`
- `https://www.scaleway.com/en/pricing/elastic-metal/`
- `https://www.scaleway.com/en/blog/a-transparent-update-on-scaleway-pricing/`
- `https://api.scaleway.com/` (all paths)
- `https://docs.github.com/` (all paths)
- Every third-party price aggregator tried: holori, spheron, computeprices, gpuperhour,
  getdeploying, pcr.cloud-mercato, gpufinder, agentxcloud
