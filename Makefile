# FuguTTX task targets. Run `make check` before each commit.

.PHONY: help setup deps fmt spec-check check

# List the targets.
help:
	@awk '/^# / { c = substr($$0, 3) } /^[a-z][a-z-]*:/ { sub(/:.*/, ""); printf "  %-12s %s\n", $$0, c }' Makefile

# Install the development tools into .venv.
setup:
	uv sync

# Install the external dependencies from deps/<OS>.txt: the Fugu distribution
# with cpanm, and the Scaleway CLI into ~/.local/bin.
deps:
	scripts/deps runtime

# Format the Python code and the Markdown documents.
fmt:
	uv run ruff format .
	uv run ruff check --fix .
	uv run flowmark --auto .

# Verify the internal links, the anchors, and the index coverage of the documents.
spec-check:
	uv run python scripts/spec_check.py

# Verify the lockfile, the formats, and the lints. CI runs the same gate.
check:
	uv lock --check
	uv run ruff format --check .
	uv run ruff check .
	uv run flowmark --check --semantic --cleanups --smartquotes --ellipses .
	$(MAKE) spec-check
