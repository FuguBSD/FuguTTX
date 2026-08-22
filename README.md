# FuguTTX

A small language model and agent for OpenBSD system administration.

FuguTTX makes TTX 1: a fine-tune of Qwen3-4B on OpenBSD knowledge. The model
operates locally and offline, on the CPU only, on OpenBSD in 16 GB of RAM or
less, through llama.cpp. The model and the harness together make the TTX agent.
The `ttx` harness — Perl 5, base modules plus the Fugu module allow-list of D7 —
operates the model in the boundaries of pledge, unveil, doas rules, and dry-run
gates.

The project is specification-first: the code follows the specification.

## Quick start

```sh
make setup       # install the development tools into .venv
make deps        # install the Fugu distribution and the Scaleway CLI
make check       # the full gate; run it before each commit
```

## Documentation

The specification in [spec/](spec/index.md) is the authoritative reference. Read
[spec/DECISIONS.md](spec/DECISIONS.md) before you make a plan. Research notes
live in `docs/research/`.

## Commands

```sh
make check       # lockfile + ruff + spec-check + ste-lint + test
make fmt         # format the Python code
make prettier    # Markdown formatting check
make help        # list the targets
```

## Commit scopes

`spec`, `docs`, `harness`, `corpus`, `train`, `eval`, `infra`, `ci`.

## License

ISC. See [LICENSE](LICENSE).
