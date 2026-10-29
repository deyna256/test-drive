# Run the test suite against the installed development package.
test:
    uv run --locked --project python python -B -m unittest discover -s tests -v

# Check formatting, style and import order without modifying files.
lint:
    uv run --locked --project python ruff format --check --config python/pyproject.toml python/src tests
    uv run --locked --project python ruff check --config python/pyproject.toml python/src tests

# Apply Ruff fixes and formatting.
format:
    uv run --locked --project python ruff check --fix --config python/pyproject.toml python/src tests
    uv run --locked --project python ruff format --config python/pyproject.toml python/src tests

# Check types in the package and its tests.
type:
    uv run --locked --project python ty check --project python --extra-search-path python/src python/src tests

# Build the Python wheel and source distribution.
build:
    uv build python --no-sources --out-dir dist
