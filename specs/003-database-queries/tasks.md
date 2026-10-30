# Tasks: Filtering, ordering and grouping partial dates in the database

**Input**: `spec.md`, `plan.md`, `research.md` in `specs/003-database-queries/`

Every task is test-first: the test is written and seen to fail before the code. A test that passes
on its first run, because the field already behaves that way, records in its task's evidence the
change to the code that turns it red. No test asserts wording. No name starts with an underscore.

## Phase 1: User Story 1 — A developer filters partial dates, knowing which uncertain dates each filter includes (P1)

**Goal**: filter by year, month, day or a range in the database, and find in the guide exactly what
each filter includes.

**Independent test**: `uv run pytest tests/test_lookups.py tests/test_fields.py tests/test_guide.py`,
then the same with `TEST_DATABASE=postgresql` and the `PG*` variables set.

### Group 1

- [ ] T001 [US1] `Sample` in `tests/models.py` as `plan.md` describes, `SampleFactory`, a `sample`
  fixture, a test in `tests/test_factories.py`, and `tests/migrations/0002_sample.py` made by
  `makemigrations tests`. The existing parametrised test in `tests/test_models.py` covers its field
- [ ] T002 [US1] `Year`, `Month` and `Day` in `partial_dates/lookups.py`, registered in
  `partial_dates/fields.py`. Tests in `tests/test_lookups.py`, classes `TestYear`, `TestMonth`,
  `TestDay`: `year=1990`, `month=6` and `day=14` against `1990`, `1990-06`, `1990-06-14`, `1991` and
  an empty row (US-1 1–3, 13); `month__gte`, `month__in`, `year__range` (US-1 4); `month__isnull` and
  `day__isnull` both ways (US-1 5); `exclude(month=6)` and `exclude(day=14)` leave out dates with
  that part unknown, on `Sample` and on the required `Event.occurred` (US-1 6); an empty row is
  returned by `exclude` on a nullable field (US-1 14); `month=13`, `day=32`, `year=0`, `year=10000`
  find nothing and raise nothing (US-1 7); `year=1`, `year=990`, `year=9999` each find `0001`, `0990`,
  `9999-12-31` (US-1 8); `day=1` finds `1990-06-01` and not `1990-06` (edge case); two fields on
  `Record` are filtered independently (edge case)
- [ ] T003 [US1] `YearExact` in `partial_dates/lookups.py`, and the `query_plan` fixture in
  `tests/conftest.py`. Tests in `TestYearIndex`: the plan for `year=1990` on `Sample.collected` names
  an index, and for `month=6` does not (US-1 15, FR-008). The T002 year tests keep passing, and a
  test proves `year=F("other__year")` still compares on `Record`. Revert `YearExact` and watch the
  plan test go red
- [ ] T004 [US1] Tests in `tests/test_fields.py`, class `TestBounds`, parametrised from the two
  tables in `spec.md`, with each row and each lookup a case and the bound given both as a
  `PartialDate` and as its ISO form (US-1 9); a `range` mixing precisions and forms finds the same
  rows as `gte` and `lte`, and a reversed `range` finds nothing (US-1 10); `in` finds exact values
  only (US-1 11); `1990-6`, `datetime.date(1990, 1, 1)` and `1990` as an integer each raise
  `ValueError` through `gt`, `gte`, `lt`, `lte`, `range` and `in`, under
  `django_assert_num_queries(0)` (US-1 12); empty rows are not found, and `exclude` of a bound returns
  them (US-1 13, 14). Class `TestRangeIndex`: the plan for `gte` with `lte` names an index (US-1 15).
  No production code is expected. Record the mutation in the evidence
- [ ] T005 [US1] `docs/index.md`, `docs/developer/index.md`, `docs/developer/installation.md`, and
  the filtering half of `docs/developer/querying.md`, with its two result tables, the recipe for
  June of any year and the three recipes for the other rule (FR-014, FR-015, US-1 16–18). Tests in
  `tests/test_guide.py`: class `TestExamples` runs every `>>>` example in the fenced blocks with
  `doctest.DocTestParser` and `DocTestRunner`, on rows from a fixture, and fails on no examples
  found; class `TestStatedResults` reads each result table and asserts each cell against the filter
  it names (SC-002). `tests/test_guide.py` joins `non-mirror-paths` in `pyproject.toml`. `README.md`
  *Status* and a *Querying* section, `CHANGELOG.md` *Added*
- [ ] T006 [US1] `TestQueryCount` in `tests/test_lookups.py`: a `year` filter, a `month` filter and a
  range each run one query with one row and with several (SC-005). Then the whole suite with
  `TEST_DATABASE=postgresql` and the `PG*` variables set (US-1 19)

**Checkpoint**: a developer can filter by part and by range, on both databases, and the guide says
what each filter includes.

## Phase 2: User Story 2 — A developer orders and groups partial dates, for lists, drilldowns and chart axes (P2)

**Goal**: order, select and group in the database, and put dates on a date axis.

**Independent test**: the same commands as Phase 1.

### Group 1

- [ ] T007 [US2] Tests in `tests/test_fields.py`, class `TestOrdering`: ordering by the field gives
  the order `sorted()` gives, and `-field` the reverse, on values at each precision including
  `0001` and `9999-12-31` (US-2 1, SC-004); `nulls_first` and `nulls_last` put empty rows first and
  last (US-2 2); the plan for `order_by` on `Sample.collected` names an index (US-2 12, FR-012). No
  production code is expected. Record the mutation in the evidence
- [ ] T008 [US2] Tests in `TestYear`, `TestMonth`, `TestDay`: `values`, `values_list` and `annotate`
  give whole numbers equal to the value's parts, and `None` where unknown or empty (US-2 3);
  counts grouped by `year` include every row with a date (US-2 4); counts grouped by `year` and
  `month` keep year-only rows out of every month, and by `year`, `month` and `day` keep month-only
  rows out of every day (US-2 5); `order_by` on each part is numeric, with `nulls_last` where a part
  can be unknown (US-2 6). No production code is expected beyond T002. Record the mutation in the
  evidence
- [ ] T009 [US2] `Start` in `partial_dates/lookups.py`, registered in `partial_dates/fields.py`. Tests
  in `TestStart`: `values`, `values_list` and `annotate` give a `datetime.date` equal to the value's
  `start`, and `None` for an empty row (US-2 7); grouping by `start` counts `1990`, `1990-01` and
  `1990-01-01` on one day (US-2 8); `exact`, `gt`, `gte`, `lt`, `lte` and `range` with real dates
  (US-2 9); `order_by("collected__start", "collected")` gives a stable order (US-2 10); `0001`,
  `9999-12-31`, `2000-02-29` (US-2 11); `1990-06` and `1990-06-01` share a `start` and stay different
  values (edge case). One test over the whole grid for SC-003
- [ ] T010 [US2] The rest of `docs/developer/querying.md`: what ordering, grouping and `start` do at
  each precision, where each database sorts an empty row and how to say which, and the recipes for
  a date axis and a drilldown, with its closing explanation sections (FR-016, US-2 13, 14). Every
  example runs under `TestExamples` on both databases. `README.md` *Querying* and `CHANGELOG.md` extended
- [ ] T011 [US2] Add ordering and grouping to `TestQueryCount` (SC-005). Then the whole suite with
  `TEST_DATABASE=postgresql` and the `PG*` variables set (US-2 15)

**Checkpoint**: both stories work on both databases, and the guide is complete.
