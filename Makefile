PYTHON ?= python3
TYPECHECK_PYTHON := $(shell $(PYTHON) -c 'import sys; print(sys.executable)')

test:
	$(PYTHON) -m pytest

lint:
	ruff check .

typecheck:
	ty check --python "$(TYPECHECK_PYTHON)"

build:
	$(PYTHON) -m build
