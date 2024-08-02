set positional-arguments

_all:
    @just --list

# Test
test *ARGS:
    poetry run python -m pytest {{ARGS}}

# Test
test-cov *ARGS:
    poetry run python -m pytest --cov --cov-report=html {{ARGS}}

# Test debug
test-debug *ARGS:
    poetry run python -m debugpy --listen localhost:5678 --wait-for-client -m pytest {{ARGS}}

# Format
fmt:
    poetry run ruff check --select I --fix .
    poetry run ruff format .

# Format check
fmt-check:
    poetry run ruff format --check .

# Lint
lint:
    poetry run ruff check .

# Typecheck
tc:
    poetry run mypy --strict .

# Manage
manage *ARGS:
    @poetry run python manage.py "$@"

# Manage debug
manage-debug *ARGS:
    @poetry run python -m debugpy --listen localhost:5678 --wait-for-client manage.py {{ARGS}}