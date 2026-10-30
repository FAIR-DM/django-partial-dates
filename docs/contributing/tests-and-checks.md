# Run the tests and checks

Continuous integration runs everything on this page against a pull request. Run these commands from
the root of a clone, once the [development environment](development-environment.md) is installed.

## Run the tests

Run the whole suite.

```console
$ uv run pytest
```

Run one file or class while you work on it.

```console
$ uv run pytest tests/test_partial_date.py -x
```

The tests use SQLite unless you say otherwise. To run them on PostgreSQL, as continuous integration
also does, set `TEST_DATABASE` and the standard connection variables.

```console
$ TEST_DATABASE=postgresql PGDATABASE=partial_dates PGUSER=postgres PGPASSWORD=postgres PGHOST=localhost PGPORT=5432 uv run pytest
```

## Run the linters and hooks

```console
$ uv run pre-commit run --all-files
```

## Check the types and dependencies

```console
$ uv run mypy
$ uv run deptry .
```

## Build the package

```console
$ uv build
```

## Build the documentation

The documentation has its own dependency group. A page missing from the contents, or a link to a
page that does not exist, shows up as a warning in the output.

```console
$ uv run --group docs sphinx-build -E -b html docs docs/_build
```

Open `docs/_build/index.html` to read the result.
