# Run the test suite against the installed development package.
test:
    uv run --locked --project python python -B -m unittest discover -s tests -v

# Check formatting, style and import order without modifying files.
lint:
    uv run --locked --project python ruff format --check --config python/pyproject.toml python/src tests tools
    uv run --locked --project python ruff check --config python/pyproject.toml python/src tests tools

# Apply Ruff fixes and formatting.
format:
    uv run --locked --project python ruff check --fix --config python/pyproject.toml python/src tests tools
    uv run --locked --project python ruff format --config python/pyproject.toml python/src tests tools

# Check types in the package and its tests.
type:
    uv run --locked --project python ty check --project python --extra-search-path python/src python/src tests tools

# Build the Python wheel and source distribution.
build:
    uv build python --no-sources --out-dir dist

# Check that the package, lockfile, skill and README agree on versions before a release.
check-versions:
    uv run --locked --project python python tools/check_versions.py

# Show the next release's changelog entry without changing files.
changelog:
    uv run --locked --project python towncrier build --config python/pyproject.toml --dir . --draft --version "$(uv version --project python --short)"

# Move the fragments into CHANGELOG.md under the version in python/pyproject.toml.
release-notes:
    uv run --locked --project python towncrier build --config python/pyproject.toml --dir . --yes --version "$(uv version --project python --short)"
