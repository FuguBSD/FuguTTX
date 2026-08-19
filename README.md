# FuguTTX

A small language model and agent for OpenBSD system administration.

FuguTTX makes TTX 1: a fine-tune of Qwen3-4B on OpenBSD knowledge.
The model operates locally and offline, on the CPU only, on OpenBSD in 16 GB of RAM or
less, through llama.cpp.
The model and the harness together make the TTX agent.
The `ttx` harness — Perl 5, base modules only — operates the model in the boundaries of
pledge, unveil, doas rules, and dry-run gates.

## Quick start

```sh
make setup
make check
```

The project is specification-first: the code follows the specification.

## Documentation

The specification in [spec/](spec/index.md) is the authoritative reference.
Read [spec/decisions.md](spec/decisions.md) before you make a plan.

## Development

See [CLAUDE.md](CLAUDE.md) for the development guide: the specification process and the
writing standard.

## License

ISC. See [LICENSE](LICENSE).
