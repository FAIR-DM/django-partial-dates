# Implementation Plan: Filtering, ordering and grouping partial dates in the database

**Branch**: `003-database-queries` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: `specs/003-database-queries/spec.md`, `research.md`

## Summary

One new module, `partial_dates/lookups.py`, holding the `year`, `month`, `day` and `start`
transforms and an `exact` lookup that lets a one-year filter use the index. `PartialDateField`
registers them. Range filters, `in`, and ordering already work through the field and gain tests.
The rest of the feature is the documentation: the package's first guide, whose examples and tables
are run by a test.

## Technical context

- **Language**: Python 3.12 and later. Django 5.2 LTS, 6.0 and 6.1
- **Dependencies**: none new
- **Testing**: pytest-django, against SQLite by default and PostgreSQL with
  `TEST_DATABASE=postgresql`
- **Constraints**: no stored value changes and no migration ships (Article XI). Same behaviour on
  both databases (FR-013)

## Constitution check

| Article | How the plan meets it |
|---|---|
| I Testing | Test-first per task. No test asserts wording. Tests that pass on their first run record the mutation that turns them red |
| II Simplicity | Four transforms and one lookup, on Django's documented extension points. Nothing for what the field already does |
| III Anti-abstraction | No base class. The three part transforms differ in one line and stay three classes |
| IV Integration-first | Every test goes through a model and a queryset |
| V Security | Values reach SQL as parameters. The SQL holds only literals of ours |
| VI Documentation | Guide, README, CHANGELOG. Examples are run by a test |
| VII Dependencies | None added |
| VIII i18n | No user-facing strings |
| IX Data model | No model ships. Indexing stays the developer's choice |
| X Cohesion | One class per lookup, the way Django shapes them |
| XI Storage | Nothing stored changes. `start` is derived when a query runs |
| XII Filters | Every filter has a result stated in the guide, and the boundary tests cover a value at each precision on both sides of each bound. Every lookup runs in the database on both supported databases |
| XIII Compatibility | Run on Django 5.2, 6.0 and 6.1 and on both databases before review |

No violations.

## Design

### `partial_dates/lookups.py`

| Class | Base | Members |
|---|---|---|
| `Year` | `Transform` | `lookup_name = "year"`, `output_field = IntegerField()`, `template = "CAST(SUBSTR(%(expressions)s, 1, 4) AS INTEGER)"` |
| `Month` | `Transform` | `lookup_name = "month"`, as `Year`, with `CAST(NULLIF(SUBSTR(%(expressions)s, 6, 2), '') AS INTEGER)` |
| `Day` | `Transform` | `lookup_name = "day"`, as `Year`, with `CAST(NULLIF(SUBSTR(%(expressions)s, 9, 2), '') AS INTEGER)` |
| `Start` | `Transform` | `lookup_name = "start"`, `output_field = DateField()`, `template = "CAST(SUBSTR(%(expressions)s \|\| '-01-01', 1, 10) AS DATE)"`, `as_sqlite` passing a template with no cast |
| `YearExact` | `Exact` | registered on `Year` with `@Year.register_lookup`. `as_sql` compares the column under the transform with `BETWEEN` and two bounds, `f"{year:04d}"` and `f"{year:04d}-99"`, when `rhs_is_direct_value()`, and otherwise defers to `Exact` |

The column under the transform is `self.lhs.lhs`, passed to `process_lhs`, as Django's `YearLookup`
does.

### `partial_dates/fields.py`

After the class:

```python
PartialDateField.register_lookup(Year)
PartialDateField.register_lookup(Month)
PartialDateField.register_lookup(Day)
PartialDateField.register_lookup(Start)
```

Nothing else changes.

### Test app

- `tests/models.py` gains `Sample`, `collected = PartialDateField(null=True, blank=True,
  db_index=True)`, with a `verbose_name` and `help_text`, the model the guide's examples use. The
  index lets the plan tests use the same rows.
- `tests/factories.py` gains `SampleFactory`, `tests/conftest.py` a fixture wrapping it, and
  `tests/test_factories.py` its test.
- `tests/migrations/0002_sample.py`, made with `makemigrations tests`.
- `pyproject.toml` conformance gains `tests/test_guide.py` under `non-mirror-paths`, because its
  subject is a page and not a module.

### Tests

`tests/test_lookups.py` mirrors `partial_dates/lookups.py`, `tests/test_fields.py` gains the filters
the field provides itself, and `tests/test_guide.py` reads the guide.

| Class | File | Covers |
|---|---|---|
| `TestYear` | `test_lookups.py` | US-1 1, 7, 8, 13; US-2 3, 4, 6 |
| `TestMonth` | `test_lookups.py` | US-1 2, 4, 5, 6, 7, 13, 14; US-2 3, 5, 6 |
| `TestDay` | `test_lookups.py` | US-1 3, 5, 6, 7; US-2 3, 5, 6; the `day=1` edge case |
| `TestYearIndex` | `test_lookups.py` | US-1 15 for `year`, FR-008 |
| `TestStart` | `test_lookups.py` | US-2 7–11, the `gt` of `1990-06` edge case |
| `TestBounds` | `test_fields.py` | US-1 9–14, parametrised over the two expected-results tables |
| `TestRangeIndex` | `test_fields.py` | US-1 15 for a range, FR-008 |
| `TestOrdering` | `test_fields.py` | US-2 1, 2, 12 and SC-004 |
| `TestQueryCount` | `test_lookups.py` | SC-005: one query for a filter, a grouping and an ordering, with one row and with several |
| `TestExamples` | `test_guide.py` | FR-017, SC-006: every `>>>` example in the guide runs and prints what it shows |
| `TestStatedResults` | `test_guide.py` | US-1 16, SC-002: each cell of the guide's result tables is what the filter returns |

Plan tests read `QuerySet.explain()`. A shared helper in `tests/conftest.py`, a fixture
`query_plan(queryset)`, returns the plan text and, on PostgreSQL, sets `SET LOCAL enable_seqscan =
off` first, so a small table cannot hide a missing index. The assertion is that the plan names an
index, and each test also asserts that the same filter without the index path does not, by
checking `month=6`, which reads the table.

US-1 scenario 19, US-2 scenario 15 and FR-013 are the whole suite run with and without
`TEST_DATABASE=postgresql`. Both runs go in the pull request.

SC-003 is one parametrised test in `TestStart`, over every value in the grid: `year`, `month`, `day`
and `start` from the database equal the attributes of the value read in Python.

## Documentation

- `docs/index.md`, the homepage, in the order `documentation.md` section 3 sets out.
- `docs/developer/index.md`, the guide's section page.
- `docs/developer/installation.md`, the core's installation in full.
- `docs/developer/querying.md`, titled "Querying". Opens with what the feature does, states the
  model and rows the examples use, then:
  - tasks, each a section titled with a verb: filter by year, month or day; find dates by precision;
    filter by a range; take in the whole of a month or year; add every uncertain date to a range;
    leave every uncertain date out of a range; find June of any year; order by the date; count by
    year, month and day; put dates on a date axis
  - the two result tables, each under its own section
  - closing explanation: why a bound is a position in the sort order, linking to ADR 0001; which
    of Django's text lookups the guide does not cover; which queries use an index
- `README.md`: *Status* updated, and a short *Querying* section linking to the guide by absolute
  URL.
- `CHANGELOG.md`: `[Unreleased]` → *Added*.
- `docs/ROADMAP.md`: R3's status line, as R1 and R2 read, at ready for review.

Each story writes its own part of `querying.md`: US-1 the page and everything about filters, US-2
ordering, grouping and `start`. The docs step passes at each story's exit because the page exists
from US-1 on.

## Project structure

```text
partial_dates/
├── fields.py                          registers the lookups
└── lookups.py                         new
tests/
├── models.py, factories.py            Sample
├── conftest.py, test_factories.py     fixtures, query_plan
├── migrations/0002_sample.py          new
├── test_fields.py                     TestBounds, TestRangeIndex, TestOrdering
├── test_lookups.py                    new
└── test_guide.py                      new
docs/
├── index.md                           new
└── developer/
    ├── index.md, installation.md      new
    └── querying.md                    new
pyproject.toml                         non-mirror path
README.md, CHANGELOG.md, docs/ROADMAP.md
```

## Stories and dispatch

Two stories, one dispatch group each, in order on the feature branch:

- US-1: the test model, `year`, `month`, `day`, the one-year filter, bounds, and the guide (T001–T006)
- US-2: ordering, selecting and grouping, `start`, and the rest of the guide (T007–T011)
