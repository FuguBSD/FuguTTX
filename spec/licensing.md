# Licensing and Release

<a id="lic-lic"></a>

## Licenses

| Component                                      | License                                                                | Notes                                                                                                                                                                       |
| ---------------------------------------------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Weights                                        | **Apache 2.0**                                                         | Inherited cleanly from the base model ([base model](model.md)). A base that forces a restrictive derivative license is excluded by policy — for TTX 1 and for each variant. |
| Code (Python packages, Perl harness, OpenTofu) | **ISC**                                                                | The preferred OpenBSD license for new code (`/usr/share/misc/license.template`). Functionally equivalent to two-clause BSD.                                                 |
| Clean corpus                                   | ISC/BSD, per source                                                    | Redistributable with attribution and notices.                                                                                                                               |
| Port run dependencies                          | p5-Fugu: **ISC**; llama.cpp: see [inference](inference.md#inf-runtime) | The port lists both as run dependencies ([harness](harness.md#hrn-pkg)).                                                                                                    |

<a id="lic-data"></a>

## Datasets

The clean corpus derives from ISC/BSD source code, mandoc (ISC) man pages, the
BSD-licensed FAQ/www, and the commit logs of those trees. The project
distributes the commit logs with the code, so the logs share its terms. All of
it is redistributable with attribution and notices. Published **dataset cards**
document the source, the filters, and the license class of each component. The
commit-log card also records the basis of its lane: the project distributes the
logs with the code, and a human approved the lane ([corpus](corpus.md)).

The synthetic augmentation is a training-data component like the others
([corpus](corpus.md#synthetic-augmentation)). Each record derives from one
clean-lane source chunk, and the Apache 2.0 teacher places no restriction on its
output. Its dataset card records the teacher model and version, the generation
method, the judge filter, and the human lane approval.

Mailing-list archives and undeadly.org are copyright of their authors. They live
only in the eval/RAG corpus. They must not enter the training data. Their raw
text must not be redistributed. The license tags of the pipeline enforce the
lanes mechanically ([corpus](corpus.md)).

<a id="lic-cards"></a>

## Model cards

Each release has a model card. It documents the base model, the corpus
composition, the training method, the evaluation results, and the known
limitations.

<a id="lic-release"></a>

## Release integrity

GGUF artifacts, manifests, and dataset cards are published with `signify(1)`
signatures, under the pinned FuguTTX key. A human makes each signature. The
signify private key is never available to development agents
([autonomous development](agents.md)).
