# FuguTTX

A small language model and agent for OpenBSD system administration.

FuguTTX makes TTX 1: a fine-tune of Qwen3-4B on OpenBSD knowledge. The model
operates locally and offline, on the CPU only, on OpenBSD in 16 GB of RAM or
less, through llama.cpp.

The model and the harness together make the TTX agent. The `ttx` harness — Perl
5 over Fugu — operates the model in the boundaries of pledge, unveil, doas
rules, and dry-run gates.

Two pilot projects rehearse the FuguTTX production pipeline at small scale:
[FuguCTX](https://github.com/FuguBSD/FuguCTX) and
[FuguSTX](https://github.com/FuguBSD/FuguSTX).

## Documentation

The project is specification-first: the specification in [spec/](spec/index.md)
is the authoritative reference. Research notes live in `docs/research/`.

## Commands

```sh
make setup       # install the development tools into .venv
make deps        # install the Fugu distribution and the Scaleway CLI
make check       # lockfile + ruff + spec-check + ste-lint + gitleaks + test
make format-fix  # format the Python, Markdown, JSON and YAML
```

`make check` runs the Markdown format gate, and prettier runs through bunx. The
operator installs bun and gitleaks, for example from Homebrew. No deps manifest
provides them.

## Commit scopes

`spec`, `docs`, `harness`, `corpus`, `train`, `eval`, `infra`, `ci`.

## License

ISC. See [LICENSE](LICENSE).
