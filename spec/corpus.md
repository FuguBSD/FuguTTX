# Corpus

## Sources

| Source | Format / access | License | Extraction method |
| --- | --- | --- | --- |
| Man pages | mdoc/man macros; `man.openbsd.org`; in the `src` and `ports` trees | ISC (mandoc) / per-file BSD-ISC | Render with `mandoc -T markdown` or `-T ascii` from the source tree |
| FAQ and website | HTML; the `www` repository | BSD | Clone `www.git`, convert HTML to text |
| Base source (C) | C; the `src` git mirror | ISC/BSD (ISC template preferred for new code) | Clone the git mirror, walk the tree |
| Ports infrastructure (Perl) | Perl and Makefiles; the `ports` git mirror | BSD/ISC | Clone `ports.git` |
| Commit logs | git log from the mirrors | **Copyright of the committers** | `git log` extraction, for the eval/RAG corpus only |
| Mailing lists (misc, tech, ports, bugs) | mbox/HTML via marc.info, mail-archive.com | **Copyright of the authors** | Collect for the eval/RAG corpus only |
| undeadly.org articles | HTML | **Copyright of the authors** | Collect for the eval/RAG corpus only |

## License lanes

The pipeline emits two corpora:

- **Redistributable-clean corpus:** source, man pages, FAQ, www.
  This corpus is the CPT training data.
  It can ship inside the weights.
- **Eval/RAG corpus:** mailing lists, undeadly.org, commit logs.
  This corpus is only for evaluation and optional local retrieval.

Commit messages are prose by their committers, like list mail.
No committer granted a training license, so commit logs take the eval/RAG lane.

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
