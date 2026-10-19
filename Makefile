# Convenience targets for the fff-profiles tooling. See scripts/extract.py.
PYTHON ?= python3
BUNDLE ?= ../PrusaSlicer_config_bundle.ini
MANIFEST ?= manifest.json

.PHONY: help test test-net validate validate-net check hooks status install pull list publish

help:
	@echo "Targets:"
	@echo "  make test      - run the offline test suite"
	@echo "  make test-net  - also run the pristine-Prusa-bundle smoke test (needs network)"
	@echo "  make validate  - check profiles, docs and repo hygiene"
	@echo "  make validate-net - also verify parent presets against Prusa's system bundle"
	@echo "  make check     - validate + test (what the pre-commit hook runs)"
	@echo "  make hooks     - enable the pre-commit hook in this clone"
	@echo "  make status    - show repo profiles that differ from PrusaSlicer's presets"
	@echo "  make install   - copy repo profiles into PrusaSlicer (quit PrusaSlicer first)"
	@echo "  make pull      - copy PrusaSlicer edits back into the repo profiles"
	@echo "  (legacy) make list / publish - extract from a master bundle via \$$MANIFEST"

test:
	$(PYTHON) -m unittest discover -s tests -v

test-net:
	FFF_NET_TESTS=1 $(PYTHON) -m unittest discover -s tests -v

validate:
	$(PYTHON) scripts/validate.py

validate-net:
	$(PYTHON) scripts/validate.py --check-system-presets

check: validate test

hooks:
	git config core.hooksPath .githooks
	@echo "pre-commit hook enabled (.githooks/pre-commit)"

status:
	$(PYTHON) scripts/sync.py status

install:
	$(PYTHON) scripts/sync.py install

pull:
	$(PYTHON) scripts/sync.py pull

list:
	$(PYTHON) scripts/extract.py --source "$(BUNDLE)" --list

publish:
	$(PYTHON) scripts/extract.py --manifest "$(MANIFEST)"
