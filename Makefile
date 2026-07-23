# Convenience targets for the fff-profiles tooling. See scripts/extract.py.
PYTHON ?= python3
BUNDLE ?= ../PrusaSlicer_config_bundle.ini
MANIFEST ?= manifest.json

.PHONY: help test test-net list publish

help:
	@echo "Targets:"
	@echo "  make test      - run the offline test suite"
	@echo "  make test-net  - also run the pristine-Prusa-bundle smoke test (needs network)"
	@echo "  make list      - list presets in \$$BUNDLE (default: $(BUNDLE))"
	@echo "  make publish   - extract everything in \$$MANIFEST (default: $(MANIFEST)) into profiles/"

test:
	$(PYTHON) -m unittest discover -s tests -v

test-net:
	FFF_NET_TESTS=1 $(PYTHON) -m unittest discover -s tests -v

list:
	$(PYTHON) scripts/extract.py --source "$(BUNDLE)" --list

publish:
	$(PYTHON) scripts/extract.py --manifest "$(MANIFEST)"
