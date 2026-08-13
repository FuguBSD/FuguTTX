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
  This corpus is the CPT training data.
  It can ship inside the weights.
- **Eval/RAG corpus:** mailing lists, undeadly.org.
  This corpus is only for evaluation and optional local retrieval.

Commit logs are part of the trees.
The project distributes them with the code, in every checkout and every public mirror.
Thus the commit logs take the clean lane, with the code they describe.
This lane assignment is a recorded human licensing-lane decision
([autonomous development](agents.md)). List mail is different: the project does not
distribute the list archives, and each author keeps copyright.
Commit logs matter for CPT. Each message binds a change to its reason, in the idiom of
the project.

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
clean corpus, plus the [replay data](#replay-data).
A variant must not have its own CPT slice.

The SFT pass trains on synthetic traces, not on raw corpus text
([training](training.md)). The corpus still steers SFT: `ttx-synth` draws its scenarios
and its grounding facts from named corpus components.
The table maps each variant to its corpus use.

| Variant | CPT data | SFT scenario sources |
| --- | --- | --- |
| TTX 1 (operator) | Full clean corpus + replay data | Man pages and FAQ/www: `pf.conf` debug, package workflows, `sysctl` adjustment, `rcctl` service management |
| TTX 1 Port (candidate) | The shared CPT checkpoint | Ports tree and the `ports` commit logs: port updates, Makefile and PLIST work |
| TTX 1 Code (candidate) | The shared CPT checkpoint | Base source tree and the `src` commit logs: patches against the trees, regress runs |

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

## Pipeline stages

1. Fetch and synchronize the mirrors.
2. Extract and normalize: render the man pages with mandoc, convert HTML to text, walk
   the code trees.
3. Clean and chunk: remove license headers, remove near-duplicates.
4. Tag each chunk with its source and its license class.
5. Emit the two corpora.
