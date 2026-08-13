# Corpus

## Sources

| Source | Format / access | License | Extraction method |
| --- | --- | --- | --- |
| Man pages | mdoc/man macros; `man.openbsd.org`; in the `src` and `ports` trees | ISC (mandoc) / per-file BSD-ISC | Render with `mandoc -T markdown` or `-T ascii` from the source tree |
| FAQ and website | HTML; the `www` repository | BSD | Clone `www.git`, convert HTML to text |
| Base source (C) | C; the `src` git mirror | ISC/BSD (ISC template preferred for new code) | Clone the git mirror, walk the tree |
| Ports infrastructure (Perl) | Perl and Makefiles; the `ports` git mirror | BSD/ISC | Clone `ports.git` |
| Commit logs (`src`, `ports`, `www`) | git log from the mirrors | Distributed with the trees, under the terms of the trees | `git log` extraction from each mirror |
| Mailing lists (misc, tech, ports, bugs) | mbox/HTML via marc.info, mail-archive.com | **Copyright of the authors** | Collect for the eval/RAG corpus only |
| undeadly.org articles | HTML | **Copyright of the authors** | Collect for the eval/RAG corpus only |

## License lanes

The pipeline emits two corpora:

- **Redistributable-clean corpus:** source, man pages, FAQ, www, commit logs.
  This corpus, plus its [synthetic augmentation](#synthetic-augmentation), is the CPT
  training data. It can ship inside the weights.
- **Eval/RAG corpus:** mailing lists, undeadly.org.
  This corpus is only for evaluation and optional local retrieval.

Commit logs are part of the trees.
The project distributes them with the code: every clone of a public mirror contains the
full log. Thus the commit logs take the clean lane, with the code they describe.
This lane assignment is a recorded human licensing-lane decision
([autonomous development](agents.md)). List mail is different: the project does not
distribute the list archives, and each author keeps copyright.
Commit logs matter for CPT. Each message binds a change to its reason, in the idiom of
the project. Each commit-log chunk keeps the tree name, the commit id, the date, and the
committer. Thus attribution travels with the text, and the pipeline can select the logs
of one tree.

The lane rule is absolute.
Author-copyrighted material must not enter the training data.
Its raw text must not be redistributed.
The undeadly.org footer reads verbatim: *“Articles and comments are copyright their
respective authors, submission implies license to publish on this web site.”*

A machine check enforces the rule.
Each chunk has a license tag.
A training manifest accepts only tags on a fixed allow list: the clean-lane tags and the
approved [replay](#replay-data) tags.
A chunk with the eval/RAG tag must not reach a training manifest.

## Synthetic augmentation

CPT carries the primary knowledge of the model (D4), and a model learns a fact only from
many diverse statements of that fact.
The raw corpus states most facts once.
Therefore the Qwen3-32B teacher rewrites the prose components of the clean corpus — the
man pages, the FAQ/www, and the commit logs — into paraphrases, question-and-answer
pairs, and fact summaries ([training](training.md#augmentation-generation)). The code
trees are not augmented.
Code trains in its raw form.

The grounded QA slice of the SFT pass ([training](training.md#sft-pass)) is generated in
the same way, and it follows the same rules.

These rules govern the augmentation:

- Each record derives from exactly one source chunk of the clean corpus.
  Each record keeps the chunk id and the license tag of its source, plus a synthetic
  marker. Thus provenance travels with the text, and the manifest check applies.
- The eval/RAG corpus must not seed a record.
  The lane rule applies to derived text.
- The held-out perplexity slice must not seed a record
  ([evaluation](evaluation.md#domain-knowledge)).
- An evaluation item must not enter a training manifest.
  A near-duplicate check compares the augmentation and the grounded QA slice against the
  OpenBSD QA set, and it drops each match from the training data.
- Qwen3-32B has an Apache 2.0 license, with no restriction on its output.
  Thus each record shares the clean lane of its source chunk.
- The augmentation set is a training source.
  It gets a dataset card ([licensing](licensing.md)), and its lane assignment is a
  recorded human licensing-lane decision ([autonomous development](agents.md)).

## Replay data

The CPT pass mixes in general-domain replay data against catastrophic forgetting
([training](training.md)). Replay data is third-party text, so it needs its own rules:

- Each replay source must have a documented open license that permits training use and
  redistribution of the text.
  The ODC-By licensed FineWeb-Edu sample is the leading candidate.
  Confirm the license and the version before use.
- Each replay chunk carries its own license tag, like each corpus chunk.
- Each replay source gets a dataset card, like each corpus component
  ([licensing](licensing.md)).
- The addition of a replay source is a licensing-lane change.
  A human approves it ([autonomous development](agents.md)).

## Corpus use per variant

One CPT run serves the whole family.
Each variant is an SFT overlay on the CPT checkpoint of TTX 1 (D5,
[variants](variants.md)). Thus the CPT data is the same for every variant: the full
clean corpus, its [synthetic augmentation](#synthetic-augmentation), plus the
[replay data](#replay-data).
A variant must not have its own CPT slice.

The SFT pass trains on synthetic traces and the grounded QA slice, not on raw corpus
text ([training](training.md)). The corpus still steers SFT: `ttx-synth` draws its
scenarios and its grounding facts from named corpus components.
The table maps each variant to its scenario sources.

| Variant | SFT scenario sources |
| --- | --- |
| TTX 1 (operator) | Man pages and FAQ/www: `pf.conf` debug, package workflows, `sysctl` adjustment, `rcctl` service management |
| TTX 1 Port (candidate) | Ports tree, the `ports` commit logs, and the port-maintenance man pages (`ports(7)`, `bsd.port.mk(5)`): port updates, Makefile and PLIST work |
| TTX 1 Code (candidate) | Base source tree, the `src` commit logs, and `style(9)`: patches against the trees, regress runs |

A seed and an evaluation item must stay apart.
An item that seeds an SFT trace or a grounded QA item must not appear in an evaluation
suite ([evaluation](evaluation.md)). Without this split, a persona measurement grades
memory, and the promotion rule of D5 loses its meaning.

The eval/RAG corpus serves every variant in the same way: evaluation suites and optional
local retrieval. It must not train any variant.

## Mirrors

Fetch from the official read-only git conversions at
`github.com/openbsd/{src,ports,www}`. The documented fallback is the Game of Trees Hub
mirror: `ssh://anonymous@openbsd.gothub.org/{src,ports,www}.git`, at most one commit
behind CVS. Do not pull from CVS directly.
CVS pulls are brittle.
The sources table names each tree the pipeline uses.
Do not mirror a tree that no source row names.

A corpus build pins one commit per mirror.
The corpus manifest records each pinned commit id.
Thus each build is reproducible, and the dataset card names the exact tree state.

## Pipeline stages

1. Fetch and synchronize the mirrors, and pin one commit per mirror.
2. Extract and normalize: render the man pages with mandoc, convert HTML to text, walk
   the code trees, extract one record per commit from each log.
3. Clean and chunk: remove license headers, remove near-duplicates, drop each commit
   message below a documented length floor.
4. Tag each chunk with its source and its license class.
5. Emit the two corpora, and hold out a slice of the clean corpus for the perplexity
   suite ([evaluation](evaluation.md#domain-knowledge)). The held-out slice must not
   enter a training manifest, and it must not seed the
   [synthetic augmentation](#synthetic-augmentation).
