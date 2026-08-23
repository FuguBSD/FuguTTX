# mk/local.mk: the consumer hook of this repository (MK-LOCAL).
# sync never touches this file. The Python targets live here until a
# second Python repository exists and a python pack forms.

CHECK_TARGETS		+= lock-py
LINT_TARGETS		+= lint-py
FORMAT_TARGETS		+= format-py
FORMAT_FIX_TARGETS	+= format-py-fix

# Install the development tools into .venv.
setup:
	uv sync

# Install the external dependencies from deps/<OS>.txt: the Fugu
# distribution with cpanm, and the Scaleway CLI into ~/.local/bin.
deps:
	scripts/deps runtime

lock-py:
	uv lock --check

lint-py:
	uv run ruff check .

format-py:
	uv run ruff format --check .

format-py-fix:
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: setup deps lock-py lint-py format-py format-py-fix
