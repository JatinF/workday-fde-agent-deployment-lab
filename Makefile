.PHONY: preflight suite test lint typecheck

preflight:
	fde-lab preflight

suite:
	fde-lab run-suite

test:
	pytest

lint:
	ruff check src tests scripts

typecheck:
	mypy src
