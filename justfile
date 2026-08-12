# FuguTTX task recipes. Run `just check` before each commit.

# List the recipes.
default:
    @just --list

# Install the development tools into .venv.
setup:
    uv sync

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
    just spec-check
