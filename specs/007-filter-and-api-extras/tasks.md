# Tasks: Ready-made django-filter filters and a Django REST framework field

**Input**: `spec.md`, `plan.md`, `research.md` in `specs/007-filter-and-api-extras/`

Every task is test-first: the test is written and seen to fail before the code. A test that passes
on its first run records in its task's evidence the change to the code that turns it red. No test
asserts wording or layout. No name starts with an underscore. Lines are at most 88 characters.

## Phase 1: Foundational

- [x] T001 `django-filter` and `djangorestframework` in the dev group, and `uv.lock`

## Phase 2: User Story 1 — A developer adds partial date filters to a filter set (P1)

**Goal**: one declaration gives a validated filter for a date, a range or a part.

**Independent test**: `uv run pytest tests/test_filters.py`, then the same with
`TEST_DATABASE=postgresql` and the `PG*` variables set.

### Group 1

- [ ] T002 [US1] The extra `django-filter` in `pyproject.toml` (FR-001, added with the module that
  imports it, because `deptry` is red on an extra nothing uses), `PartialDateFilterWidget`,
  `PartialDateFilterField` and `PartialDateFilter` for
  `exact`, `gt`, `gte`, `lt` and `lte`. Tests in `tests/test_filters.py`, class
  `TestPartialDateFilter`: each lookup finds what the lookup finds, parametrised over `1990`,
  `1990-06` and `1990-06-14` on both sides of bounds of each precision, compared with the queryset
  the plain lookup gives (US-1 1, 2, FR-003, FR-014). ISO text and select parts find the same rows,
  ISO text wins when both arrive, an empty `?name=` is no entry (US-1 11, FR-007). Text that is not
  a partial date is refused and is not treated as no entry, parametrised over `1990-6`, `1990-02-30`,
  ` 1990`, digits outside ASCII, text longer than any ISO form and a NUL character (US-1 11, edge
  cases, FR-008). A filter with an entry leaves out a row holding no date, and with no entry keeps it
  (edge cases)
- [ ] T003 [US1] `year`, `month` and `day` on `PartialDateFilter`, alone and with a comparison. Class
  `TestPartFilters`: each finds what its lookup finds, `month=6` leaves out `1990`, `0`, a negative
  number and a number no date can hold find nothing, and `month__gte` works (US-1 6, FR-004).
  `1990.5` and `June` are refused (US-1 7, FR-008). Every lookup outside the plan's list raises
  `ImproperlyConfigured`, including `in`, `range` and `month__isnull` (edge cases)
- [ ] T004 [US1] `Meta.filter_overrides` and the `years` argument. Class `TestGeneratedFilters`:
  `Meta.fields` naming `exact`, `gt`, `gte`, `lt`, `lte`, `year`, `month`, `day` and `isnull` gives a
  working filter for each (US-1 8, FR-009). Naming `in` or `range` raises when the class is defined
  (edge cases). Class `TestOfferedYears`: `PartialDateFilter(years=...)` offers those years (US-1 12)

### Group 2

- [ ] T005 [US1] `PartialDateRangeWidget`, `PartialDateRangeField` and `PartialDateRangeFilter`.
  Class `TestPartialDateRangeFilter`: every row of FR-005's table, through ISO text and through
  select parts (US-1 3, FR-005). One bound alone, each way (US-1 4). The rule for when a range
  finds nothing, both sides: `1991-04` to `1991-03` finds nothing, `1991-03-31` to `1991-03` finds
  `1991-03-31`, `1991-03-15` to `1991-03` and `1991-06` to `1991` find what US-1 5 says (FR-005,
  FR-014). A row at each precision on both sides of a bound of each precision (FR-014). `9999` and
  `9999-12` as bounds (edge cases). A refused bound on either side (FR-008). `years` reaches both
  bounds (US-1 12)
- [ ] T006 [US1] Across a relation, on a `Note`-style model with many dates per record: a record with
  one date before the range and one after it is not found, and one inside is (US-1 9, FR-006).
  `exclude=True` and `distinct=True` behave as on any filter. Use `Record` and `Note`, with
  `field_name="note__drafted"`, and add no model
- [ ] T007 [US1] In `tests/test_filters.py`, class `TestFilterBackend`: a list view with
  `DjangoFilterBackend` gives a 400 naming the filter for text that is not a partial date, and the
  filtered list for an ISO form (US-1 10, SC-004). Class
  `TestWithoutRestFramework`: a fresh interpreter with `rest_framework` blocked imports
  `partial_dates.filters` and builds a filter set (US-1 13, FR-002)
- [ ] T008 [US1] `docs/developer/filtering.md` (US-1 14, FR-013, FR-014, SC-006), links from
  `docs/developer/index.md`, `docs/developer/installation.md` and `docs/index.md`, a README section
  and a CHANGELOG entry. Tests in `tests/test_guide.py`, class `TestFilteringExamples`: every example
  on the page runs, and every row of its table is what the filter finds

## Phase 3: User Story 2 — A user narrows a list of records by date (P2)

**Goal**: a person narrows a list by what they know, and a mistake is reported.

**Independent test**: `uv run pytest tests/test_filters.py -k TestListPage`

- [ ] T009 [US2] A `FilterView` over `Sample` in `tests/urls.py` with a small test template. Class
  `TestListPage`, through the test client: the page offers a year, a month and a day select for each
  filter, each with an empty choice, and lists every record (US-2 1). A start of a year and an end
  of a year and a month list the stretch, including a day inside that month (US-2 2). Empty parts do
  not narrow (US-2 3). A day with no month gives `incomplete`, 30 February gives `invalid`, each with
  a 200 response (US-2 4). The address of a narrowed list, opened again, shows the same rows with the
  same parts selected (US-2 5). An ISO address shows its parts selected (US-2 6). A record holding no
  date is left out once narrowed (US-2 7)
- [ ] T010 [US2] The range filter on the example project's sample list, with a `FilterView`, the form
  on the list page and the seed data unchanged (FR-017). Add `example/samples/filters.py`. Say how to try it
  on `docs/developer/filtering.md`, as `docs/developer/forms.md` does

## Phase 4: User Story 3 — A developer exposes a partial date through an API (P2)

**Goal**: one declaration gives a field that reads and writes the ISO form.

**Independent test**: `uv run pytest tests/test_rest_framework.py`

- [ ] T011 [US3] The extra `djangorestframework` in `pyproject.toml` (FR-001, with its module, as
  T002 does), and `PartialDateField` in `partial_dates/rest_framework.py`, reading. Class
  `TestReading`: each precision reads as its ISO form, no date as `null`, an object holding ISO text
  reads as that form (US-3 1–3, FR-010)
- [ ] T012 [US3] Writing. Class `TestWriting`: each ISO form and a `PartialDate` validate to the
  value, and a `ModelSerializer` declaring the field saves it (US-3 4, FR-011). `null` with and
  without `allow_null` (US-3 5). Refused with the code `invalid`, parametrised over `1990-6`,
  `1990-02-30`, `""`, `1990`, `[]`, `{}`, `True`, a NUL character and long text (US-3 6, FR-012,
  SC-004). A required date on a `ModelSerializer` given `""` is a validation error and writes
  nothing (US-3 7). Add the message to `partial_dates/locale/en/LC_MESSAGES/django.po` (FR-016)
- [ ] T013 [US3] Class `TestOptions`: `required`, `read_only`, `source` across a relation and a
  validator (US-3 8), an empty HTML form entry on a field allowing `null` (US-3 9). Class
  `TestModelSerializer`: with nothing declared, a read and a write give the same ISO form as the
  declared field (US-3 10). Class `TestWithoutDjangoFilter`: a fresh interpreter with `django_filters`
  blocked imports the module and validates a value (US-3 11, FR-002). In `tests/test_init.py`, class
  `TestImportWithoutExtras`: with both blocked, `partial_dates`, `partial_dates.fields` and
  `partial_dates.forms` import, and `partial_dates` and a model field build a value (SC-005, FR-002)
- [ ] T014 [US3] `docs/developer/rest-framework.md` (FR-013), links from
  `docs/developer/index.md`, `docs/developer/installation.md` and `docs/index.md`, a README section
  and a CHANGELOG entry. Class `TestRestFrameworkExamples` in `tests/test_guide.py`: every example on
  the page runs

## Requirement coverage

| Requirement | Tasks |
|---|---|
| FR-001 | T002, T011 |
| FR-002 | T007, T013 |
| FR-003 | T002 |
| FR-004 | T003 |
| FR-005 | T005 |
| FR-006 | T006 |
| FR-007 | T002, T004, T009 |
| FR-008 | T002, T003, T005 |
| FR-009 | T004 |
| FR-010 | T011 |
| FR-011 | T012 |
| FR-012 | T012, T013 |
| FR-013, FR-014 | T005, T008, T014 |
| FR-015 | Every test runs on both databases |
| FR-016 | T012 |
| FR-017 | T010 |
| SC-001 | T005, T008 |
| SC-002 | T011, T014 |
| SC-003 | T006, with `docs/developer/filtering.md` showing FairDM's shape: a date range across `dates__value` |
| SC-004 | T002, T003, T005, T007, T012 |
| SC-005 | T013 |
| SC-006 | T008 |
