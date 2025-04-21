.PHONY: default format mypy precommit ruff

default: format

format: precommit mypy

ruff:
	@ruff check . --fix
	@ruff format .

precommit:
	@pre-commit install
	@pre-commit run --all-file

mypy:
	@mypy .

test:
	@PYTHONPATH=./src pytest
