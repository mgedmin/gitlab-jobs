.PHONY: test
test:                           ##: run tests
	tox -p auto

.PHONY: coverage
coverage:                       ##: measure test coverage
	tox -e coverage


FILE_WITH_VERSION = gitlab_jobs.py
include release.mk
