# Corpus

## Sources

| Source | Format / access | License | Extraction method |
|---|---|---|---|
| Man pages | mdoc/man macros; `man.openbsd.org`; in the `src` and `ports` trees | ISC (mandoc) / per-file BSD-ISC | Render with `mandoc -T markdown` or `-T ascii` from the source tree |
| FAQ and website | HTML; the `www` repository | BSD | Clone `www.git`, convert HTML to text |
| Base source (C) | C; the `src` git mirror | ISC/BSD (ISC template preferred for new code) | Clone the git mirror, walk the tree |
| Ports infrastructure (Perl) | Perl and Makefiles; the `ports` git mirror | BSD/ISC | Clone `ports.git` |
| Commit logs | git log from the mirrors | Metadata; messages by committers | `git log` extraction |
| Mailing lists (misc, tech, ports, bugs) | mbox/HTML via marc.info, mail-archive.com | **Copyright of the authors** | Collect for the eval/RAG corpus only |
| undeadly.org articles | HTML | **Copyright of the authors** | Collect for the eval/RAG corpus only |

## License lanes

The pipeline emits two corpora:

- **Redistributable-clean corpus:** source, man pages, FAQ, www. This corpus is the CPT training data. It can ship inside the weights.
- **Eval/RAG corpus:** mailing lists, undeadly.org. This corpus is only for evaluation and optional local retrieval.

The lane rule is absolute. Author-copyrighted material must not enter the training data. Its raw text must not be redistributed. The undeadly.org footer reads verbatim: *"Articles and comments are copyright their respective authors, submission implies license to publish on this web site."*

A machine check enforces the rule. Each chunk has a license tag. A chunk with the eval/RAG tag must not reach a training manifest.

## Mirrors

Fetch from the official read-only git conversions at `github.com/openbsd/{src,ports,www,xenocara}`. The documented fallback is the Game of Trees Hub mirror: `ssh://anonymous@openbsd.gothub.org/{src,ports,www,xenocara}.git`, at most one commit behind CVS. Do not pull from CVS directly. CVS pulls are brittle.

## Pipeline stages

1. Fetch and synchronize the mirrors.
2. Extract and normalize: render the man pages with mandoc, convert HTML to text, walk the code trees.
3. Clean and chunk: remove license headers, remove near-duplicates.
4. Tag each chunk with its source and its license class.
5. Emit the two corpora.
