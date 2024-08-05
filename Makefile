export PATH := .venv/bin:$(PATH)

.venv: pyproject.toml  ## Create the python virtual environment.
	/usr/bin/python3 -m venv --clear --upgrade-deps .venv
	pip install -e '.[dev]'

.PHONY: lint
lint: .venv  ## Lint the code base.
	ruff check --diff
	ruff format --diff

.PHONY: format
format: .venv  ## Format the code base.
	ruff check . --fix
	ruff format .

.PHONY: test
test: .venv  ## Run the tests,
	pytest