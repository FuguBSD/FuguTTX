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
make deps        # install gitleaks, the Fugu distribution and the CLI
make check       # lockfile + ruff + spec-check + ste-lint + gitleaks + test
make format-fix  # format the Python, Markdown, JSON and YAML
```

`make check` runs the Markdown format gate, and prettier runs through bunx. The
operator installs bun, for example from Homebrew. The manifest does not provide
it, because the format gate needs `bunx` before a target can run.

`make deps` verifies every download. The Fugu release carries a signed `SHA256`
manifest, and `deps/KEYS.txt` declares the release key of the organization by
URL and digest. `scripts/deps` fetches that key, holds it to the digest, and
verifies the manifest with signify(1). `deps/SHA256.txt` records the digest of
the Scaleway CLI and of gitleaks.

`make deps` also installs gitleaks, the tool of the secret gate. It installs the
`tool` environment before every other environment, so the gate tool is present
for each chain. The CI gate installs gitleaks with `make deps`, so one pin
serves the operator gate and the CI gate.

## Commit scopes

`spec`, `docs`, `harness`, `corpus`, `train`, `eval`, `infra`, `ci`.

## License

ISC. See [LICENSE](LICENSE).
