# FuguTTX task targets. Run `make check` before each commit.

# Pin the version so that local runs and CI agree on formatting
PRETTIER = npx prettier@3.9.6

.PHONY: help setup deps fmt check prettier prettier-fix spec-check ste-lint test

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

# Format the Python code.
fmt:
	uv run ruff format .
	uv run ruff check --fix .

# Validate the specification and the plans.
spec-check:
	@scripts/spec-check

# Check the prose against the writing standard.
ste-lint:
	@scripts/ste-lint

# Run the workflow tests.
test:
	prove -l t/ci/*.t

# Verify the lockfile, the formats, the lints, and the documents. CI runs the same gate.
check:
	uv lock --check
	uv run ruff format --check .
	uv run ruff check .
	$(MAKE) spec-check ste-lint test

# Check the Markdown, JSON and YAML formatting.
prettier:
	@$(PRETTIER) --check --no-error-on-unmatched-pattern '**/*.md' '**/*.json' '**/*.yml' || { echo "Run 'make prettier-fix' to fix formatting"; exit 1; }

# Format the Markdown, JSON and YAML files.
prettier-fix:
	$(PRETTIER) --write --no-error-on-unmatched-pattern '**/*.md' '**/*.json' '**/*.yml'
