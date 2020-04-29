help:
	@echo "make test        run tests"
	@echo "make coverage    measure test coverage"

test:
	tox -p auto

coverage:
	tox -e coverage
