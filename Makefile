.PHONY: preflight suite story test lint typecheck

preflight:
	fde-lab preflight

suite:
	fde-lab run-suite

story:
	fde-lab run-story

test:
	pytest

lint:
	ruff check src tests scripts security

typecheck:
	mypy src
