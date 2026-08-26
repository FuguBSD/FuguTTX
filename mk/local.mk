# mk/local.mk: the consumer hook of this repository (MK-LOCAL).
# sync never touches this file. The Python targets live in the synced
# mk/python.mk of the python pack.

# Install the external dependencies from deps/<OS>.txt: the Fugu
# distribution with cpanm, and the Scaleway CLI into ~/.local/bin.
deps:
	scripts/deps runtime

.PHONY: deps
