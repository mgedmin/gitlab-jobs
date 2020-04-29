.PHONY: help
help:
	@echo "make test        run tests"
	@echo "make coverage    measure test coverage"
	@echo "make release     publish a new release to PyPI"

.PHONY: test check
test check:
	tox -p auto

.PHONY: coverage
coverage:
	tox -e coverage

PYTHON = python3
include release.mk
