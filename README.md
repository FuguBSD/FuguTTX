# FuguTTX

A small language model and agent for OpenBSD system administration. FuguTTX
makes TTX 1: a fine-tune of Qwen3-4B on OpenBSD knowledge. The model operates
locally and offline, on the CPU only, on OpenBSD in 16 GB of RAM or less.

The model and the harness together make the TTX agent. The `ttx` harness, Perl 5
over Fugu, operates the model inside pledge, unveil, doas rules, and dry-run
gates. [FuguCTX](https://github.com/FuguBSD/FuguCTX) and
[FuguSTX](https://github.com/FuguBSD/FuguSTX) rehearse the pipeline at small
scale.

## Commands

```sh
make setup       # install the development tools into .venv
make deps        # install gitleaks, the Fugu distribution and the Scaleway CLI
make check       # run every gate; run it before each commit
make test        # run the test suite
make format-fix  # fix the Python, Markdown, JSON and YAML formatting
```
