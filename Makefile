UV ?= uv
RUN := $(UV) run --frozen

.PHONY: lint ruff-check type-check fix ruff-fix test

lint: ruff-check type-check

ruff-check:
	$(RUN) ruff check .

type-check:
	$(RUN) mypy

fix: ruff-fix

ruff-fix:
	$(RUN) ruff check --fix .

test:
	$(RUN) pytest -v
