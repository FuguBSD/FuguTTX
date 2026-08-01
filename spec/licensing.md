# Licensing and Release

## Licenses

| Component | License | Notes |
|---|---|---|
| Weights | **Apache 2.0** | Inherited cleanly from the base model ([base model](model.md)). A base that forces a restrictive derivative license is excluded by policy — for TTX 1 and for each variant. |
| Code (Python packages, Perl harness, OpenTofu) | **ISC** | The preferred OpenBSD license for new code (`/usr/share/misc/license.template`). Functionally equivalent to two-clause BSD. |
| Clean corpus | ISC/BSD, per source | Redistributable with attribution and notices. |

## Datasets

The clean corpus derives from ISC/BSD source code, mandoc (ISC) man pages, and the BSD-licensed FAQ/www. All of it is redistributable with attribution and notices. Published **dataset cards** document the source, the filters, and the license class of each component.

Mailing-list archives and undeadly.org are copyright of their authors. They live only in the eval/RAG corpus. They must not enter the training data. Their raw text must not be redistributed. The license tags of the pipeline enforce the lanes mechanically ([corpus](corpus.md)).

## Model cards

Each release has a model card. It documents the base model, the corpus composition, the training method, the evaluation results, and the known limitations.

## Release integrity

GGUF artifacts, manifests, and dataset cards are published with `signify(1)` signatures, under the pinned FuguTTX key. A human makes each signature. The signify private key is never available to development agents ([autonomous development](agents.md)).
